"""模型空间 DWG 直读记录与 DXF 实体按句柄双向核对。"""
from collections import Counter
from math import degrees, isclose
import re
from numbers import Real

import ezdxf


def equal(a, b):
    if isinstance(a, Real) and isinstance(b, Real):
        return isclose(a, b, rel_tol=0, abs_tol=1e-6)
    if a is None or b is None or isinstance(a, str) or isinstance(b, str):
        return a == b
    try:
        return len(a) == len(b) and all(equal(i, j) for i, j in zip(a, b))
    except TypeError:
        return a == b


def hatch_paths(s, e):
    yield 'path_count', len(s['paths']), len(e.paths)
    for p, q in zip(s['paths'],e.paths):
        yield 'path_flags', p['flag'], q.path_type_flags
        if 'polyline_paths' in p and hasattr(q,'vertices'):
            yield 'closed', bool(p['closed']), q.is_closed
            yield 'vertices', [[*v['point'],v.get('bulge',0)] for v in p['polyline_paths']], q.vertices
        elif 'segs' in p and hasattr(q,'edges'):
            yield 'edge_count', len(p['segs']), len(q.edges)
            for edge, target in zip(p['segs'],q.edges):
                kind = edge['curve_type']
                yield 'edge_type', kind, int(target.type)
                if kind != int(target.type):
                    continue
                if kind == 1:
                    yield 'edge_start', edge['first_endpoint'], target.start
                    yield 'edge_end', edge['second_endpoint'], target.end
                elif kind == 3:
                    yield 'major_axis', edge['endpoint'], target.major_axis
                    yield 'center', edge['center'], target.center
                    yield 'ratio', edge['minor_major_ratio'], target.ratio
                    start, end = degrees(edge['start_angle']), degrees(edge['end_angle'])
                    if not edge['is_ccw']:
                        start, end = 360-end, 360-start
                    yield 'start_angle', start, target.start_angle
                    yield 'end_angle', end, target.end_angle
                    yield 'ccw', edge['is_ccw'], target.ccw
                elif kind == 4:
                    yield 'degree', edge['degree'], target.degree
                    yield 'knots', edge['knots'], target.knot_values
                    yield 'control_points', [v['point'] for v in edge['control_points']], target.control_points
                    yield 'rational', edge['is_rational'], target.rational
                    yield 'periodic', edge['is_periodic'], target.periodic
                    if edge['is_rational']:
                        yield 'weights', [v.get('weight') for v in edge['control_points']], target.weights
                else:
                    yield 'unsupported_hatch_edge', kind, None
        else:
            yield 'path_representation', 'DWG', 'DXF'


def fields(s, e, names):
    kind = e.dxftype()
    d = e.dxf
    if 'extrusion' in s and d.is_supported('extrusion'):
        yield 'extrusion', s['extrusion'], d.extrusion
    if kind in ('TEXT', 'MTEXT'):
        raw = s['text_value'] if kind == 'TEXT' else s['text']
        yield 'text', raw, d.text if kind == 'TEXT' else e.text
        point = s['ins_pt']
        yield 'insert', point if len(point)==3 else [*point, s.get('elevation',0)], d.insert
        if kind == 'TEXT':
            yield 'height', s['height'], d.height
            yield 'rotation', degrees(s.get('rotation',0)), d.rotation
        else:
            yield 'char_height', s['text_height'], d.char_height
    elif kind == 'DIMENSION':
        yield 'override', s.get('user_text',''), d.get('text','')
        yield 'dimtype', s['flag'], d.dimtype
        yield 'cache', s.get('act_measurement',-1), d.get('actual_measurement',-1)
        yield 'defpoint', s['def_pt'], d.defpoint
        yield 'text_midpoint', [*s['text_midpt'],s['elevation']], d.text_midpoint
        for key, target in [('xline1_pt','defpoint2'),('xline2_pt','defpoint3'),
                            ('first_arc_pt','defpoint4'),('center_pt','defpoint4')]:
            if key in s:
                yield key, s[key], d.get(target)
        if s['entity']=='DIMENSION_LINEAR':
            yield 'angle', degrees(s.get('dim_rotation',0)), d.angle
    elif kind in ('LINE','ARC','CIRCLE','ELLIPSE','XLINE'):
        keys = {'LINE':[('start','start'),('end','end')], 'ARC':[('center','center'),('radius','radius')],
                'CIRCLE':[('center','center'),('radius','radius')],
                'ELLIPSE':[('center','center'),('sm_axis','major_axis'),('axis_ratio','ratio'),
                           ('start_angle','start_param'),('end_angle','end_param')],
                'XLINE':[('point','start'),('vector','unit_vector')]}[kind]
        for key, target in keys:
            yield key, s[key], getattr(d,target)
        if kind == 'ARC':
            for k in ('start_angle','end_angle'):
                yield k, degrees(s[k]), getattr(d,k)
    elif kind == 'SPLINE':
        yield 'degree', s['degree'], d.degree
        yield 'fit_points', s.get('fit_pts',[]), list(e.fit_points)
        ctrl = s.get('ctrl_pts',[])
        yield 'control_points', [[p['x'],p['y'],p['z']] for p in ctrl], list(e.control_points)
        yield 'knots', s.get('knots',[]), list(e.knots)
        if s.get('weighted'):
            yield 'weights', [p['w'] for p in ctrl], list(e.weights)
        for raw, dest in [('beg_tan_vec','start_tangent'),('end_tan_vec','end_tangent')]:
            if raw in s:
                yield raw, s[raw], d.get(dest,(0,0,0))
    elif kind == 'LWPOLYLINE':
        yield 'closed', bool(s['flag'] & 512), e.closed
        yield 'const_width', s.get('const_width',0), d.const_width
        yield 'vertices', s['points'], e.get_points('xy')
        bulges = s.get('bulges',[])
        yield 'bulges', bulges or [0]*len(e), [p[0] for p in e.get_points('b')]
    elif kind == 'INSERT':
        yield 'block', names.get(s['block_header'][-1]), d.name
        yield 'insert', s['ins_pt'], d.insert
        yield 'scale', s['scale'], (d.xscale,d.yscale,d.zscale)
        yield 'rotation', degrees(s['rotation']), d.rotation
    elif kind == 'LEADER':
        yield 'vertices', s['points'], e.vertices
    elif kind == 'SOLID':
        for i in range(4):
            yield f'corner{i+1}', [*s[f'corner{i+1}'],s['elevation']], getattr(d,f'vtx{i}')
    elif kind == 'POINT':
        yield 'location', [s[k] for k in ('x','y','z')], d.location
    elif kind == 'HATCH':
        yield from hatch_paths(s,e)
        yield 'pattern_name', s['name'], d.pattern_name


