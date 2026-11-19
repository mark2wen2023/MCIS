"""Offline AST/extracted-function check. No application or third-party imports."""
import ast
import asyncio
import copy
from pathlib import Path
import subprocess
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
BASE = '1366168e77c348a2ae061ef4a885649286e68e35'
MAIN = 'service/mcis_service/main.py'
old = ast.parse(subprocess.check_output(['git', 'show', f'{BASE}:{MAIN}'], cwd=ROOT, text=True))
new = ast.parse((ROOT / MAIN).read_text())
shell_tree = ast.parse((ROOT / 'service/mcis_service/_app_shell.py').read_text())
def function(tree, name):
    return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
def dump(n):
    return ast.dump(n, include_attributes=False)
o = function(old, 'create_app'); n = function(new, 'create_app')
h = function(shell_tree, '_create_app_shell')
expanded = copy.deepcopy(n)
slot = next(i for i, x in enumerate(expanded.body) if isinstance(x, ast.Assign) and isinstance(x.value, ast.Call) and isinstance(x.value.func, ast.Name) and x.value.func.id == '_create_app_shell')
expanded.body[slot:slot+1] = copy.deepcopy(h.body[:-1])
assert dump(expanded) == dump(o), 'original full create_app AST changed'
assert dump(h.body[-1]) == dump(ast.parse('return app').body[0])
allowed = {'__future__', 'fastapi', 'fastapi.exceptions', 'fastapi.middleware.cors', 'fastapi.responses', None}
assert all(x.module in allowed for x in shell_tree.body if isinstance(x, ast.ImportFrom))
assert not any(isinstance(x, ast.Import) for x in ast.walk(shell_tree))
assert all(isinstance(x, (ast.Expr, ast.ImportFrom, ast.FunctionDef)) for x in shell_tree.body)
# Only compile extracted functions; seed import statements are removed and names
# supplied as handwritten fakes. No original module top-level code is executed.
class StripImports(ast.NodeTransformer):
    def visit_ImportFrom(self, node):
        return ast.Pass()
def run(fn, seeded, fail):
    events = []
    def event(name, *args):
        events.append((name, args))
        if name == fail:
            raise RuntimeError('synthetic stop')
    class App:
        def __init__(self, **kw):
            event('app', kw); self.state = SimpleNamespace(); self.handlers = {}; self.routes = {}
        def add_middleware(self, cls, **kw): event('cors', cls, kw)
        def exception_handler(self, cls):
            def register(cb): self.handlers[cls] = cb; event('handler', cls.__name__); return cb
            return register
        def get(self, path, **kw):
            def register(cb): self.routes[path] = cb; event('route', path, kw); return cb
            return register
        def include_router(self, router): event('router', router)
    class HTTPException(Exception):
        def __init__(self, status_code, detail): self.status_code = status_code; self.detail = detail
    class RequestValidationError(Exception):
        def errors(self): return [{'loc': ('body', 'synthetic'), 'msg': 'synthetic error'}]
    class Directory:
        def __init__(self, name): self.name = name
        def mkdir(self, **kw): event(self.name, kw)
    class DB:
        def __init__(self, url): event('db', url)
        def create_all(self): event('tables')
        def session(self): return self
        def __enter__(self): event('session-enter'); return 'synthetic-session'
        def __exit__(self, *args): event('session-exit')
    settings = SimpleNamespace(data_dir=Directory('data-dir'), blob_dir=Directory('blob-dir'), resolved_db_url='synthetic-url', seed_demo=seeded)
    def seed(name):
        return lambda s, blob: event(name, s, blob.name)
    ns = dict(FastAPI=App, HTTPException=HTTPException, RequestValidationError=RequestValidationError,
              Request=object, CORSMiddleware='synthetic-cors', JSONResponse=lambda **kw: kw,
              __version__='synthetic-version', Settings=lambda: settings, Database=DB,
              seed=seed('seed-lily'), seed_haili5=seed('seed-haili'), seed_yangze22=seed('seed-yangze'))
    for node in ast.walk(o):
        if isinstance(node, ast.Name) and node.id.endswith('_router'): ns[node.id] = node.id
    funcs = [copy.deepcopy(h), StripImports().visit(copy.deepcopy(fn))]
    # Remove annotations to avoid any actual type dependency.
    for f in funcs:
        f.returns = None
        for a in f.args.args: a.annotation = None
    exec(compile(ast.fix_missing_locations(ast.Module(body=funcs, type_ignores=[])), '<synthetic-functions>', 'exec'), ns)
    app = None
    try: app = ns['create_app'](settings)
    except RuntimeError as exc: assert str(exc) == 'synthetic stop'
    if fail:
        assert app is None and not any(e[0] == 'app' for e in events)
        return events, None
    assert app.state.settings is settings and isinstance(app.state.db, DB) and app.state.sim_states == {}
    callbacks = [app.routes['/api/v1/health'](),
        asyncio.run(app.handlers[HTTPException](None, HTTPException(418, {'code': 'synthetic'}))),
        asyncio.run(app.handlers[HTTPException](None, HTTPException(409, 'synthetic message'))),
        asyncio.run(app.handlers[RequestValidationError](None, RequestValidationError()))]
    assert callbacks == [{'status':'ok','service':'mcis-service','version':'synthetic-version'},
        {'status_code':418,'content':{'code':'synthetic'}},
        {'status_code':409,'content':{'code':'HTTP_409','message':'synthetic message'}},
        {'status_code':422,'content':{'code':'VALIDATION_ERROR','message':'请求参数不合法','detail':[{'loc':['body','synthetic'],'msg':'synthetic error'}]}}]
    return events, callbacks
for seeded, fail in [(False,None),(True,None),(False,'data-dir'),(False,'db'),(False,'tables'),(True,'seed-haili')]:
    assert run(o,seeded,fail) == run(n,seeded,fail)
    print('PASS old/new assembly', seeded, fail)
print('PASS complete expanded AST; fake state/CORS/error/health/router order. No real app imported.')
