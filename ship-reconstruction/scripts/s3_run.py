"""Run frozen S2.1 in its own checkout, then consume its verified geometry.
Research only. Never imports the older S2 from the S3 checkout.
"""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
from s3_s21 import reconstruct
from coordinate_contract import contract, export_mesh

FROZEN='0cfbcb74ae7749e83a02baccab4ec68d71b134a4'

def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],text=True).strip()

def verify_checkout(root):
    if git(root,'rev-parse','HEAD') != FROZEN or git(root,'status','--porcelain','--untracked-files=all'):
        raise ValueError('upstream must be clean frozen S2.1 checkout')
    if not (root/'ship-reconstruction/scripts/s2.py').is_file():
        raise ValueError('missing upstream entrypoint')

def verify_handoff(g, check, digest):
    if g.get('schema_version') != '2.1' or check.get('valid') is not True:
        raise ValueError('invalid upstream handoff')
    if check.get('engineering_approved') is not False or check.get('eligible_for_automatic_full_loft') is not False:
        raise ValueError('unsupported upstream authorization')
    inventory=g.get('inventory', [])
    if len(inventory)!=1 or inventory[0].get('source_sha256')!=digest:
        raise ValueError('geometry source fingerprint mismatch')
    for part in ('tables','curves','alignment'):
        if any(r.get('source_sha256')!=digest for r in g.get(part, [])):
            raise ValueError('unbound geometry source')


def run(root, source, out, python=sys.executable):
    root,source,out=map(lambda p:Path(p).resolve(),(root,source,out))
    verify_checkout(root)
    if not source.is_file() or source.suffix.lower()!='.dxf':
        raise ValueError('single DXF required for this runner')
    if out.exists() or out.is_relative_to(root): raise ValueError('new output outside upstream required')
    out.mkdir(parents=True)
    entry=root/'ship-reconstruction/scripts/s2.py'
    def invoke(tool,src,dest):
        p=subprocess.run([python,str(entry),tool,str(src),'--out',str(dest)],capture_output=True,text=True,timeout=180)
        (out/(tool+'.log')).write_text(p.stdout+'\n'+p.stderr)
        if p.returncode: raise ValueError(f'upstream {tool} failed: {p.returncode}')
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    invoke('run',source,out/'extract')
    path=out/'extract/geometry.json'; raw=path.read_bytes(); g=json.loads(raw)
    invoke('geometry_data_validate',path,out/'validate')
    check=json.loads((out/'validate/geometry_data_validate.json').read_bytes())
    if path.read_bytes()!=raw or hashlib.sha256(source.read_bytes()).hexdigest()!=digest: raise ValueError('input changed')
    verify_checkout(root)
    verify_handoff(g, check, digest)
    report={'upstream_commit':FROZEN,'source_sha256':digest,'geometry_sha256':hashlib.sha256(raw).hexdigest(),'upstream_validation':check,'engineering_approved':False}
    try:
        mesh,r=reconstruct(g,upstream_check=lambda _:check)
    except ValueError as e:
        report.update(status='blocked',reason=str(e))
    else:
        frame="vessel" if r["absolute_frame"] else "local_hull"
        try:
            asset=export_mesh(out/"research.glb",mesh,contract(frame,[0,0,0]))
        except ValueError as exc:
            report.update(status="blocked",reason=str(exc))
        else:
            report.update(status="research_mesh",mesh_report=r,asset=asset)
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False,default=lambda a:a.tolist()))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('upstream',type=Path); p.add_argument('source',type=Path); p.add_argument('out',type=Path); p.add_argument('--python',default=sys.executable); a=p.parse_args(); print(run(a.upstream,a.source,a.out,a.python)['status'])
