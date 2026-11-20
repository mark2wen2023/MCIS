"""Pure source page shapers + fake registration; never import application packages."""
import ast
import runpy
from pathlib import Path
import subprocess
import shutil
import tempfile
from types import SimpleNamespace as NS
NODE=shutil.which('node')
if NODE is None:raise RuntimeError('offline Node dependency missing')
ROOT=Path(__file__).resolve().parents[2]
def git_source(path):return subprocess.check_output(['git','show','825ef7e:'+path],cwd=ROOT,text=True)
def definitions(source,scope,names=None):
    tree=ast.parse(source)
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and (names is None or n.name in names)]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<reviewed pure AST>','exec'),scope)
skin=runpy.run_path(str(ROOT/'service/mcis_service/local_review_pilot/workbench_skin.py'))
scope={'CSS':skin['CSS'],'image_shell':skin['image_shell']}
definitions(git_source('service/mcis_service/_review_page.py'),scope)
source=(ROOT/'service/mcis_service/local_review_pilot/pages.py').read_text()
definitions(source,scope,['workbench_page','image_page'])
raw=(ROOT/'service/mcis_service/image_review/review.html').read_text()
html=scope['image_page'](raw)
workbench=(ROOT/'service/mcis_service/local_review_pilot/workbench.html').read_text()
assert scope['workbench_page'](workbench,images=False)==workbench.replace('/* pilot-workbench-skin */',skin['CSS'])
assert 'const imagePageAvailable=true;' in scope['workbench_page'](workbench,images=True)
for marker in ['const originalRoutesAvailable=true;','const pilotSession=false;','<section class="image-pane"']:
    try:scope['image_page'](raw.replace(marker,''))
    except ValueError:pass
    else:raise AssertionError('missing capability accepted')
# Actual mount body, no real Path/response/app imports. Only predefined source strings.
class FakePath:
    def __init__(self,*a):self.name=''
    @property
    def parents(self):return [self,self]
    def __truediv__(self,name):p=FakePath();p.name=name;return p
    def read_text(self,**kw):
        return {'review.html':raw,'preview.js':'// synthetic asset'}[self.name]
class App:
    def __init__(self):self.routes=[]
    def get(self,path,**kw):
        def register(fn):self.routes.append((path,fn));return fn
        return register
node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='_mount_pilot_image_pages')
node.body=[n for n in node.body if not isinstance(n,ast.ImportFrom)]
scope.update(Path=FakePath,__file__='synthetic',HTMLResponse=lambda content,**kw:NS(content=content,**kw),Response=lambda content,**kw:NS(content=content,**kw))
exec(compile(ast.Module(body=[node],type_ignores=[]),'<real mount fake adapters>','exec'),scope)
app=App();scope['_mount_pilot_image_pages'](app)
assert [p for p,f in app.routes]==['/pilot/image-review','/image-review-lab/preview.js']
assert app.routes[0][1]().content==html
assert app.routes[1][1]().media_type=='text/javascript'
with tempfile.TemporaryDirectory(prefix='mcis-pilot-pages-') as temp:
    page=Path(temp)/'image.html';page.write_text(html)
    subprocess.run([NODE,str(ROOT/'tests_acceptance/pilot-pages/page.cjs'),str(page)],cwd=ROOT,env={},check=True)
    # Existing fixed source test, only synthetic inline DOM/history/memoryRequest.
    test=Path(temp)/'reopen.cjs';test.write_text(git_source('tests_acceptance/image-reopen-address/page.test.cjs'))
    subprocess.run([NODE,'--test',str(test)],cwd=ROOT,env={'IMAGE_PAGE_SOURCE':str(page)},check=True)
    original=Path(temp)/'original.html';original.write_text(raw)
    subprocess.run([NODE,'--test',str(test)],cwd=ROOT,env={'IMAGE_PAGE_SOURCE':str(original)},check=True)
print('PASS source shapers, marker rejection, real mount AST; no runtime factory or network')
