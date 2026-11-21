"""Read fixed Git source objects only. Never a build manifest or runtime preflight."""
import argparse
import ast
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys

SOURCE = '0a7c09aaf25218337852bc55a075a400acb3402e'
PREVIOUS = 'e9db012c478fbee5f72c283f593b4f781778043c'
FROZEN = '3a615bf6d449c90eb0a64d25c20c5cdc83fdd06c'
OLD_INPUT = 'tools/pilot_image_build/inputs.json'
OLD_INPUT_SHA = 'e910b3f6d95deb5faf00986760fc4ea8180c71db881f57bdc55559b2d457aad6'
RECEIPT_SHA = '9569b90787065b55828eb1f622108cb13873e29b2cbf6d5efd297bd6480d485a'
EXTRA = (
 'service/mcis_service/audio_review/__init__.py',
 'service/mcis_service/audio_review/app.py',
 'service/mcis_service/local_review_pilot/audio_workbench.html',
 'service/mcis_service/local_review_pilot/workbench_skin.py',
 'tools/audio_transcript_contract/contract.py',
 'tools/audio_transcript_contract/machine_contract.py',
 'tools/audio_transcript_contract/sample_machine_contract.py',
)
FIELDS = ('path','comparison','old_sha256','previous_sha256','source_sha256','source_bytes','source_blob','review_reason')
class Rejected(ValueError): pass

def need(ok, code):
    if not ok: raise Rejected(code)
def digest(raw): return hashlib.sha256(raw).hexdigest()
def safe_path(path):
    p=PurePosixPath(path)
    need(not p.is_absolute() and str(p)==path and all(x not in ('.','..','') for x in p.parts), 'path_rejected')
    need(path.endswith(('.py','.html','.js','.json')) and not any(x in path.lower() for x in ('seed','credential','secret')), 'non_source_path')

class GitObjects:
    def __init__(self, repo): self.repo=repo
    def run(self,*args):
        # No replacement objects, lazy remote fetch, network, checkout or hooks.
        env=dict(PATH=os.defpath,LC_ALL='C',GIT_NO_REPLACE_OBJECTS='1',GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0',GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull)
        p=subprocess.run(['git','-C',str(self.repo),*args],env=env,capture_output=True)
        need(p.returncode==0,'git_objects_unavailable')
        return p.stdout
    def read(self, ref, path, optional=False):
        need(ref in (SOURCE,PREVIOUS,FROZEN),'unfixed_ref')
        safe_path(path)
        raw=self.run('ls-tree','-z',ref,'--',path)
        if not raw and optional:return None
        entries=raw.rstrip(b'\0').split(b'\0')
        need(len(entries)==1 and b'\t' in entries[0], 'missing_or_ambiguous_source')
        meta,name=entries[0].split(b'\t')
        mode,kind,oid=meta.split()
        need(mode in (b'100644',b'100755') and kind==b'blob' and name.decode()==path,'non_regular_source')
        size=int(self.run('cat-file','-s',oid.decode()))
        need(0<=size<=2_000_000,'source_size_limit')
        content=self.run('cat-file','blob',oid.decode())
        need(len(content)==size,'source_size_changed')
        return content,oid.decode()

def old_rows(raw):
    need(digest(raw)==OLD_INPUT_SHA,'old_inputs_changed')
    doc=json.loads(raw)
    need(doc['commit']==FROZEN and len(doc['files'])==58,'old_freeze_identity')
    rows=doc['files'];paths=[x['path'] for x in rows]
    need(len(set(paths))==len(paths),'duplicate_old_path')
    for path in paths:safe_path(path)
    return rows

def verify(rows, receipt, read):
    """Inject only a read-only Git object reader; synthetic tests use byte maps."""
    old={r['path']:r for r in rows};expected=set(old)|set(EXTRA)
    need(len(receipt)==len(expected) and {r['path'] for r in receipt}==expected,'receipt_file_set')
    counts={'unchanged':0,'changed':0,'additional-review':0}
    for r in receipt:
        path=r['path'];safe_path(path)
        target,blob=read(SOURCE,path)
        need(digest(target)==r['source_sha256'] and len(target)==int(r['source_bytes']) and blob==r['source_blob'],'target_bytes_mismatch')
        prev=read(PREVIOUS,path,True)
        need(r['previous_sha256']==(digest(prev[0]) if prev else '-'),'previous_bytes_mismatch')
        if path in old:
            prior,oldblob=read(FROZEN,path)
            original=old[path]
            need(digest(prior)==original['sha256']==r['old_sha256'] and len(prior)==original['size'] and oldblob==original['blob'],'old_frozen_bytes_mismatch')
            status='unchanged' if prior==target else 'changed'
        else:
            need(r['old_sha256']=='-','unexpected_old_entry');status='additional-review'
        need(status==r['comparison'],'wrong_comparison');counts[status]+=1
        # Parse only explicitly reviewed Python bytes, never import them.
        if path.endswith('.py'):ast.parse(target,filename=path)
    return counts

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-only',action='store_true',required=True)
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--source-ref',required=True)
    args=p.parse_args();need(args.source_ref==SOURCE,'source_ref_mismatch')
    g=GitObjects(args.repo)
    partial=subprocess.run(['git','-C',str(args.repo),'config','--local','--get-regexp',r'^(remote\..*\.promisor|extensions\.partialclone)$'],capture_output=True)
    need(partial.returncode in (0,1) and not partial.stdout,'partial_clone_not_supported')
    g.run('merge-base','--is-ancestor',PREVIOUS,SOURCE)
    raw,_=g.read(PREVIOUS,OLD_INPUT);rows=old_rows(raw)
    # Freeze still unchanged at target, not implicitly upgraded to blue UI.
    need(g.read(SOURCE,OLD_INPUT)[0]==raw,'old_builder_inputs_changed')
    receipt_path=Path(__file__).with_name('review.tsv')
    info=receipt_path.lstat()
    need(stat.S_ISREG(info.st_mode) and info.st_size<=100000,'receipt_not_regular_or_oversized')
    receipt_raw=receipt_path.read_bytes()
    need(digest(receipt_raw)==RECEIPT_SHA,'review_receipt_changed')
    reader=csv.DictReader(io.StringIO(receipt_raw.decode()),delimiter='\t')
    need(tuple(reader.fieldnames or ())==FIELDS,'review_columns')
    counts=verify(rows,list(reader),g.read)
    print('SOURCE_REVIEW_MATCH '+json.dumps(counts,sort_keys=True))
    print('NOT_BUILD_INPUT; NOT_CLOSED_DEPENDENCIES; NO_RUNTIME_APPROVAL')

if __name__=='__main__':
    try:main()
    except (Rejected,ValueError,KeyError,OSError,SyntaxError) as e:
        print('SOURCE_REVIEW_REJECTED '+(str(e) if isinstance(e,Rejected) else type(e).__name__),file=sys.stderr)
        raise SystemExit(2)
