"""AST only for launcher/prepare; literals and synthetic import statements only executed."""
import ast
from copy import deepcopy
from pathlib import Path
import subprocess
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[2]
BASE='585a9c0ffbce68a5a98c9facdfb2c91fd2db2c4a'
PREFIX='tools/media_review_demo/'
MODULE='tools.media_review_demo.constants'

def old(name):
    result=subprocess.run(['/usr/bin/git','-C',str(ROOT),'show',BASE+':'+PREFIX+name],
        env={'PATH':'/usr/bin:/bin','GIT_NO_LAZY_FETCH':'1','GIT_CONFIG_NOSYSTEM':'1',
             'GIT_CONFIG_GLOBAL':'/dev/null'},check=True,capture_output=True)
    return ast.parse(result.stdout)

def current(name):return ast.parse((ROOT/PREFIX/name).read_text())
def selected(n):
    return isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('CID','PUBLIC')

prepare, launch = old('prepare.py'),old('launch.py')
constants=current('constants.py')
assert isinstance(constants.body[0],ast.Expr) and isinstance(constants.body[0].value,ast.Constant)
assert all(selected(n) for n in constants.body[1:])
original=[n for n in prepare.body if selected(n)]
assert len(original)==2
assert [ast.dump(n) for n in constants.body[1:]]==[ast.dump(n) for n in original]
assert {n.targets[0].id:ast.literal_eval(n.value) for n in original}=={n.targets[0].id:ast.literal_eval(n.value) for n in constants.body[1:]}
expected=deepcopy(prepare)
first=next(i for i,n in enumerate(expected.body) if selected(n))
expected.body=[n for n in expected.body if not selected(n)]
import_node=ast.parse('from tools.media_review_demo.constants import CID, PUBLIC').body[0]
expected.body.insert(first,import_node)
assert ast.dump(expected)==ast.dump(current('prepare.py'))
edges=[n for n in launch.body if isinstance(n,ast.ImportFrom) and n.module=='tools.media_review_demo.prepare']
assert len(edges)==1
edges[0].module=MODULE
assert ast.dump(launch)==ast.dump(current('launch.py'))
assert not any(isinstance(n,ast.ImportFrom) and n.module=='tools.media_review_demo.prepare' for n in ast.walk(current('launch.py')))
# Only literal shared module and selected import nodes; NEVER execute either script.
shared={'__builtins__':{}}
exec(compile(constants,'<constant literals>','exec'),shared)
module=SimpleNamespace(CID=shared['CID'],PUBLIC=shared['PUBLIC'])
def importer(name,globals=None,locals=None,fromlist=(),level=0):
    assert name==MODULE and fromlist==('CID','PUBLIC') and level==0
    return module
spaces=[]
for filename in ('prepare.py','launch.py'):
    nodes=[n for n in current(filename).body if isinstance(n,ast.ImportFrom) and n.module==MODULE]
    assert len(nodes)==1
    space={'__builtins__':{'__import__':importer}}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<synthetic shared import>','exec'),space)
    assert space['CID']==shared['CID'] and space['PUBLIC'] is shared['PUBLIC']
    spaces.append(space)
assert spaces[0]['PUBLIC'] is spaces[1]['PUBLIC']
print('PASS original constant literals, zero-import shared module, exact AST-only relocation')
print('PASS old launcher→prepare edge exists; candidate removes it; both retain CID/PUBLIC names and shared object')
print('NOT RUN: launcher/prepare, dependencies, application or startup; no isolation claim')
