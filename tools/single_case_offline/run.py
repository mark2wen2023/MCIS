"""Default preflight only. Explicit --run executes four fixed offline scripts.
No fetch, installation, branch switching, server, browser or application startup.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import stat
import time

ROOT=Path(__file__).resolve().parents[2]
STAGES=('business_query.py','pilot_prepare.py','t100_seat_crosscheck.py','raw_fixture_prepare.py')

def require_bytes(raw,expected):
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('fixed_input_mismatch')

REQUIRED_LOCAL = tuple('tests_acceptance/registered-trajectory-pair/'+name for name in (*STAGES,'business.py')) + tuple('service/mcis_service/'+name for name in ('common/local_review_pilot.py','common/verified_case_context.py','reports/generation_snapshot.py','reports/pilot_trajectory_prepare.py'))

def require_local_inputs(root, config):
    hashes={e['path']:e['sha256'] for e in config['files'] if e['ref']==config['baseline']}
    hashes.update(config['localFiles'])
    for name in REQUIRED_LOCAL:
        path=root/name
        try:
            if not stat.S_ISREG(path.lstat().st_mode):raise ValueError('required_local_not_regular')
        except FileNotFoundError:
            raise ValueError('required_local_missing') from None
        require_bytes(path.read_bytes(),hashes[name])

def require_versions(actual,expected):
    if actual!=expected:raise ValueError('dependency_versions_not_reviewed')

def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT,stderr=subprocess.DEVNULL)

def preflight():
    if not sys.flags.isolated:raise ValueError('python_isolated_mode_required')
    if sys.version_info[:2]!=(3,12):raise ValueError('python_3_12_required')
    config=json.loads(Path(__file__).with_name('inputs.json').read_text())
    require_versions({k:importlib.metadata.version(k) for k in config['dependencies']},config['dependencies'])
    # Import only existing libraries, never MCIS. Failure is not a passed precheck.
    subprocess.run([sys.executable,'-I','-c','import sqlalchemy,fastapi,jsonschema'],check=True,capture_output=True,timeout=30)
    for ref in config['requiredRefs']+[config['baseline']]:git('cat-file','-e',ref+'^{commit}')
    require_local_inputs(ROOT,config)
    summaries=[]
    for entry in config['files']:
        ref,path,digest=entry['ref'],entry['path'],entry['sha256']
        require_bytes(git('show',ref+':'+path),digest)
        if ref==config['baseline']:
            require_bytes(git('show','HEAD:'+path),digest)
            local=ROOT/path
            if local.exists():require_bytes(local.read_bytes(),digest)
        if ref.startswith('2048c60'):
            raw=git('show',ref+':'+path)
            compact=json.dumps(json.loads(raw),separators=(',',':')).encode()
            summaries.append({'file':Path(path).name,'rawSha256':digest,
                              'compactSha256':hashlib.sha256(compact).hexdigest(),
                              'sameBytes':raw==compact})
    return {'python':sys.version.split()[0],'dependencies':config['dependencies'],'syntheticFiles':summaries}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true');args=parser.parse_args()
    start=time.monotonic();results=[]
    try:
        info=preflight()
        print(json.dumps({'preflight':'passed',**info},ensure_ascii=False),flush=True)
        if args.run:
            for script in STAGES:
                tick=time.monotonic()
                try:
                    done=subprocess.run([sys.executable,'-I',str(ROOT/'tests_acceptance/registered-trajectory-pair'/script)],cwd=ROOT,capture_output=True,text=True,timeout=120)
                    code=done.returncode
                    print(done.stdout,end='');print(done.stderr,end='',file=sys.stderr)
                except subprocess.TimeoutExpired:
                    code=124
                results.append({'stage':script,'exitCode':code,'seconds':round(time.monotonic()-tick,3)})
                if code:break
        ok=not args.run or len(results)==len(STAGES) and all(r['exitCode']==0 for r in results)
        print(json.dumps({'mode':'offline-run' if args.run else 'preflight-only','passed':ok,'stages':results,'seconds':round(time.monotonic()-start,3),'browserVerified':False,'loginVerified':False,'archiveVerified':False}))
        return 0 if ok else 1
    except (ValueError,OSError,subprocess.SubprocessError,importlib.metadata.PackageNotFoundError) as exc:
        reason=str(exc) if type(exc) is ValueError else ('dependency_missing' if isinstance(exc,importlib.metadata.PackageNotFoundError) else 'fixed_git_object_file_or_dependency_probe_unavailable')
        print(json.dumps({'preflight':'failed','reason':reason,'passed':False}),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
