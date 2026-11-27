"""预登记的独立结构观测评分。按原始文件和完整实例绑定；无证与漏识别分开。"""
import math,re
from pathlib import Path
from collections import Counter
import ezdxf
import numpy as np
from ezdxf.math import Vec3

ALIASES={'shell_plate':{'shell_plate','plate','outer_plate','shell_plating'},'double_bottom_plate':{'double_bottom_plate','inner_bottom_plate'},'strong_beam':{'strong_beam','deep_beam'},'frame':{'frame','web_frame'},'stiffener':{'stiffener','bulkhead_stiffener'}}
UNITS={'mm':1.,'毫米':1.,'cm':10.,'厘米':10.,'m':1000.,'米':1000.,'in':25.4,'inch':25.4,'英寸':25.4}
def nums(s):return [float(x) for x in re.findall(r'\d+(?:\.\d+)?',s)]
def norm(s):return re.sub(r'\s+','',s.replace('\\P','').replace('×','x').replace('＊','x')).casefold()
def positions(d,inst,entity):
    path=inst.split('/')[:-1];out=[]
    for pts in entity:
        p=Vec3(pts)
        for h in reversed(path):p=d.entitydb[h].matrix44().transform(p)
        out.append(list(p))
    return out
def tip_from_original(d,leader_instance):
    e=d.entitydb[leader_instance.split('/')[-1]]
    raw=e.vertices[0] if e.dxftype()=='LEADER' else list(e.vertices())[0]
    return positions(d,leader_instance,[raw])[0]
def points(p):
    if isinstance(p,dict) and 'x' in p and 'y' in p:return [p['x'],p['y'],p.get('z',0)]
    return p
def xyerr(a,b):
    try:return float(np.linalg.norm(np.asarray(points(a))[:2]-np.asarray(points(b))[:2]))
    except (ValueError,TypeError,IndexError):return float('inf')
