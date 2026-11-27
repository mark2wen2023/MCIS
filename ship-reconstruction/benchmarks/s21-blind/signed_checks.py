"""跨图舷别证据的输入合同级控制实验；采用自己的纸面比例、偏移及见证位置。"""
import argparse,copy,json,subprocess,sys,tarfile,tempfile
from pathlib import Path
def specimen(scenario):
    a,b='1'*64,'2'*64
    pbase=[(12,4),(26,4),(30,4)]
    qbase=[(3+(p[0]-10)/2,6.) for p in pbase]
    # 源图物理 X=(u-10)/2，Y=±v/2；目标图 X=u-3，Y=(v-10)/2，Z=1。
    if scenario=='only_one':pbase=pbase[:1];qbase=qbase[:1]
    if scenario=='conflict':qbase[1]=(qbase[1][0],14.)
    if scenario=='unrepeatable_pair':pbase[1]=pbase[0];qbase[1]=qbase[0];pbase=pbase[:2];qbase=qbase[:2]
    if scenario=='off_trace':pbase=[(x,y+.7) for x,y in pbase]
    if scenario=='out_of_bounds':qbase=[(x,y+50) for x,y in qbase]
    if scenario=='centerline':pbase=[(x,0) for x,y in pbase];qbase=[(x,10) for x,y in qbase]
    labels=lambda xy:[dict(id='feature-'+str(i),instance='ID'+str(i),layout='Model',p=[x,y,0]) for i,(x,y) in enumerate(xy)]
    ca=labels(pbase);cb=labels(qbase)
    if scenario=='repeated_names':cb.extend(copy.deepcopy(cb))
    m=lambda s:[[.5,0,-5],[0,.5*s,0],[0,0,1]]
    frame=dict(layout='Model',status='verified',controls=['DD','EE','FF','AB'],hull_halfspaces=[[1,0,-30],[-1,0,0],[0,1,-20],[0,-1,0]],paper_to_ship_m=[[1,0,-3],[0,.5,-5],[0,0,1]])
    c=dict(source_sha256=a,instance='A7/CF',layout='Model',samples=[[10,0 if scenario=='centerline' else 4,0],[34,0 if scenario=='centerline' else 4,0]],ship_coordinate_candidates=[dict(y_sign=s,paper_to_ship_m=m(s)) for s in [1,-1]])
    return dict(inventory=[dict(source_sha256=a,landmarks=ca),dict(source_sha256=b,landmarks=cb,registration_notes=[dict(instance='ST',layout='Model',text='X forward Y port Z up origin: stern')])],relationships=[dict(sources=[a,b],explicit_refs=[] if scenario=='unrelated' else ['drawing ref'])],alignment=[dict(source_sha256=b,frames=[frame])],curves=[c])
def main():
    a=argparse.ArgumentParser();a.add_argument('repo',type=Path);a.add_argument('rev');a.add_argument('out',type=Path);arg=a.parse_args();arg.out.mkdir(parents=True,exist_ok=False);rows=[]
    with tempfile.TemporaryDirectory() as tmp,tempfile.TemporaryFile() as f:
        subprocess.run(['git','-C',str(arg.repo),'archive',arg.rev,'ship-reconstruction'],stdout=f,check=True);f.seek(0)
        with tarfile.open(fileobj=f) as t:t.extractall(tmp,filter='data')
        sys.path.insert(0,str(Path(tmp)/'ship-reconstruction/scripts'));from s2lib.landmarks import decide
        for sc in ['negative_port_sign','only_one','unrelated','conflict','unrepeatable_pair','off_trace','out_of_bounds','centerline','repeated_names']:
            g=specimen(sc);(arg.out/(sc+'-input.json')).write_text(json.dumps(g))
            decide(g);c=g['curves'][0];score=c.get('registration_decision',{});sign=score.get('y_sign');want=-1 if sc=='negative_port_sign' else None
            rows.append(dict(case=sc,want=want,observed=sign,candidates_retained=len(c['ship_coordinate_candidates']),passed=sign==want and len(c['ship_coordinate_candidates'])==2))
            (arg.out/(sc+'-output.json')).write_text(json.dumps(c))
    (arg.out/'outcomes.json').write_text(json.dumps(rows,indent=2)+'\n');print([(r['case'],r['passed']) for r in rows])
if __name__=='__main__':main()