def audit(source, dxf, manifest):
    objects = source['OBJECTS']
    names = {r['handle'][-1]:r['name'] for r in objects if 'handle' in r and 'name' in r}
    raw = [r for r in objects if r.get('entmode')==2 and r.get('entity') not in ('BLOCK','ENDBLK')]
    src = {format(r['handle'][-1],'X'):r for r in raw}
    doc = ezdxf.readfile(dxf)
    dst = {e.dxf.handle:e for e in doc.modelspace()}
    if len(src)!=len(raw) or len(dst)!=len(doc.modelspace()) or not src:
        raise ValueError('空模型空间或句柄重复')
    issues = []
    groups = Counter()
    checked = Counter()
    supported = {'TEXT','MTEXT','DIMENSION','LINE','ARC','CIRCLE','ELLIPSE','SPLINE',
                 'LWPOLYLINE','INSERT','LEADER','SOLID','POINT','XLINE','HATCH'}
    def record(handle, prop):
        issues.append({'handle':handle,'field':prop})
    for h in sorted(src.keys() | dst.keys()):
        if h not in src or h not in dst:
            record(h,'added' if h not in src else 'missing')
            continue
        s,e=src[h],dst[h]
        kind=e.dxftype()
        if ('DIMENSION' if s['entity'].startswith('DIMENSION_') else s['entity']) != kind:
            record(h,'type')
            continue
        groups[kind]+=1
        if names.get(s['layer'][-1]) != e.dxf.layer:
            record(h,'layer')
        if kind not in supported:
            record(h,'unverified_type')
            continue
        for key, a, b in fields(s,e,names):
            checked[kind]+=1
            if not equal(a,b):
                record(h,key)
    offsets = {}
    failed = {i['handle'] for i in issues}
    for key, expected_kind in [('offset_values','TEXT'),('station_labels','TEXT'),('column_labels','TEXT'),('grid_lines','LINE')]:
        handles = manifest.get(key,[])
        if len(handles)!=len(set(handles)):
            raise ValueError(f'重复的表格定位 {key}')
        passed=0
        for h in handles:
            if h not in src or h not in dst or src[h]['entity']!=expected_kind or h in failed:
                record(h,key)
            elif key in ('offset_values','station_labels') and not src[h]['text_value'].replace('.','',1).isdigit():
                record(h,key+'_not_numeric')
            else:
                passed+=1
        offsets[key]={'expected':len(handles),'matched':passed}
    outside = Counter()
    outside_details = []
    for r in objects:
        if 'entity' not in r or r.get('entmode')==2:
            continue
        outside['dwg_entities'] += 1
        h = format(r['handle'][-1],'X')
        ent = doc.entitydb.get(h)
        if ent is None:
            outside['missing_handles'] += 1
            outside_details.append({'handle':h,'type':r['entity'],'field':'missing'})
        elif r['entity'] in ('TEXT','MTEXT'):
            outside['texts_examined'] += 1
            differences = (['type'] if ent.dxftype()!=r['entity'] else
                           [k for k,a,b in fields(r,ent,names) if not equal(a,b)])
            if differences:
                outside['texts_with_difference'] += 1
                if differences == ['text']:
                    src_text = r.get('text_value',r.get('text'))
                    dst_text = ent.text if ent.dxftype()=='MTEXT' else ent.dxf.text
                    decoded = re.sub(r'\\U\+([0-9a-fA-F]{4})',lambda m:chr(int(m[1],16)),dst_text)
                    if decoded == src_text:
                        outside['unicode_escape_only'] += 1
                outside_details.extend({'handle':h,'type':r['entity'],'field':k} for k in differences)
        else:
            outside['other_present_handles'] += 1
    return {'source_entities':len(src),'dxf_entities':len(dst),'types':dict(groups),
            'checked_properties':dict(checked),'offsets':offsets,'differences':issues,
            'outside_modelspace':dict(outside),'outside_details':outside_details,'lofting_allowed':False}
