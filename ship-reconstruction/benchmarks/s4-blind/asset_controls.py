"""完整结构交接包验收，保留闭合体积相同却形状/位置错误的反例。"""
import argparse,copy,hashlib,json,shutil,struct,subprocess,sys,tarfile,tempfile
from pathlib import Path
from collections import Counter
P=Path(__file__).resolve().parent
def save(p,o):p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n')
def main():
    a=argparse.ArgumentParser();a.add_argument('repo',type=Path);a.add_argument('rev');a.add_argument('run');v=a.parse_args();r=P/'runs'/v.run;dst=r/'成品独立回读';dst.mkdir(exist_ok=False);rows=[]
    with tempfile.TemporaryDirectory() as tmp,tempfile.TemporaryFile() as st:
        subprocess.run(['git','-C',str(v.repo),'archive',v.rev,'ship-reconstruction'],stdout=st,check=True);st.seek(0)
        with tarfile.open(fileobj=st) as t:t.extractall(tmp,filter='data')
        scripts=Path(tmp)/'ship-reconstruction/scripts';sys.path.insert(0,str(scripts));import s4_validate
        fresh=[*sorted(r.glob('S*/out/structures.json')),*sorted((r/'原9项').glob('*/structures.json')),*sorted((r/'阵列补充').glob('*/structures.json')),*sorted((r/'局部板件控制').glob('*/structures.json'))]
        for g in fresh:
            issues=s4_validate.validate(g);rows.append(dict(file=str(g.relative_to(r)),valid=not issues,issues=issues))
        save(dst/'原始交接.json',rows);out=[]
        original=r/'局部板件控制/compact_letters'
        for key in ('original','missing','scaled_volume','shift_equal_volume','reshaped_equal_volume','shift_and_updated_digest','reshape_and_updated_digest'):
            loc=dst/key;shutil.copytree(original,loc)
            ply=next(loc.glob('*.ply'))
            if key=='missing':ply.unlink()
            if key not in ('original','missing'):
                b=bytearray(ply.read_bytes());start=b.index(b'end_header\n')+len(b'end_header\n');head=bytes(b[:start]);assert b'property double x' in head
                import re
                n=int(re.search(rb'element vertex (\d+)',head)[1])
                for i in range(n):
                    ix=start+i*24;x,y,z=struct.unpack_from('<ddd',b,ix)
                    if key=='scaled_volume':x*=1.5
                    if key in ('shift_equal_volume','shift_and_updated_digest'):x+=.25
                    if key in ('reshaped_equal_volume','reshape_and_updated_digest'):x*=2;y*=.5
                    struct.pack_into('<ddd',b,ix,x,y,z)
                ply.write_bytes(b)
                if key.endswith('updated_digest'):
                    manifest=loc/'structures.json';g=json.loads(manifest.read_bytes());g['local_models'][0]['asset_sha256']=hashlib.sha256(b).hexdigest();save(manifest,g)
            cli=subprocess.run([sys.executable,str(scripts/'s4_validate.py'),str(loc/'structures.json')],capture_output=True,text=True)
            result=json.loads(cli.stdout);ok=result['valid']==(key=='original') and cli.returncode==(0 if key=='original' else 4)
            out.append(dict(case=key,expected_valid=key=='original',observed_valid=result['valid'],exit=cli.returncode,issues=result['issues'],correct=ok))
        save(dst/'成品控制.json',out)
        print('原交接',sum(c['valid'] for c in rows),len(rows),'控制',[(x['case'],x['correct']) for x in out])
if __name__=='__main__':main()
