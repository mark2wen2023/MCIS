"""Only AST-extracted mounts, pure renderer and handmade app/path/response objects."""
import ast
import json
from pathlib import Path
import subprocess
import tempfile
import os
from types import SimpleNamespace
BASE = 'af80e1eaf37716df6e21267d10c4c975407baf24'
def need(ok, why):
    if not ok: raise AssertionError(why)
def dump(x): return ast.dump(x, include_attributes=False)
renderer_source = Path('service/mcis_service/_review_page.py').read_text()
renderer_ast = ast.parse(renderer_source)
need(not any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(renderer_ast)), 'renderer must have no imports')
env = {}
exec(compile(renderer_ast, '<pure page renderer>', 'exec'), env)
render = env['_review_page']
pages = {}
for media, taskarg in [('image', 'tasks_router'), ('audio', 'tasks')]:
    path = f'service/mcis_service/{media}_review/app.py'
    original = ast.parse(subprocess.check_output(['git', 'show', f'{BASE}:{path}'], text=True))
    tree = ast.parse(Path(path).read_text())
    # Reverse only the pure helper import and page-response wrapping; all guards,
    # handlers, register calls, SQL, and dynamic binding checks must match baseline.
    normalized = ast.parse(Path(path).read_text())
    normalized.body = [n for n in normalized.body if not (isinstance(n, ast.ImportFrom) and n.module == '_review_page')]
    class Unwrap(ast.NodeTransformer):
        def visit_Call(self, n):
            if isinstance(n.func, ast.Name) and n.func.id == '_review_page':
                need(len(n.args)==1 and len(n.keywords)==1 and n.keywords[0].arg=='task_routes', 'fixed helper contract')
                need(dump(n.keywords[0].value)==dump(ast.parse(taskarg+' is not None', mode='eval').body), 'registration closure only')
                return n.args[0]
            return self.generic_visit(n)
    normalized = Unwrap().visit(normalized)
    need(dump(normalized)==dump(original), 'non-page product AST unchanged')
    html = Path(f'service/mcis_service/{media}_review/review.html').read_text()
    need(render(html,task_routes=True)==html, 'full rendering byte unchanged')
    pages[media] = {}
    for enabled in [False, True]:
        routes = {}; included=[]
        class App:
            def include_router(self,r): included.append(r)
            def get(self,path,**kw):
                def decorate(fn): routes[path]=fn; return fn
                return decorate
        class FakePath:
            def __init__(self,*args): pass
            def with_name(self,name): need(name=='review.html','only HTML callback expected'); return self
            def read_text(self): return html
        def response(value,**kw):
            need(kw=={'headers':{'Cache-Control':'no-store'}}, 'response metadata unchanged')
            return value
        mount=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==f'_mount_{media}_review_routes')
        scope={'router':'review','HTMLResponse':response,'Response':object,'Path':FakePath,'__file__':'synthetic-path','_review_page':render}
        exec(compile(ast.Module(body=[mount],type_ignores=[]),'<mount only>', 'exec'),scope)
        task = ('task' if media=='image' else SimpleNamespace(router='task')) if enabled else None
        scope[mount.name](App(),task)
        need(included==(['review','task'] if enabled else ['review']), 'exact task surface')
        result=routes[f'/{media}-review-lab']()
        need(('const taskRoutesAvailable=true;' in result)==enabled,'actual response capability')
        need(('data-task-controls hidden inert' in result)==(not enabled),'limited HTML hidden before JS')
        pages[media]['full' if enabled else 'limited']=result
    print(media+': AST, registration-derived response and full/limited mounts PASS')
# Test actual shaped HTML in Node, without running any application imports or I/O callbacks.
subprocess.run(['node','tests_acceptance/media-review-capability/page.cjs'],input=json.dumps(pages),text=True,check=True)
# Existing explicit reopen tests run against limited server-shaped pages as well.
with tempfile.TemporaryDirectory(prefix='mcis-capability-source-') as tmp:
    for media in ['image','audio']:
        p=Path(tmp)/f'{media}.html';p.write_text(pages[media]['limited'])
        for suite in ['url-reopen', 'reopen-address']:
            subprocess.run(['node','--test',f'tests_acceptance/{media}-{suite}/page.test.cjs'],env={**os.environ,f'{media.upper()}_PAGE_SOURCE':str(p)},check=True)
