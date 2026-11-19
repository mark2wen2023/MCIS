"""Fixed non-seed AST only; fake in-memory storage/callbacks, no application imports."""
import ast
import copy
import hashlib
import json
from contextlib import contextmanager, nullcontext
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[2]
paths = {k: ROOT / 'service/mcis_service' / v for k, v in {
    'runs': 'colreg/runs.py', 'router': 'colreg/router.py', 'main': 'main.py'}.items()}
trees = {k: ast.parse(p.read_text()) for k, p in paths.items()}

def extract(tree, names, env):
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes} == set(names)
    mod = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *nodes], type_ignores=[])
    exec(compile(ast.fix_missing_locations(mod), '<fixed non-seed functions>', 'exec'), env)

calls = []
store = {}
def get_doc(_s, _model, _case, key): return copy.deepcopy(store.get(key))
def put_doc(_s, _model, _case, key, value): store[key] = copy.deepcopy(value)
def loader(case):
    calls.append(case)
    return {'B-SYN': ['EV-SYN']}
def create(_s, case, idx, analysis, **kw):
    store['created'] = {'case': case, 'analysis': analysis, **kw}
    idx['runs'].append({'runId': 'R-SYN'})
    idx['currentSha'] = env['_sha'](analysis)
    store['runs'] = copy.deepcopy(idx)
env = dict(copy=copy, hashlib=hashlib, json=json, get_doc=get_doc, put_doc=put_doc,
           ColregAnalysisRow=object(), INDEX_KEY='runs', CURRENT_KEY='current',
           _seed_band_evidence=loader, _create=create)
extract(trees['runs'], ['ensure', '_sha', '_kind_of'], env)
ensure = env['ensure']
seed = {'checks': [{'source': 'Seed'}], 'bands': [{'bandId': 'B-SYN'}]}
for flag in (False, None, True):
    store.clear(); calls.clear(); store['current'] = copy.deepcopy(seed)
    s = NS(info={} if flag is None else {'mcis_colreg_seed_annotations_enabled': flag})
    ensure(s, 'SYN-CASE')
    assert store['created']['analysis'] == seed
    assert calls == (['SYN-CASE'] if flag is True else [])
    assert store['created']['band_evidence'] == ({'B-SYN': ['EV-SYN']} if flag is True else None)
    assert ('未启用' in store['created']['note']) == (flag is not True)
    snapshot = copy.deepcopy(store); ensure(s, 'SYN-CASE')
    assert store == snapshot  # stored versions not rewritten or retroactively annotated
print('PASS enabled/disabled/missing configuration and preserved existing version')
for kind in ('Initial', 'RuleEngine'):
    store.clear(); calls.clear(); store['current'] = {'checks': [{'source': kind}]}
    ensure(NS(info={'mcis_colreg_seed_annotations_enabled': True}), 'SYN-CASE')
    assert not calls and store['created']['band_evidence'] is None
    assert store['created']['note'] == '首次访问时由已有 current 收编'
store.clear(); calls.clear(); ensure(NS(info={}), 'SYN-CASE')
assert not calls and store['runs']['runs'] == []
store['current'] = seed
ensure(NS(info={}), 'SYN-CASE')
assert not calls and store['created']['kind'] == 'External'
print('PASS ordinary, empty and externally changed current without seed callback')

# Execute only the actual contextmanager against wholly synthetic sessions/instances.
@contextmanager
def session():
    yield NS(info={})
renv = {'contextmanager': contextmanager, 'runs': NS(LOCK=nullcontext())}
extract(trees['router'], ['_runs_session'], renv)
for state, expected in [(NS(), False), (NS(colreg_seed_annotations_enabled=False), False),
                        (NS(colreg_seed_annotations_enabled=True), True)]:
    ctx = NS(db=NS(session=session), request=NS(app=NS(state=state)))
    with renv['_runs_session'](ctx) as s:
        assert s.info['mcis_colreg_seed_annotations_enabled'] is expected
print('PASS synthetic instance-to-session wiring')

# Static checks do not import/execute main, router, seeds, ORM, roles or HTTP.
main = next(n for n in trees['main'].body if isinstance(n, ast.FunctionDef) and n.name == 'create_app')
assignments = [n for n in main.body if isinstance(n, ast.Assign)]
assert any(ast.unparse(n) == 'colreg_seed_annotations_enabled = settings.seed_demo is True' for n in assignments)
assert any(ast.unparse(n) == 'app.state.colreg_seed_annotations_enabled = colreg_seed_annotations_enabled' for n in assignments)
assert not any(isinstance(n, ast.ImportFrom) and n.module == 'seed_annotations' for n in trees['runs'].body)
wrapper = next(n for n in trees['runs'].body if isinstance(n, ast.FunctionDef) and n.name == '_seed_band_evidence')
assert any(isinstance(n, ast.ImportFrom) and n.module == 'seed_annotations' for n in wrapper.body)
for n in trees['router'].body:
    if isinstance(n, ast.FunctionDef) and any(isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and isinstance(x.func.value, ast.Name) and x.func.value.id == 'runs' and x.func.attr in {'ensure','get_run','activate','list_runs','add_engine_run'} for x in ast.walk(n)):
        assert any(isinstance(x, ast.With) and any(isinstance(i.context_expr, ast.Call) and isinstance(i.context_expr.func, ast.Name) and i.context_expr.func.id == '_runs_session' for i in x.items) for x in ast.walk(n)), n.name
print('PASS static snapshot/lazy import/request wiring; COMPLETE')
