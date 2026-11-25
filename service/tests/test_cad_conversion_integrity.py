"""通用回归，全部几何、文字和句柄来自运行时生成的合成夹具。"""
import ezdxf
import pytest
from mcis_service.agents.skills.cad_conversion_integrity.check import inspect_blocks


def ref(entity):
    return [0, 0, int(entity.dxf.handle, 16)]


def sample():
    doc = ezdxf.new()
    block = doc.blocks.new('test_component')
    line = block.add_line((0, 0), (1, 2))
    ins = doc.modelspace().add_blockref(block.name, (2, 3))
    owner = ref(block.block_record)
    obj = [{'object':'BLOCK_HEADER','handle':owner,'name':block.name,'base_pt':[0,0,0],
            'block_entity':ref(block.block),'endblk_entity':ref(block.endblk),'first_entity':ref(line)},
           {'entity':'LINE','handle':ref(line),'ownerhandle':owner,'start':[0,0,0],'end':[1,2,0]},
           {'entity':'INSERT','handle':ref(ins),'block_header':owner,'ins_pt':[2,3,0]}]
    return doc, block, line, ins, obj


def test_intact():
    doc, _, _, _, obj = sample()
    r = inspect_blocks(obj, doc)
    assert r['status']=='passed_in_scope' and r['geometry_checked_members']==1
    assert not r['production_lofting_allowed'] and not r['whole_document_approved']


@pytest.mark.parametrize(('change','expected'), [
    ('empty','top_level_member_changed'),('add','top_level_member_changed'),
    ('shift','member_geometry_changed'),('move','insert_transform_changed'),
    ('redirect','insert_unresolved_or_redirected'),('base','block_base_point_changed'),
    ('add_insert','unexpected_insert'),('xref','external_reference_requires_source'),
])
def test_detects_changes(change, expected):
    doc, block, line, ins, obj = sample()
    if change=='empty': block.delete_entity(line)
    elif change=='add': block.add_point((3,4))
    elif change=='shift': line.dxf.end=(1,3)
    elif change=='move': ins.dxf.rotation=15
    elif change=='redirect': ins.dxf.name='other'
    elif change=='base': block.block.dxf.base_point=(0,1,0)
    elif change=='add_insert': doc.modelspace().add_blockref(block.name,(0,0))
    elif change=='xref': obj[0]['blkisxref']=1
    r=inspect_blocks(obj,doc)
    assert r['status']=='requires_review' and expected in {i['issue'] for i in r['issues']}


def test_unknown_block():
    doc, _, _, _, obj = sample()
    with pytest.raises(ValueError):
        inspect_blocks(obj,doc,'NO_SUCH_HANDLE')


def test_anonymous_name_resolved_by_block_record():
    doc, _, _, _, objs = sample()
    objs[0].update(anonymous=1,name='*U')
    assert inspect_blocks(objs,doc)['status']=='passed_in_scope'


def test_vertex_bulge_is_checked_even_with_unchanged_handles():
    doc, block, _, _, objs=sample()
    poly=block.add_polyline2d([(0,0),(1,0)])
    owner=ref(poly)
    objs.append({'entity':'POLYLINE_2D','handle':owner,'ownerhandle':ref(block.block_record),
                 'flag':poly.dxf.flags})
    for vertex in poly.vertices:
        objs.append({'entity':'VERTEX_2D','handle':ref(vertex),'ownerhandle':owner,
                     'point':list(vertex.dxf.location),'flag':vertex.dxf.flags})
    objs.append({'entity':'SEQEND','handle':ref(poly.seqend),'ownerhandle':owner})
    assert inspect_blocks(objs,doc)['status']=='passed_in_scope'
    poly.vertices[0].dxf.bulge=0.2
    assert 'member_geometry_changed' in {i['issue'] for i in inspect_blocks(objs,doc)['issues']}
