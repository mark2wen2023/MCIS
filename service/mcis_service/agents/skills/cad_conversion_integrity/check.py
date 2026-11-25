"""离线检查从 DWG 到 DXF 的 INSERT 引用、块定义及成员身份。"""
import argparse
import hashlib
from collections import defaultdict
from math import degrees, isclose
from pathlib import Path
import json
import subprocess
import sys
import tempfile

import ezdxf


def hexref(record, key):
    ref = record.get(key)
    return format(ref[-1], 'X') if ref and ref[-1] else None


def family(kind):
    for name in ('POLYLINE', 'VERTEX', 'DIMENSION'):
        if kind.startswith(name + '_'):
            return name
    return kind


def close_xyz(a, b):
    return len(a) == len(b) and all(isclose(x, y, abs_tol=1e-6, rel_tol=0) for x, y in zip(a, b))


def member_geometry(raw, entity, children):
    """None 表示本检查器未覆盖该实体的几何字段。"""
    kind = raw['entity']
    d = entity.dxf
    if kind == 'LINE':
        return close_xyz(raw['start'],d.start) and close_xyz(raw['end'],d.end)
    if kind == 'LWPOLYLINE':
        pts = raw['points']
        bulges = raw.get('bulges') or [0]*len(pts)
        widths = raw.get('widths') or [{'start':0,'end':0} for _ in pts]
        if not (len(pts)==len(entity)==len(widths)==len(bulges)):
            return False
        for pt, bulge, width, actual in zip(pts,bulges,widths,entity.get_points('xyseb')):
            if not close_xyz([*pt,width['start'],width['end'],bulge],actual):
                return False
        return (entity.closed==bool(raw['flag'] & 512) and
                close_xyz([raw.get('const_width',0),raw.get('elevation',0)],[d.const_width,d.elevation]) and
                close_xyz(raw.get('extrusion',[0,0,1]),d.extrusion))
    if kind == 'POLYLINE_2D':
        vertices = [(h,r) for h,r in children if r['entity']=='VERTEX_2D']
        if [h for h,_ in vertices]!=[v.dxf.handle for v in entity.vertices]:
            return False
        for (_,r), v in zip(vertices,entity.vertices):
            if not close_xyz(r['point'],v.dxf.location) or r['flag']!=v.dxf.flags:
                return False
            if not close_xyz([r.get(k,0) for k in ('start_width','end_width','bulge')],
                             [v.dxf.start_width,v.dxf.end_width,v.dxf.bulge]):
                return False
        return (raw['flag']==d.flags and raw.get('curve_type',0)==d.smooth_type and
                close_xyz([raw.get('start_width',0),raw.get('end_width',0),raw.get('elevation',0)],
                          [d.default_start_width,d.default_end_width,d.elevation.z]) and
                close_xyz(raw.get('extrusion',[0,0,1]),d.extrusion))
    return None


