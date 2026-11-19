"""AST plus an extracted seed branch with entirely handmade dependencies.
Does not import main, seed modules, settings, ORM or any service dependency.
"""
import ast
from copy import deepcopy
from pathlib import Path
import subprocess
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
PATH = 'service/mcis_service/main.py'
BASE = 'd9662368aa88236afa92df8ed010f79c30ee5dfc'
KNOWN = '6d5069b9d320dcaddab28b95f8ed265bfc567b67'
MODULES = ('colreg.haili5_seed', 'seed.lily_mary', 'seed.yangze22')


def source_at(commit):
    return subprocess.run(['/usr/bin/git','-C',str(ROOT),'show',commit+':'+PATH],
        env={'PATH':'/usr/bin:/bin','GIT_NO_LAZY_FETCH':'1','GIT_CONFIG_NOSYSTEM':'1',
             'GIT_CONFIG_GLOBAL':'/dev/null'},check=True,capture_output=True).stdout.decode()


def seed_import(node):
    return isinstance(node,ast.ImportFrom) and node.level == 1 and node.module in MODULES


def branch(tree):
    function = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='create_app')
    matches = [n for n in function.body if isinstance(n,ast.If)
               and ast.dump(n.test)==ast.dump(ast.parse('settings.seed_demo',mode='eval').body)]
    assert len(matches)==1
    return matches[0]


old, new, known = ast.parse(source_at(BASE)), ast.parse((ROOT/PATH).read_text()), ast.parse(source_at(KNOWN))
old_imports = [n for n in old.body if seed_import(n)]
assert [n.module for n in old_imports] == list(MODULES)
assert not any(seed_import(n) for n in new.body)
# Entire candidate AST equals the old AST with exactly the requested relocation.
expected = deepcopy(old)
expected.body = [n for n in expected.body if not seed_import(n)]
branch(expected).body[:0] = deepcopy(old_imports)
assert ast.dump(new) == ast.dump(expected)
assert ast.dump(branch(new)) == ast.dump(branch(known))
assert len([n for n in ast.walk(new) if seed_import(n)]) == 3


def exercise(tree, enabled):
    events = []
    session, blob = object(), object()
    def callback(label):
        def call(received_session, received_blob):
            assert received_session is session and received_blob is blob
            events.append('call:'+label)
        return call
    dependencies = {name:SimpleNamespace(seed=callback(name)) for name in MODULES}
    def importer(name, globals=None, locals=None, fromlist=(), level=0):
        assert name in dependencies and level==1 and fromlist==('seed',)
        events.append('import:'+name)
        return dependencies[name]
    class Context:
        def __enter__(self):
            events.append('enter')
            return session
        def __exit__(self, *args):
            events.append('exit')
            return False
    # Extract ONLY the three target imports and the seed conditional into a
    # handmade function. No create_app body, config construction or real DB.
    body = deepcopy([n for n in tree.body if seed_import(n)] + [branch(tree)])
    wrapper = ast.parse('def probe(settings, db):\n    pass\n')
    wrapper.body[0].body = body
    namespace = {'__builtins__':{'__import__':importer}}
    exec(compile(ast.fix_missing_locations(wrapper),'<synthetic seed branch>','exec'),namespace)
    namespace['probe'](SimpleNamespace(seed_demo=enabled,blob_dir=blob), SimpleNamespace(session=Context))
    return events


imports = ['import:'+m for m in MODULES]
assert exercise(old,False) == imports  # concrete old eager-load counterexample
assert exercise(new,False) == []
expected_events = imports + ['enter','call:seed.lily_mary','call:colreg.haili5_seed','call:seed.yangze22','exit']
assert exercise(old,True) == exercise(new,True) == expected_events
print('PASS full AST: only three imports relocated; identical known-policy seed branch')
print('PASS false: old 3 fake imports, candidate 0; true: unchanged imports/calls/arguments/context')
print('NOT VERIFIED: actual module imports, transitive closure, environment isolation or startup')
