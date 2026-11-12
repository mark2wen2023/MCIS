"""Real HTTP with temporary synthetic-only DB, no inference/model/real reports."""
import os,signal,subprocess,tempfile,time,urllib.request,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];C='CASE-2026-DEMO-LILY-MARY';procs=[]
try:
 with tempfile.TemporaryDirectory(prefix='w203-synthetic-') as data:
  code="""from pathlib import Path
import os,uvicorn
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.seed.lily_mary import seed
app=create_app(Settings(data_dir=Path(os.environ['MCIS_DATA_DIR']),seed_demo=False))
with app.state.db.session() as s:seed(s,app.state.settings.blob_dir)
uvicorn.run(app,host='127.0.0.1',port=18803)
"""
  env={**os.environ,'MCIS_DATA_DIR':data,'MCIS_AGENT_BASE_URL':'','MCIS_AGENT_MODEL':''}
  procs.append(subprocess.Popen([str(ROOT/'service/.venv/bin/python'),'-c',code],cwd=ROOT/'service',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True))
  procs.append(subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15804','--strictPort'],cwd=ROOT/'web',env={**os.environ,'MCIS_API':'http://127.0.0.1:18803'},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True))
  for url in ['http://127.0.0.1:18803/api/v1/agents','http://127.0.0.1:15804']:
   for _ in range(100):
    try:urllib.request.urlopen(url,timeout=1);break
    except Exception:time.sleep(.1)
   else:raise AssertionError('server unavailable')
  def audit_count():
   r=urllib.request.Request('http://127.0.0.1:18803/api/v1/cases/'+C+'/audit',headers={'X-MCIS-Role':'LeadInvestigator'})
   return len(json.load(urllib.request.urlopen(r)))
  before=audit_count()
  with sync_playwright() as pw:
   b=pw.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox']);p=b.new_page(viewport={'width':1280,'height':900});p.set_default_timeout(8000)
   writes=[];p.on('request',lambda r:writes.append(r.url) if r.method not in ('GET','HEAD') else None)
   p.add_init_script("localStorage.setItem('mcis.role','LeadInvestigator')");p.goto('http://127.0.0.1:15804/#/agents?case='+C)
   p.get_by_text('待审 2 / 全部 2',exact=False).wait_for();assert p.get_by_text('未连接',exact=True).count()==6
   assert p.get_by_role('link',name='前往原笔录与人工审核').count()==0
   p.get_by_role('button',name='重新读取登记与队列').click();p.get_by_text('待审 2 / 全部 2',exact=False).wait_for()
   p.screenshot(path=str(ROOT/'logs/W203-desktop-private.png'),full_page=True)
   p.set_viewport_size({'width':390,'height':844});p.wait_for_timeout(100);assert p.evaluate('document.documentElement.scrollWidth<=innerWidth');p.screenshot(path=str(ROOT/'logs/W203-mobile-private.png'),full_page=True)
   p.evaluate("async()=>{const a=await import('/src/api.ts');a.setIdentity('Investigator')}");p.get_by_text('后端拒绝当前身份或案件策略。',exact=False).wait_for();assert 'AD-001' not in p.locator('body').inner_text()
   p.evaluate("async()=>{const a=await import('/src/api.ts');a.setIdentity('Public')}");p.get_by_text('当前角色不展示内部模型',exact=False).wait_for();assert 'none' not in p.locator('body').inner_text()
   assert writes==[];b.close()
  assert audit_count()==before
 print('W20.3 real HTTP synthetic browser: six disconnected states, actual draft queue, unsupported old drafts not linked, refresh no writes/audit,default Investigator403/Public hidden,desktop/mobile passed')
finally:
 for p in procs:os.killpg(p.pid,signal.SIGTERM);p.wait()
