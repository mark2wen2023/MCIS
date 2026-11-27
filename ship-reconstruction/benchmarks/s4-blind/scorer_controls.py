"""基于作者真值核验评分器阳性、阴性控制，禁止作为解析器成绩。"""
import copy,json,re,tempfile
from pathlib import Path
import ezdxf
from score import chk,positions,tip_from_original,nums
P=Path(__file__).resolve().parent
def make(c):
    o=[]
    for f in c['files']:
        d=ezdxf.readfile(P/'frozen/inputs'/c['case']/f['file'])
        for inst in f['instances']:
            for idx,it in enumerate(inst['text_instances']):
                ent=d.entitydb[it.split('/')[-1]];s=ent.dxf.text if ent.dxftype()=='TEXT' else ent.text
                a=dict(type=f['role'],source_sha256=f['sha256'],layout=f['layout'],handle=ent.dxf.handle,instance=it,text=s,anchor_wcs=positions(d,it,[ent.dxf.insert])[0],material=f['material'],dimensions=[],profiles=[],frame_ranges=[],leaders=[])
                v=f['thickness_mm'];status=f['status']
                if status=='conflicting_thickness':v=8 if idx==0 else 12
                if v is not None:a['dimensions']=[dict(kind='thickness',value=v,unit='mm',raw=s)]
                if status=='unbound_unit':a['dimensions']=[dict(kind='thickness',value=8,unit=None,raw='t=8')]
                if f['specification']:
                    sp=f['specification'];a['profiles']=[dict(family=sp.split()[0],values=nums(sp),unit=None,raw=sp)]
                if f['frame_range']:a['frame_ranges']=[dict(start=f['frame_range'][0],end=f['frame_range'][1])]
                for j,l in enumerate(inst['leader_instances']):
                    if ((len(inst['text_instances'])>1) and j!=idx):continue
                    if status=='unbound_target':target=[]
                    elif status=='ambiguous_target':target=inst['target_instances'][:]
                    elif c['scenario']=='双箭头一注':target=[inst['target_instances'][j]]
                    else:target=[inst['target_instances'][0]]
                    a['leaders'].append(dict(handles=[l],tip_wcs=tip_from_original(d,l),target_instances=target))
                o.append(a)
    return dict(observations=o,components=[],engineering_approved=False)
if __name__=='__main__':
    truth=json.loads((P/'frozen/truth.json').read_bytes());rows=[]
    for t in truth:
        want=make(t);inp=P/'frozen/inputs'/t['case']
        good=chk(t,want,inp)
        bad=copy.deepcopy(want)
        for a in bad['observations']:a['source_sha256']='0'*64
        no=chk(t,bad,inp)
        rows.append(dict(case=t['case'],all_authored_evidence_accepted=all(z['passed'] for z in good),unsupported_fingerprint_rejected=not all(z['passed'] for z in no),unexpected=[z for z in good if not z['passed']]))
    (P/'scorer-control.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
    print(sum(r['all_authored_evidence_accepted'] and r['unsupported_fingerprint_rejected'] for r in rows),len(rows))
