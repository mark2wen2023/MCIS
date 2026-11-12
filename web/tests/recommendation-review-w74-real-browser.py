"""Actual loopback HTTP + synthetic-only SQLite; no model or external sending."""
import os,signal,subprocess,tempfile,time,urllib.request,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];C='CASE-2026-DEMO-LILY-MARY';procs=[]
try:
 with tempfile.TemporaryDirectory(prefix='w74-synthetic-') as data:
  code="""from pathlib import Path
import os,uvicorn
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.seed.lily_mary import seed,CASE_ID
from mcis_service.db import get_doc,put_doc
from mcis_service.recommendations.models import RecommendationRow
from mcis_service.audit import service as audit
app=create_app(Settings(data_dir=Path(os.environ['MCIS_DATA_DIR']),seed_demo=False))
with app.state.db.session() as s:
 seed(s,app.state.settings.blob_dir)
 d=get_doc(s,RecommendationRow,CASE_ID,'SR-2026-03')
 d['body']='SYNTHETIC_FULL_BODY\\n<script>window.BAD=true</script>'
 d['responses']=[{'party':'合成回复方'+str(i),'text':'SYNTHETIC_REPLY_'+str(i),'utc':'2026-11-01T00:00:00Z'} for i in range(12)]
 put_doc(s,RecommendationRow,CASE_ID,d['id'],d)
 audit.append(s,case_id=CASE_ID,operator='合成操作员',role='LeadInvestigator',action='safetyrec.update',category='SafetyRec',command='SYNTHETIC_REVIEW_AUDIT',after='合成摘要',entity_type='recommendation',entity_id=d['id'])
uvicorn.run(app,host='127.0.0.1',port=18875)
"""
  procs.append(subprocess.Popen([str(ROOT/'service/.venv/bin/python'),'-c',code],cwd=ROOT/'service',env={**os.environ,'MCIS_DATA_DIR':data},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True))
  procs.append(subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15875','--strictPort'],cwd=ROOT/'web',env={**os.environ,'MCIS_API':'http://127.0.0.1:18875'},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True))
  for url in ['http://127.0.0.1:18875/api/v1/agents','http://127.0.0.1:15875']:
   for _ in range(100):
    try:urllib.request.urlopen(url,timeout=1);break
    except Exception:time.sleep(.1)
   else:raise AssertionError('server unavailable')
  def audit_count():return len(json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18875/api/v1/cases/'+C+'/audit',headers={'X-MCIS-Role':'LeadInvestigator'}))))
  before=audit_count()
  with sync_playwright() as pw:
   b=pw.chromium.launch(executable_path=os.environ['MCIS_BROWSER_BIN'],headless=True,args=['--no-sandbox']);p=b.new_page(viewport={'width':1440,'height':950});p.set_default_timeout(8000)
   requests=[];p.on('request',lambda r:requests.append((r.method,r.url)) if '/api/v1/' in r.url else None)
   p.add_init_script("localStorage.setItem('mcis.role','LeadInvestigator')");p.goto('http://127.0.0.1:15875/#/recs?case='+C)
   panel=p.get_by_role('region',name='安全建议只读核查');panel.wait_for()
   assert panel.get_by_text('SYNTHETIC_FULL_BODY',exact=False).count()==0
   panel.get_by_role('button',name='读取正文与登记回复').click();panel.get_by_text('SYNTHETIC_FULL_BODY',exact=False).wait_for();assert not p.evaluate('Boolean(window.BAD)')
   assert panel.get_by_text('SYNTHETIC_REPLY_0',exact=True).count()==1 and panel.get_by_text('SYNTHETIC_REPLY_11',exact=True).count()==0
   panel.get_by_role('button',name='下一组回复').click();panel.get_by_text('SYNTHETIC_REPLY_11',exact=True).wait_for()
   panel.get_by_role('button',name='读取审计摘要').click();panel.get_by_text('SYNTHETIC_REVIEW_AUDIT',exact=False).wait_for()
   panel.get_by_role('button',name='重新读取完整内容').click();panel.get_by_text('SYNTHETIC_FULL_BODY',exact=False).wait_for();assert panel.get_by_text('SYNTHETIC_REPLY_0',exact=True).count()==1;assert panel.get_by_text('SYNTHETIC_REVIEW_AUDIT',exact=False).count()==0
   panel.evaluate("e=>e.scrollIntoView({block:'start'})");p.screenshot(path=str(ROOT/'logs/W74-reader-desktop-private.png'))
   p.set_viewport_size({'width':390,'height':844});p.wait_for_timeout(100)
   assert p.evaluate('document.documentElement.scrollWidth<=innerWidth');assert panel.bounding_box()['width']<=390
   panel.screenshot(path=str(ROOT/'logs/W74-reader-mobile-private.png'))
   panel.get_by_role('button',name='关闭核查').click();assert panel.get_by_text('SYNTHETIC_FULL_BODY',exact=False).count()==0
   p.evaluate("async()=>{const a=await import('/src/api.ts');a.setIdentity('Investigator')}");p.get_by_text('后端错误：完整安全建议或征求意见内容不可访问',exact=True).wait_for();assert p.get_by_text('SYNTHETIC_FULL_BODY',exact=False).count()==0
   p.evaluate("async()=>{const a=await import('/src/api.ts');a.setIdentity('Public')}");p.get_by_text('后端错误：完整安全建议或征求意见内容不可访问',exact=True).wait_for();assert p.get_by_text('SYNTHETIC_REPLY_',exact=False).count()==0
   assert all(m=='GET' for m,u in requests);b.close()
  assert audit_count()==before
 print('W7.4 real HTTP browser: current content,12 replies pagination,escaped text,separate audit,refresh/close clearing,actual W7ACCESS identity denials,GET-only and no audit mutation passed')
finally:
 for p in procs:os.killpg(p.pid,signal.SIGTERM);p.wait()
