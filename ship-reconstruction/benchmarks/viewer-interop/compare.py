"""Compare recorded engine world points after exactly one survey-origin restoration."""
import csv
import json
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from coordinate_contract import read_meta, convert

def run(folder):
    outputs={}
    for mode in ('local','baked'):
        case=folder/('origin-'+mode)
        meta=read_meta(case/'assembly.glb')['coordinates']
        oracle=json.loads((case/'oracle.json').read_bytes())
        expected={(r['node'],r['angle']):np.array([r[a] for a in 'xyz']) for r in oracle['cases']}
        unity={}
        for line in (folder/('unity-'+mode+'.log')).read_text().splitlines():
            words=line.split()
            if len(words)==7 and words[0]=='WORLD':
                p=np.array(list(map(float,words[3:6])));unity[words[1],float(words[2])]=p*[-1,1,1]
        blender={}
        with (folder/('blender-'+mode+'.csv')).open() as f:
            for r in csv.DictReader(f):
                blender[r['node'],float(r['angle_deg'])]=np.array([float(r['blender_x']),float(r['blender_z']),-float(r['blender_y'])])
        if set(expected)!=set(unity) or set(expected)!=set(blender):
            raise ValueError('incomplete engine record')
        def vessel(p):
            return convert([p],'gltf_y_up','vessel',meta)[0]
        outputs[mode]={k:(vessel(unity[k]),vessel(blender[k]),vessel(p)) for k,p in expected.items()}
    result=[]
    for k,(u,b,p) in outputs['baked'].items():
        lu,lb,lp=outputs['local'][k]
        row=dict(node=k[0],deg=k[1],baked_error_m=max(np.linalg.norm(u-p),np.linalg.norm(b-p)),
                 local_error_m=max(np.linalg.norm(lu-lp),np.linalg.norm(lb-lp)),
                 engines_m=max(np.linalg.norm(u-b),np.linalg.norm(lu-lb)),
                 encodings_m=max(np.linalg.norm(u-lu),np.linalg.norm(b-lb)),oracle_encoding_m=np.linalg.norm(p-lp))
        if max(v for n,v in row.items() if n.endswith('_m'))>2e-5:
            raise ValueError(str(row))
        result.append(row)
    with (folder/'cross-engine.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=result[0]);w.writeheader();w.writerows(result)
    return result

if __name__=='__main__':
    run(Path(sys.argv[1]))
