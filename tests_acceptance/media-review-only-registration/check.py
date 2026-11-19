"""AST + extracted registration functions with handmade dependencies only.
Never imports product modules, FastAPI, SQLAlchemy, handlers, or task modules.
"""
import ast
import builtins
from pathlib import Path
import subprocess
from types import SimpleNamespace

BASE = 'c57d12b1ef694fb44c3b57d185ecbadde1274ab4'
def need(ok, message):
    if not ok: raise AssertionError(message)
def dump(tree): return ast.dump(tree, include_attributes=False)

for media, runtime in [('image', 'image_ocr_runtime'), ('audio', 'audio_asr_runtime')]:
    path = f'service/mcis_service/{media}_review/app.py'
    original = ast.parse(subprocess.check_output(['git', 'show', f'{BASE}:{path}'], text=True))
    source = Path(path).read_text()
    current = ast.parse(source)
    limited = f'_register_{media}_review_only'
    mount = f'_mount_{media}_review_routes'
    initialize = f'_initialize_{media}_review_storage'
    register = f'register_{media}_review'
    # Whole module comparison after reversing exactly the permitted changes.
    normalized = ast.parse(source)
    normalized.body = [n for n in normalized.body if not isinstance(n, ast.FunctionDef) or n.name != limited]
    node = next(n for n in normalized.body if isinstance(n, ast.FunctionDef) and n.name == mount)
    guard = node.body[1]
    arg = 'tasks_router' if media == 'image' else 'tasks'
    need(dump(guard.test) == dump(ast.parse(f'{arg} is not None', mode='eval').body), 'only explicit None excludes task router')
    need(len(guard.body) == 1 and not guard.orelse, 'single task mount condition')
    node.body[1:2] = guard.body
    need(dump(normalized) == dump(original), 'all other AST, guards, handlers, SQL, factory and full registration unchanged')
    old_init = next(n for n in original.body if isinstance(n, ast.FunctionDef) and n.name == initialize)
    new_init = next(n for n in current.body if isinstance(n, ast.FunctionDef) and n.name == initialize)
    old_source = subprocess.check_output(['git', 'show', f'{BASE}:{path}'], text=True)
    need(ast.get_source_segment(old_source, old_init) == ast.get_source_segment(source, new_init), 'storage initialization byte identical')
    limited_node = next(n for n in current.body if isinstance(n, ast.FunctionDef) and n.name == limited)
    need(not any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(limited_node)), 'limited registration imports nothing')
    endpoints = [(n.name, ast.unparse(d)) for n in current.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for d in n.decorator_list if ast.unparse(d).startswith('router.')]
    expected = ['register', 'list_runs', 'read', 'review'] if media == 'image' else ['source_context', 'attach', 'listing', 'get', 'revise']
    need([n for n, _ in endpoints] == expected, 'exact existing review endpoint set')

    def harness(tree, failure=None):
        events = []
        def event(label, detail=None):
            events.append((label, detail))
            if failure == label: raise RuntimeError('synthetic ' + label)
        class State:
            def __init__(self): object.__setattr__(self, 'db', SimpleNamespace(engine=Engine()))
            def __setattr__(self, k, v): event('state:' + k, v); object.__setattr__(self, k, v)
        class Connection:
            def __enter__(self): event('enter'); return self
            def execute(self, value): event('execute', value)
            def __exit__(self, *args): event('exit', args[0].__name__ if args[0] else None)
        class Engine:
            def begin(self): event('begin'); return Connection()
        class App:
            def __init__(self): self.state = State()
            def include_router(self, r): event('include:' + r)
            def get(self, path, **kw):
                event('get:' + path, kw)
                def decorate(fn): event('decorate:' + path, fn.__name__); return fn
                return decorate
        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            need((name, fromlist, level) in [('tasks', ('router',), 1), ('', ('tasks',), 1)], 'unexpected import forbidden')
            event('import-task')
            return SimpleNamespace(router='task') if name == 'tasks' else SimpleNamespace(tasks=SimpleNamespace(router='task'))
        env = {'__builtins__': {**vars(builtins), '__import__': fake_import},
               'Storage': SimpleNamespace(metadata=SimpleNamespace(create_all=lambda engine: event('create_all'))),
               'sql': lambda value: value, 'router': 'review', 'HTMLResponse': 'html-response-type'}
        selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {mount, initialize, register, limited}]
        exec(compile(ast.Module(body=selected, type_ignores=[]), '<only extracted registration functions>', 'exec'), env)
        return App(), env, events

    kwargs = {'ocr_runtime' if media == 'image' else 'sensevoice_runtime': 'synthetic-runtime'}
    # Existing path: same complete order and propagation for normal and failures.
    points = [None, 'import-task', 'create_all', 'begin', 'enter', 'execute', 'include:review', 'include:task', f'get:/{media}-review-lab', f'decorate:/{media}-review-lab']
    if media == 'image': points += ['get:/image-review-lab/preview.js', 'decorate:/image-review-lab/preview.js']
    for failure in points:
        traces = []
        for tree in [original, current]:
            app, env, events = harness(tree, failure)
            error = None
            try: need(env[register](app, **kwargs) is app, 'returns app')
            except RuntimeError as exc: error = str(exc)
            need((error is not None) == (failure is not None), 'expected failure propagated')
            traces.append((events, error))
        need(traces[0] == traces[1], 'full registration sequence differs')
    # New real function body, fake dependencies: all storage and review/page operations,
    # exactly no task import/mount. No handler or page callback invoked.
    for failure in [None, 'create_all', 'begin', 'enter', 'execute', 'include:review', f'get:/{media}-review-lab']:
        app, env, events = harness(current, failure)
        error = None
        try: need(env[limited](app) is app, 'limited returns app')
        except RuntimeError as exc: error = str(exc)
        need((error is not None) == (failure is not None), 'limited failure propagation')
        need(not any(k in ('import-task', 'include:task') for k, _ in events), 'task surface excluded')
        need(getattr(app.state, runtime) is None, 'model runtime explicitly disabled')
        need(getattr(app.state, media + '_review_registered', False) == (failure is None), 'flag only after success')
        if failure is None:
            old_app, old_env, full = harness(original)
            old_env[register](old_app, **{next(iter(kwargs)): None})
            need(events == [e for e in full if e[0] not in ('import-task', 'include:task')], 'limited keeps every non-task setup operation and order')
    # Either registration prevents a second/mixed registration before any side effect.
    for first in [register, limited]:
        for second in [register, limited]:
            app, env, events = harness(current)
            env[first](app)
            before = list(events)
            try: env[second](app)
            except ValueError as exc: need(str(exc) == media + ' review already registered', 'same duplicate error')
            else: raise AssertionError('duplicate accepted')
            need(events == before, 'duplicate has no setup side effect')
    print(media + ': full-module AST/byte-preserved storage, full/limited registration and synthetic failure/duplicate checks PASS')
print('No app/FastAPI/ORM/task import, endpoint execution, SQL execution, filesystem data or network access.')