def inspect_blocks(objects, drawing, only=None):
    """仅判定同句柄转换路径。重新编号的转换件也需要另行建立映射。"""
    headers = {}
    children = defaultdict(list)
    inserts = []
    seen = set()
    for obj in objects:
        handle = hexref(obj, 'handle')
        if not handle or handle in seen:
            raise ValueError('源对象句柄缺失或重复')
        seen.add(handle)
        if obj.get('object') == 'BLOCK_HEADER':
            headers[handle] = obj
        if 'entity' in obj:
            children[hexref(obj,'ownerhandle')].append((handle,obj))
            if obj['entity'] in ('INSERT','MINSERT'):
                inserts.append(obj)
    problems = []
    def issue(code, handle):
        problems.append({'issue':code,'handle':handle})

    references = defaultdict(list)
    for ins in inserts:
        block_id = hexref(ins,'block_header')
        if only is None or only==block_id:
            references[block_id].append(ins)
    if only is not None and only not in references:
        raise ValueError('指定块没有可定位的源引用')
    if not headers:
        raise ValueError('未取得原件块表')
    expected_inserts = {hexref(r,'handle') for refs in references.values() for r in refs}
    target_record = drawing.entitydb.get(only) if only else None
    selected_name = target_record.dxf.name.casefold() if target_record is not None and target_record.dxftype()=='BLOCK_RECORD' else None
    for candidate in drawing.entitydb.values():
        if candidate.dxftype()=='INSERT' and (only is None or candidate.dxf.name.casefold()==selected_name):
            if candidate.dxf.handle not in expected_inserts:
                issue('unexpected_insert',candidate.dxf.handle)
    reviewed = 0
    checked_geometry = 0
    unchecked_types = set()
    for block_id, refs in references.items():
        header = headers.get(block_id)
        if header is None:
            issue('source_block_unresolved',block_id)
            continue
        name = header['name']
        if header.get('blkisxref') or header.get('xrefoverlaid'):
            issue('external_reference_requires_source',block_id)
            continue
        record = drawing.entitydb.get(block_id)
        if record is not None and record.dxftype()=='BLOCK_RECORD' and header.get('anonymous'):
            name = record.dxf.name
        block = drawing.blocks.get(name)
        if block is None or block.block_record.dxf.handle != block_id:
            issue('target_definition_unresolved',block_id)
            continue
        reviewed += 1
        if not close_xyz(header['base_pt'],block.block.dxf.base_point):
            issue('block_base_point_changed',block_id)
        for ins in refs:
            h = hexref(ins,'handle')
            e = drawing.entitydb.get(h)
            if e is None or not e.is_alive or e.dxftype()!='INSERT' or e.dxf.name.casefold()!=name.casefold():
                issue('insert_unresolved_or_redirected',h)
                continue
            attrs = e.dxf
            if not (close_xyz(ins['ins_pt'],attrs.insert) and
                    close_xyz(ins.get('scale',[1,1,1]),(attrs.xscale,attrs.yscale,attrs.zscale)) and
                    close_xyz(ins.get('extrusion',[0,0,1]),attrs.extrusion) and
                    close_xyz([degrees(ins.get('rotation',0))],[attrs.rotation])):
                issue('insert_transform_changed',h)
            if ins['entity']=='MINSERT':
                issue('array_placement_requires_review',h)
        members = children[block_id]
        if (hexref(header,'first_entity') or header.get('entities')) and not any(
                r['entity'] not in ('BLOCK','ENDBLK') for _,r in members):
            issue('source_membership_not_resolved',block_id)
        kinds = {h:family(r['entity']) for h,r in members if r['entity'] not in ('BLOCK','ENDBLK')}
        actual = {e.dxf.handle:e.dxftype() for e in block}
        for h in sorted(actual.keys() | kinds.keys()):
            if actual.get(h)!=kinds.get(h):
                issue('top_level_member_changed',h)
        for key, bound in [('block_entity',block.block),('endblk_entity',block.endblk)]:
            if hexref(header,key)!=bound.dxf.handle:
                issue('block_boundary_changed',hexref(header,key))
        for h,r in members:
            if r['entity'] in ('BLOCK','ENDBLK'):
                continue
            e = drawing.entitydb.get(h)
            if e is None or not e.is_alive or e.dxftype()!=family(r['entity']):
                continue
            geometry = member_geometry(r,e,children[h])
            if geometry is None:
                unchecked_types.add(r['entity'])
            else:
                checked_geometry += 1
                if not geometry:
                    issue('member_geometry_changed',h)
            nested = {j:family(c['entity']) for j,c in children[h]}
            sub = {}
            if hasattr(e,'all_sub_entities'):
                sub = {child.dxf.handle:child.dxftype() for child in e.all_sub_entities()}
            # ezdxf attaches an in-memory SEQEND to an INSERT even with no attributes.
            if e.dxftype()=='INSERT' and not e.attribs and not nested and not r.get('has_attribs'):
                sub = {j:k for j,k in sub.items() if k!='SEQEND'}
            for j in sorted(nested.keys() | sub.keys()):
                if nested.get(j)!=sub.get(j):
                    issue('child_member_changed',j)
    return {'scope':'referenced_block_membership_and_insert_transforms',
            'geometry_checked_members':checked_geometry,'geometry_unchecked_types':sorted(unchecked_types),
            'blocks_checked':reviewed,'references_found':sum(map(len,references.values())),
            'issues':problems,'status':('requires_review' if problems else
                                        'passed_in_scope' if references else 'no_references'),
            'whole_document_approved':False,'production_lofting_allowed':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dwg',type=Path)
    parser.add_argument('dxf',type=Path)
    parser.add_argument('--block',help='可选，指定源块记录句柄')
    args = parser.parse_args()
    def digest(path):
        with path.open('rb') as stream:
            return hashlib.file_digest(stream,'sha256').hexdigest()
    inputs = [args.dwg,args.dxf]
    hashes = [digest(path) for path in inputs]
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp)/'source.json'
        subprocess.run(['dwgread','-O','JSON','-o',source,args.dwg.resolve()],
                       stdout=subprocess.DEVNULL,check=True,timeout=180)
        objects = json.loads(source.read_bytes())['OBJECTS']
    report = inspect_blocks(objects,ezdxf.readfile(args.dxf),args.block.upper() if args.block else None)
    if hashes != [digest(path) for path in inputs]:
        raise ValueError('核对过程中输入版本发生变化')
    report['dwg_sha256'],report['dxf_sha256'] = hashes
    print(json.dumps(report,ensure_ascii=False))
    return 4 if report['status']=='requires_review' else 0


if __name__=='__main__':
    try:
        sys.exit(main())
    except (OSError,KeyError,TypeError,ValueError,subprocess.SubprocessError,ezdxf.DXFError) as exc:
        print(f'无法完成比对：{exc}',file=sys.stderr)
        sys.exit(4)
