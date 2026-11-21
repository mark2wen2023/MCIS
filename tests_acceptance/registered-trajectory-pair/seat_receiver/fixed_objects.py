"""Read fixed local Git objects only. No fetch, checkout, object writes or fallback."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
from types import ModuleType
BASELINE='1095e67e2d5c1564bfaf82b8e0552dc2d99e7080'
FILES={
 'validation':('0dc1226364524977a4155e480d96436443cd8967','service/mcis_service/trajectory_exchange/validation.py','cd1be59c2c74327ca5468eab06d1461c71ad0afe'),
 'project':('0dc1226364524977a4155e480d96436443cd8967','service/mcis_service/trajectory_exchange/registered_query.py','a7a5a12294308395413af75de1837de284a94a1c'),
 'host':('420284ab5fd44c94b737f8c1cf51bc0ef09aea29','research/expert_group/packet.py','ff2018dad2d58e9fe158f503ecd71a004c20e226'),
 'a':('2048c60fd6650c6f2c99a76a16be463a3895655d','tests_acceptance/shared-trajectory-cross-repo-expanded/vessel-a.json','d8e132c566f07004d76227af52745d5b5ad943c4'),
 'b':('2048c60fd6650c6f2c99a76a16be463a3895655d','tests_acceptance/shared-trajectory-cross-repo-expanded/vessel-b.json','7b332f3af0acbe9d5260fca88b889de95c5279c0')}
class FixedObjectError(ValueError):pass
def read_object(repo,ref,path):
    env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0',GIT_OPTIONAL_LOCKS='0')
    try:
        result=subprocess.run(['git','-C',str(repo),'--no-replace-objects','show',ref+':'+path],
            env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15,check=False)
    except (OSError,subprocess.TimeoutExpired) as e:raise FixedObjectError('LOCAL_GIT_READ_FAILED') from e
    if result.returncode:raise FixedObjectError('FIXED_OBJECT_MISSING:'+ref+':'+path)
    return result.stdout
def verified_modules(raws):
    # Test helper accepts pinned bytes, not an authorization record. No source fallback.
    for key,(_,_,blob) in FILES.items():
        raw=raws[key]
        if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=blob:
            raise FixedObjectError('BLOB_MISMATCH:'+key)
    package='_portable_seat_pinned'
    pkg=ModuleType(package);pkg.__path__=[];sys.modules[package]=pkg
    def module(key,name):
        m=ModuleType(name)
        # Pure imported code computes paths at import, but no disk copies/read are needed.
        m.__file__='/fixed-git-object/'+FILES[key][1]
        m.__package__=package
        sys.modules[name]=m
        exec(compile(raws[key],m.__file__,'exec'),m.__dict__)
        return m
    module('validation',package+'.validation')
    project=module('project',package+'.registered_query')
    host=module('host',package+'.host')
    return project,host,[json.loads(raws['a']),json.loads(raws['b'])]
def fixed_dependencies(repo):
    read_object(repo,BASELINE,'tests_acceptance/registered-trajectory-pair/SEAT-HANDOFF.md')
    return verified_modules({k:read_object(repo,ref,path) for k,(ref,path,_) in FILES.items()})
