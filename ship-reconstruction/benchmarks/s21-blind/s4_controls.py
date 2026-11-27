"""S4 原生双视图输入的独立正负控；以实体是否输出和未知项核对处置。"""
import argparse,json,subprocess,sys,tarfile,tempfile
from pathlib import Path
import ezdxf
CASES=['完整双图','缺交叉引用','截面厚度冲突','外法向反号','标注落在部件外','多轮廓重叠','役别不一致','次视图控制共线','缺第二张图']
def make(folder,scenario):
    folder.mkdir(parents=True)
    for view in ('XY','XZ'):
        if scenario=='缺第二张图' and view=='XZ':continue
        doc=ezdxf.new('R2013');m=doc.modelspace()
        def text(x,z,s):m.add_text(s,dxfattribs={'height':.015,'insert':(x,z)})
        if scenario!='缺交叉引用':text(0,4,'DRAWING ID=alt_side' if view=='XZ' else 'REF=alt_side')
        pts=[(-3,-2),(6,-2),(-3,4),(6,4),(1,3)] if view=='XY' or scenario!='次视图控制共线' else [(-3,2),(0,2),(1,2),(3,2)]
        for i,(u,v) in enumerate(pts):
            xyz=(u,v,0) if view=='XY' else (u,0,v)
            text(u,v,f'CONTROL POINT{i} X={xyz[0]} Y={xyz[1]} Z={xyz[2]} m')
        ymin=0.;top=1.3 if view=='XY' else (.32 if scenario=='截面厚度冲突' else .18)
        e=m.add_lwpolyline([(-.6,ymin),(4.2,ymin),(4.2,top),(-.6,top)],close=True)
        if scenario=='多轮廓重叠' and view=='XY':
            m.add_lwpolyline([(-.4,.02),(2,.02),(2,1),(-.4,1)],close=True)
        text(.06,.08,'PART APR21 '+('deck' if view=='XY' or scenario!='役别不一致' else 'tank'))
        if view=='XY':
            text(.3,2.5 if scenario=='标注落在部件外' else .48,'THICKNESS=180 mm');text(.32,.64,'NORMAL=-Z' if scenario=='外法向反号' else 'NORMAL=+Z')
        path=folder/(view+'.dxf');doc.saveas(path)
        aud=ezdxf.readfile(path).audit();assert not aud.errors and not aud.fixes
def main():
    a=argparse.ArgumentParser();a.add_argument('repo',type=Path);a.add_argument('rev');a.add_argument('out',type=Path);arg=a.parse_args();arg.out.mkdir(parents=True,exist_ok=False);rec=[]
    with tempfile.TemporaryFile() as spool,tempfile.TemporaryDirectory() as tmp:
        subprocess.run(['git','-C',str(arg.repo),'archive',arg.rev,'ship-reconstruction'],stdout=spool,check=True);spool.seek(0)
        with tarfile.open(fileobj=spool) as t:t.extractall(tmp,filter='data')
        cli=Path(tmp)/'ship-reconstruction/scripts/s4_structure.py'
        for ix,sc in enumerate(CASES):
            root=arg.out/f'{ix:02}';inputs=root/'inputs';out=root/'out';make(inputs,sc)
            p=subprocess.run([sys.executable,str(cli),str(inputs),'--out',str(out)],capture_output=True)
            path=out/'structures.json';j=json.loads(path.read_bytes()) if path.is_file() else {};rows=j.get('components',[])
            got=all(r['geometry_status']=='research_geometry_verified' for r in rows) and len(rows)>0
            expected=ix==0;assets=list(out.glob('*.ply'))
            valid=got==expected and p.returncode==(0 if expected else 4) and len(assets)==int(expected) and j.get('engineering_approved') is False
            if expected:valid=valid and abs(rows[0].get('dimension_m',-1)-.18)<1e-7 and 'hull_attachment' in rows[0].get('unknowns',[])
            rec.append(dict(case=sc,expected_geometry=expected,exit_code=p.returncode,geometry_count=len(assets),status=[r.get('geometry_status') for r in rows],issues=[r['issues'] for r in rows],correct=valid))
            if p.stderr:(root/'stderr.log').write_text(p.stderr.decode().replace(str(arg.out.resolve()),'<outputs>').replace(tmp,'<frozen>'))
    (arg.out/'results.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n');print([(r['case'],r['correct']) for r in rec])
if __name__=='__main__':main()