def chk(case,data,folder):
    out=[]
    def ck(metric,part,ok,actual=None):
        out.append(dict(metric=metric,source=part,passed=bool(ok),actual=actual))
    obs=data.get('observations',[]);ck('observations_output',case['case'],isinstance(obs,list) and bool(obs),len(obs))
    ck('engineering_gate',case['case'],data.get('engineering_approved') is False,data.get('engineering_approved'))
    ck('no_unproved_3d',case['case'],not any(c.get('geometry_status')=='research_geometry_verified' for c in data.get('components',[])))
    for f in case['files']:
        name=f['file'];d=ezdxf.readfile(folder/name);loc=lambda n:name+'#'+n;sh=f['sha256'];status=f['status']
        for inst in f['instances']:
            anns=inst['text_instances'];main=anns[0];h=main.split('/')[-1]
            matched=[r for r in obs if r.get('source_sha256')==sh and r.get('handle')==h and r.get('instance')==main and r.get('layout')==f['layout']]
            obj=loc(main);ck('annotation_instance',obj,matched,len(matched))
            present=' '.join(str(r.get('text','')) for r in matched)
            ck('raw_annotation',obj,bool(present) and (norm(f['raw_text']) in norm(present) or all(norm(part) in norm(present) for part in re.split(r'\\P|  ',f['raw_text']))),present)
            anchor=positions(d,main,[d.entitydb[h].dxf.insert])[0]
            error=min([xyerr(r.get('anchor_wcs'),anchor) for r in matched] or [float('inf')]);ck('original_wcs',obj,error<1e-5,error if math.isfinite(error) else None)
            roles={r.get('type') for r in matched}
            ck('component_type',obj,bool(roles & ALIASES.get(f['role'],{f['role']})),sorted(str(t) for t in roles))
            dims=[z for r in matched for z in r.get('dimensions',[]) if isinstance(z,dict) and str(z.get('kind','')).lower() in ['thickness','plate_thickness','板厚','厚度']]
            known=[(z.get('value'),str(z.get('unit')).lower()) for z in dims]
            physical=[v*UNITS[u] for v,u in known if isinstance(v,(int,float)) and not isinstance(v,bool) and u in UNITS]
            if f['thickness_mm'] is not None:
                ck('printed_thickness',obj,any(abs(t-f['thickness_mm'])<1e-7 for t in physical),known)
            elif status in ['unknown_thickness','orphan_size']:
                ck('do_not_borrow_thickness',obj,bool(matched) and not physical,known)
            elif status=='unbound_unit':
                ck('unbound_printed_unit',obj,bool(matched) and not physical and any(v==8 and u in ['none','unknown',''] for v,u in known),known)
            elif status=='conflicting_thickness':
                other=[r for r in obs if r.get('instance') in anns[1:] and r.get('source_sha256')==sh]
                vals=[z.get('value') for r in [*matched,*other] for z in r.get('dimensions',[]) if z.get('kind') in ['thickness','plate_thickness']]
                ck('distinct_conflicting_evidence',obj,8 in vals and 12 in vals,vals)
            if f['specification']:
                prof=[o for r in matched for o in r.get('profiles',[]) if isinstance(o,dict)]
                raw=f['specification'];family=raw.split()[0].upper()
                def eq(z):
                    fam=str(z.get('family','')).upper()
                    good=(fam==family or {'L':'ANGLE','FB':'FLAT_BAR','HP':'BULB_FLAT','T':'TEE'}.get(family)==fam)
                    if not good:return False
                    a=z.get('values',[]); a=list(a.values()) if isinstance(a,dict) else a
                    try: values=[float(v) for v in a if v is not None]
                    except (ValueError,TypeError):return False
                    return values==nums(raw) and z.get('unit') in (None,'','unknown') and ('?' not in raw or '?' in str(z.get('raw','')))
                ck('profile_dimensions_and_printed_unit',obj,any(eq(z) for z in prof),prof)
            if f['frame_range']:
                fr=[o for r in matched for o in r.get('frame_ranges',[]) if isinstance(o,dict)]
                ck('frame_scope',obj,any([q.get('start'),q.get('end')]==f['frame_range'] for q in fr),fr)
            if f.get('material'):
                materials=[r.get('material') for r in matched];ck('material_evidence',obj,any(f['material'].casefold() in str(v).casefold() for v in materials),materials)
            if case['scenario']=='材料未注':
                materials=[r.get('material') for r in matched];ck('unknown_material',obj,bool(matched) and not any(re.search(r'AH\d|DH\d|Q\d|steel',str(v),re.I) for v in materials),materials)
            leaders=[v for r in matched for v in r.get('leaders',[]) if isinstance(v,dict)]
            # 附着在第二个原始注记的引线按第二个注记计，保持同值及矛盾两条证据。
            for r in obs:
                if r.get('source_sha256')==sh and r.get('instance') in anns[1:]:leaders.extend(v for v in r.get('leaders',[]) if isinstance(v,dict))
            for n,lead in enumerate(inst['leader_instances']):
                end=tip_from_original(d,lead)
                def idmatch(l):
                    ids=set(str(h) for h in l.get('handles',[]));return lead in ids or lead.rsplit('/',1)[-1] in ids
                refer=[l for l in leaders if idmatch(l)]
                ck('leader_handle_and_tip',loc(lead),any(xyerr(v.get('tip_wcs'),end)<1e-5 for v in refer),[v.get('tip_wcs') for v in refer])
                actual={str(id) for l in refer for id in l.get('target_instances',[])}
                if status=='unbound_target':want=set()
                elif status=='ambiguous_target':want=set(inst['target_instances'])
                elif case['scenario']=='双箭头一注':want={inst['target_instances'][n]}
                else:want={inst['target_instances'][0]}
                ck('leader_target_candidates',loc(lead),bool(refer) and (actual==want or (status=='ambiguous_target' and not actual)),sorted(actual))
            if not inst['leader_instances'] and status=='unbound_target':
                actual=[b for l in leaders for b in l.get('target_instances',[])];ck('do_not_invent_leader',obj,bool(matched) and not actual,actual)
    return out
