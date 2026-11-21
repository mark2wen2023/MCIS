"""Explicit pinned dependencies. No fetch/install/network or authority claims."""
import argparse,hashlib,json,os,subprocess,tempfile
from pathlib import Path
from contextlib import contextmanager
ROOT=Path(__file__).resolve().parent
def verify(raw,spec):
    blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if blob!=spec['blob']:raise ValueError('DEPENDENCY_BLOB:'+spec['key'])
    if 'sha256' in spec and hashlib.sha256(raw).hexdigest()!=spec['sha256']:
        raise ValueError('ORIGINAL_SHA256:'+spec['key'])
def get_raw(spec,repo=None,export=None):
    if export is not None:
        return (export/spec['ref']/spec['path']).read_bytes()
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0',GIT_OPTIONAL_LOCKS='0',GIT_ALLOW_PROTOCOL='')
    result=subprocess.run(['git','-C',str(repo),'--no-replace-objects','show',spec['ref']+':'+spec['path']],
                          env=env,capture_output=True,timeout=15)
    if result.returncode:raise ValueError('FIXED_OBJECT_MISSING:'+spec['key'])
    return result.stdout
@contextmanager
def dependencies():
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--repo',type=Path,help='existing MCIS checkout with fixed objects')
    group.add_argument('--dependencies',type=Path,help='explicit export root: <commit>/<repository path>')
    args=parser.parse_args()
    specs=json.loads((ROOT/'DEPENDENCIES.json').read_text())
    data={}
    for spec in specs:
        raw=get_raw(spec,repo=args.repo,export=args.dependencies);verify(raw,spec);data[spec['key']]=raw
    # Original check imports sibling receiver.py; stage verified public files only.
    with tempfile.TemporaryDirectory(prefix='mcis-ecfc-public-deps-') as temp:
        paths={}
        for spec in specs:
            path=Path(temp)/spec['ref']/spec['path'];path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data[spec['key']]);paths[spec['key']]=path
        yield paths
