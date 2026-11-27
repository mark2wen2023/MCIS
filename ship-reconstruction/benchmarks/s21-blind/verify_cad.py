"""逐曲线从独立原图读控制文字、母实体、插入变换，对照解析船体和运行结果。"""
import argparse,csv,json,re
from collections import defaultdict
from pathlib import Path
import ezdxf
import numpy as np
from ezdxf.math import Vec3
from forms import FORMS,width
P=Path(__file__).resolve().parent

def read_frame(doc,refs):
    p=[];q=[]
    for pair in refs:
        inst,h=pair['instance'].split('/');source=doc.entitydb[h];ip=doc.entitydb[inst]
        coord=ip.matrix44().transform(source.dxf.insert);numbers=re.fullmatch(r'CONTROL \S+ X=(\S+) Y=(\S+) Z=(\S+) m',source.dxf.text).groups()
        p.append([coord.x,coord.y,1.]);q.append([float(v) for v in numbers])
    fit,_,rank,_=np.linalg.lstsq(np.asarray(p),np.asarray(q),rcond=None)
    if rank!=3:raise ValueError('rank')
    return fit

def physical(form,curve,p):
    k=0 if curve['view']=='YZ' else 2;ref=curve['station_m'] if k==0 else curve['level_m']
    # CAD 齐次坐标回投可能越过端站 ~1e-14 m，同一端站按浮点舍入归齐。
    x=float(np.clip(p[0],0,form.length));from forms import vertical
    lo,hi=vertical(form,x/form.length);z=float(np.clip(p[2],lo,hi));w=width(form,x,z,curve['side']);sign=1 if curve['side']=='port' else -1
    return [abs(p[k]-ref),abs(p[1]-sign*w)]

def main():
    a=argparse.ArgumentParser();a.add_argument('run');args=a.parse_args();folder=P/'runs'/args.run
    truth=json.loads((P/'casebook/source-truth.json').read_bytes())
    rows=[]
    for f,item in zip(FORMS,truth):
        data=json.loads((folder/f.code/'out/geometry.json').read_bytes())
        info=next(x for x in item['files'] if x['curves'])
        doc=ezdxf.readfile(P/'casebook/inputs'/f.code/info['file'])
        groups=defaultdict(list)
        for ctl in info['controls']:groups[ctl['frame']].append(ctl)
        matrices={k:read_frame(doc,v) for k,v in groups.items()}
        for c in info['curves']:
            ins,h=c['instance'].split('/');entity=doc.entitydb[h];matrix=matrices[ins];placement=doc.entitydb[ins].matrix44()
            if entity.dxftype()=='SPLINE':
                pp=list(entity.construction_tool().approximate(128))
            else:
                a=np.asarray(entity.get_points('xy'))
                pp=[Vec3(*(q0+t*(q1-q0)),0) for q0,q1 in zip(a,a[1:]) for t in (0,.25,.5,.75)]+[Vec3(*a[-1],0)]
            wcs=np.asarray([[p.x,p.y,1] for p in map(placement.transform,pp)])
            raw=wcs@matrix;errors=np.array([physical(f,c,xyz) for xyz in raw])
            output=next((k for k in data.get('curves',[]) if k['source_sha256']==info['sha256'] and k['instance']==c['instance']),None)
            delta=None;count=0
            if output and len(output.get('ship_coordinates',[]))==1:
                p2=np.asarray(output['samples']);xyz=np.asarray(output['ship_coordinates'][0]['points_m']);count=len(xyz)
                if count==len(p2):
                    comp=np.column_stack((p2[:,:2],np.ones(len(p2))))@matrix
                    delta=float(np.max(np.linalg.norm(comp-xyz,axis=1)))
            rows.append(dict(case=f.code,instance=c['instance'],entity=entity.dxftype(),view=c['view'],side=c['side'],independent_samples=len(wcs),source_fixed_axis_error_m=float(errors[:,0].max()),source_vs_analytic_halfwidth_max_m=float(errors[:,1].max()),output_samples=count,output_xyz_vs_independent_map_max_m=delta))
    with (folder/'曲线三维独立回读.csv').open('w',encoding='utf-8-sig',newline='') as file:
        w=csv.DictWriter(file,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    metric=dict(curves=len(rows),source_read_points=sum(r['independent_samples'] for r in rows),output_points=sum(r['output_samples'] for r in rows),available_coordinate_max_error_m=max(r['output_xyz_vs_independent_map_max_m'] for r in rows if r['output_xyz_vs_independent_map_max_m'] is not None),coordinate_matches=sum(r['output_xyz_vs_independent_map_max_m'] is not None and r['output_xyz_vs_independent_map_max_m']<=1e-7 for r in rows),source_vs_analytic_max_by_case_view={case.code:{v:max(r['source_vs_analytic_halfwidth_max_m'] for r in rows if r['case']==case.code and r['view']==v) for v in ('YZ','XY')} for case in FORMS})
    (folder/'曲线三维独立回读.json').write_text(json.dumps(metric,indent=2)+'\n')
    print(metric)
if __name__=='__main__':main()
