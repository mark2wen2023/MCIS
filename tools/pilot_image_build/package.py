"""Standard-library Git-object packager. Never builds, installs, imports app or runs Docker."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys

REF='5647d960a9fe7ed3976e9b19219f88ba29939680'
# Filled from this revision's reviewed manifests, not user-supplied locks.
INPUTS_SHA='475eb0ea815673e6b7f5111ef5865bde358bf987e06459dbd06831b2b447b414'
IMPORTS_SHA='e5a620d09c209cea7f933f97b03bf09b8d6147443181791bc47feeee2fffbb6c'
class Blocked(RuntimeError):pass

def require(ok,message):
    if not ok:raise Blocked(message)

def digest(raw):return hashlib.sha256(raw).hexdigest()

def load_json(raw):
    def unique(pairs):
        result={}
        for k,v in pairs:
            require(k not in result,'Duplicate manifest key');result[k]=v
        return result
    return json.loads(raw,object_pairs_hook=unique)

def safe_path(value):
    require(isinstance(value,str) and bool(re.fullmatch(r'[A-Za-z0-9_./-]+',value)), 'Invalid relative path')
    p=PurePosixPath(value)
    require(not p.is_absolute() and str(p)==value and all(x not in ('','.','..') for x in p.parts),'Path escapes allowlist')
    require(not any(x.startswith('.') or 'seed' in x.lower() or x.lower() in
        ('data','blobs','credentials','secrets','node_modules','__pycache__') for x in p.parts),'Forbidden path')
    require(value.startswith(('service/mcis_service/','tools/pilot_image_acceptance/','contracts/schemas/')),'Outside source roots')
    require(value.endswith(('.py','.html','.js','.schema.json')),'Forbidden file type')
    require(p.name not in ('main.py','models_registry.py','tasks.py'),'Excluded broad startup/task path')
    return p

def plain_directory(path):
    path=Path(path).absolute()
    for part in (list(reversed(path.parents))+[path]):
        st=part.lstat();require(stat.S_ISDIR(st.st_mode) and not stat.S_ISLNK(st.st_mode),'Directory symlink/special path refused')
    return path

class GitObjects:
    def __init__(self,repo,ref):
        self.repo=plain_directory(repo);require(ref==REF,'Exact fixed commit required');self.ref=ref
        # Explicit commands only; reject partial clone rather than permitting
        # missing-object hydration. No network/git fetch/checkout/filter/hooks.
        result=self.command(['config','--local','--get-regexp',r'^(remote\..*\.promisor|extensions\.partialclone)$'],check=False)
        require(result.returncode==1,'Promisor/partial-clone or unreadable Git configuration refused')
        require(self.command(['rev-parse','--verify',ref+'^{commit}']).stdout.strip().decode()==ref,'Fixed commit missing')
    def command(self,args,check=True):
        result=subprocess.run(['/usr/bin/git','--no-replace-objects','-C',str(self.repo),*args],
            env={'PATH':'/usr/bin:/bin','HOME':'/nonexistent','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null',
                 'GIT_NO_LAZY_FETCH':'1','GIT_OPTIONAL_LOCKS':'0','GIT_TERMINAL_PROMPT':'0'},
            capture_output=True,timeout=30)
        if check:require(result.returncode==0,'Required local Git object unavailable; no automatic fetch')
        return result
    def read(self,row):
        p=row['path'];safe_path(p)
        meta=self.command(['ls-tree',self.ref,'--',p]).stdout.decode().strip().split()
        require(meta==['100644','blob',row['blob'],p],'Tracked path/mode/blob differs; symlinks forbidden')
        require(int(self.command(['cat-file','-s',row['blob']]).stdout)==row['size'],'Git size mismatch')
        return self.command(['cat-file','blob',row['blob']]).stdout

def snapshot(manifest,reader):
    require(manifest['format']=='mcis-pilot-build-inputs/1' and re.fullmatch('[0-9a-f]{40}',manifest['commit']), 'Unfixed manifest')
    rows=manifest['files'];require(isinstance(rows,list) and rows,'Empty source allowlist')
    result={}
    for row in rows:
        require(set(row)=={'path','blob','sha256','size'},'Unknown file declaration')
        p=row['path'];safe_path(p);require(p not in result,'Duplicate source path')
        require(re.fullmatch('[0-9a-f]{40}',row['blob']) and re.fullmatch('[0-9a-f]{64}',row['sha256']), 'Nonfixed digest')
        require(type(row['size']) is int and 0<=row['size']<=2*1024*1024,'Source size budget')
        raw=reader(row)
        require(len(raw)==row['size'] and digest(raw)==row['sha256'],'Source SHA256/size mismatch')
        require(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['blob'],'Git blob digest mismatch')
        result[p]=raw
    return result

def verify_artifact(root,item):
    require(set(item)=={'name','sha256','size'} and isinstance(item['name'],str)
            and re.fullmatch('[A-Za-z0-9_.-]+',item['name']) and not item['name'].startswith('.'),'Invalid external name')
    require(isinstance(item['sha256'],str) and re.fullmatch('[0-9a-f]{64}',item['sha256'])
            and type(item['size']) is int and item['size']>0,'Missing fixed external bytes/digest')
    path=root/item['name'];st=path.lstat()
    require(stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_size==item['size'],'External link/type/size refused')
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    require(h.hexdigest()==item['sha256'],'External hash mismatch')

def external_inputs(lock,root):
    require(lock['status']=='reviewed' and isinstance(lock['base_image_id'],str)
            and re.fullmatch('sha256:[0-9a-f]{64}',lock['base_image_id']), 'Runtime base not frozen/reviewed')
    require(root is not None,'Offline external input directory required')
    root=plain_directory(root)
    require(set(p.name for p in root.iterdir())=={lock['archive']['name'],lock['inventory']['name']},'External input set differs')
    for name in ('archive','inventory'):verify_artifact(root,lock[name])
    # Bytes only. This neither loads OCI nor proves inventory matches image layers;
    # that binding must be audited before this immutable lock says reviewed.
    return lock['base_image_id']

def recipe(base):
    require(re.fullmatch('sha256:[0-9a-f]{64}',base),'Unpinned Docker base')
    return ('# Offline reviewed base only; no RUN/download/install and no whole-checkout COPY.\n'
        +'FROM '+base+'\n'
        +'COPY --chown=65532:65532 source/ /opt/pilot/source/\n'
        +'COPY --chown=65532:65532 source/tools/pilot_image_acceptance/container_entry.py /opt/pilot/entry.py\n'
        +'ENV PATH=/opt/pilot/bin:/usr/bin:/bin LANG=C.UTF-8\n'
        +'USER 65532:65532\nWORKDIR /opt/pilot\nENTRYPOINT []\n'
        +'CMD ["/opt/pilot/bin/python", "-I", "/opt/pilot/entry.py"]\n').encode()

def assemble(manifest,reader,target,*,external=None,review_only=False):
    target=Path(target).absolute();plain_directory(target.parent)
    require(not target.exists() and not target.is_symlink(),'Destination already exists')
    require(type(review_only) is bool,'Explicit output mode required')
    if not review_only:require(not manifest['blocked'],'Product source closure blocked: '+','.join(x['code'] for x in manifest['blocked']))
    source=snapshot(manifest,reader)
    base=None if review_only else external_inputs(manifest['external'],external)
    target.mkdir(mode=0o700)  # exclusive create, never merge/overwrite a directory
    try:
        for name,raw in source.items():
            path=target/'source'/name;path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('xb') as f:f.write(raw)
        status={'commit':manifest['commit'],'files':len(source),'buildable':not review_only,
                'runtimeApproved':False,'blockers':manifest['blocked']}
        (target/'STATUS.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n')
        if review_only:
            (target/'NOT_BUILDABLE.txt').write_text('SOURCE REVIEW ONLY. No Dockerfile. Product/database and offline base unresolved.\n')
        else:
            (target/'Dockerfile').write_bytes(recipe(base))
            (target/'.dockerignore').write_text('*\n!source/\n!source/**\n!Dockerfile\n')
        return status
    except BaseException:
        shutil.rmtree(target);raise  # only newly owned target; exclusive parent required

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',required=True);parser.add_argument('--ref',required=True)
    parser.add_argument('--target',required=True);parser.add_argument('--external-inputs')
    parser.add_argument('--source-review-only',action='store_true')
    args=parser.parse_args()
    try:
        root=Path(__file__).resolve().parent
        raw=(root/'inputs.json').read_bytes();require(digest(raw)==INPUTS_SHA,'Input manifest changed')
        require(digest((root/'imports.json').read_bytes())==IMPORTS_SHA,'Import evidence changed')
        manifest=load_json(raw);require(manifest['commit']==REF,'Manifest ref changed')
        git=GitObjects(args.repo,args.ref)
        result=assemble(manifest,git.read,args.target,external=args.external_inputs,review_only=args.source_review_only)
    except (Blocked,OSError,ValueError,KeyError,subprocess.SubprocessError) as error:
        print('BLOCKED: '+str(error),file=sys.stderr);return 2
    print(json.dumps(result,ensure_ascii=False));return 0

if __name__=='__main__':raise SystemExit(main())
