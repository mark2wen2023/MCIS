"""Actual page/factory AST with handmade routing and file strings. No app import."""
import ast
from pathlib import Path
import runpy
import subprocess
from types import SimpleNamespace as NS
ROOT=Path(__file__).resolve().parents[2]
prior=runpy.run_path(str(ROOT/'tests_acceptance/pilot-audio-imports/check.py'))
factory=prior['prior']; tree=ast.parse((ROOT/'service/mcis_service/local_review_pilot/pages.py').read_text())
raw=(ROOT/'service/mcis_service/local_review_pilot/audio_workbench.html').read_text()
skin=runpy.run_path(str(ROOT/'service/mcis_service/local_review_pilot/workbench_skin.py'))
class TextPath:
    def __init__(self,*a):pass
    def with_name(self,name):
        assert name=='audio_workbench.html';return self
    def read_text(self,**kw):return raw
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_mount_pilot_audio_page')
node.body=[n for n in node.body if not isinstance(n,ast.ImportFrom)]
scope={'Path':TextPath,'__file__':'synthetic','CSS':skin['CSS'],'HTMLResponse':lambda html,**kw:NS(html=html,**kw)}
exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual mount/fake IO>','exec'),scope)
s=factory['setup']();routes=prior['route_scope']()
s.scope.update(APIRouter=routes['APIRouter'],NoStoreRoute=object,receipt_input=object(),
 _mount_audio_imports_only=routes['_mount_audio_imports_only'],_initialize_audio_review_storage=lambda *a,**kw:None,
 _mount_pilot_audio_page=scope['_mount_pilot_audio_page'])
app=s.construct(audio_imports=True,audio_blob_dir=s.scope['Path']('/synthetic'))
paths={(m,r.path) for r in app.routes for m in r.methods}
assert paths==s.scope['ROUTES']|s.scope['AUDIO_ROUTES']
assert not any('/source/' in p or 'tasks' in p or 'download' in p for m,p in paths)
response=factory['endpoint'](app,'/pilot/audio-review')()
assert response.headers=={'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY'}
assert response.html==raw.replace('/* pilot-workbench-skin */',skin['CSS'])
for token in ['240px minmax(0,1fr) 380px','class="side"','class="stage-bar"','class="inspector"','3 询问']:
    assert token in response.html
normal=factory['setup']().construct()
assert '/pilot/audio-review' not in {r.path for r in normal.routes}
# Actual workbench shaper, no URL/query capability source.
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='workbench_page')
exec(compile(ast.Module(body=[node],type_ignores=[]),'<pure shaper>','exec'),scope)
w=(ROOT/'service/mcis_service/local_review_pilot/workbench.html').read_text()
assert 'const audioPageAvailable=false;' in scope['workbench_page'](w,images=False)
assert 'const audioPageAvailable=true;' in scope['workbench_page'](w,images=False,audio=True)
# Legacy page and business handlers remain byte-identical to approved baseline.
for path in ['service/mcis_service/audio_review/app.py','service/mcis_service/audio_review/review.html']:
    old=subprocess.check_output(['git','show','145b163a5c4371b987d5a980b02be3f29956ddcb:'+path],cwd=ROOT)
    assert (ROOT/path).read_bytes()==old
print('PASS actual audio mount + factory AST, default off, same original API routes; legacy audio untouched')
