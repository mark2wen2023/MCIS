"""Real FastAPI + real C# CPA. Separate delayed/error response probes use interception."""
import os,subprocess,tempfile,time,urllib.request,signal,json,sqlite3
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
env={**os.environ,'PYTHONPATH':str(ROOT/'service'),'MCIS_DOTNET':os.environ.get('MCIS_DOTNET',str(Path.home()/'.dotnet/dotnet')),'MCIS_API':'http://127.0.0.1:15861'}
with tempfile.TemporaryDirectory(prefix='mcis-w122-browser-') as d:
 env['MCIS_DATA_DIR']=d
 log=open('/tmp/mcis-w122-browser.log','w')
 service=subprocess.Popen([str(ROOT/'service/.venv/bin/python'),str(Path(__file__).with_name('current-analysis-w122-server.py'))],env=env,stdout=log,stderr=log,start_new_session=True)
 web=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15862','--strictPort'],cwd=ROOT/'web',env=env,stdout=log,stderr=log,start_new_session=True)
 try:
  for url in ['http://127.0.0.1:15861/api/v1/health','http://127.0.0.1:15862']:
   for _ in range(100):
    try:urllib.request.urlopen(url,timeout=1);break
    except Exception:time.sleep(.1)
   else:raise AssertionError('server did not start: '+url)
  with sync_playwright() as pw:
   b=pw.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox']);p=b.new_page(viewport={'width':1440,'height':1000});p.set_default_timeout(12000)
   p.add_init_script("localStorage.setItem('mcis.role','LeadInvestigator')")
   errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
   p.goto('http://127.0.0.1:15862/#/analysis?case=SYNTHETIC-W122')
   p.get_by_label('本船',exact=True).select_option('A');p.get_by_label('目标船',exact=True).select_option('B')
   calls=[];p.on('request',lambda r:calls.append(r.url) if '/analysis/current?' in r.url else None)
   btn=p.get_by_role('button',name='计算同刻已存点',exact=True);btn.evaluate('(el)=>{el.click();el.click()}')
   panel=p.get_by_role('region',name='当前案计算结果');panel.wait_for();assert len(calls)==1
   assert '记录为实测' in panel.inner_text() and '记录为插值' in panel.inner_text();assert panel.locator('tbody tr').count()==100
   assert p.evaluate('window.pwned') is None and panel.locator('img').count()==0
   panel.get_by_role('button',name='下一页').click();assert '2 / 3 页' in panel.inner_text();panel.get_by_role('button',name='下一页').click();assert panel.locator('tbody tr').count()==5
   panel.get_by_text('输入标识、计算假设与可追溯边界',exact=True).click();assert '位置参考点未知' in panel.inner_text()
   Path('/tmp/w122-shots').mkdir(exist_ok=True)
   p.screenshot(path='/tmp/w122-shots/current-1440.png',full_page=True)
   p.set_viewport_size({'width':1920,'height':1080});p.screenshot(path='/tmp/w122-shots/current-1920.png',full_page=True)
   assert p.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
   p.get_by_label('起始相对秒',exact=True).fill('300');assert panel.count()==0;btn.click();panel.wait_for();assert '没有可配对同刻点' in panel.inner_text()
   p.get_by_label('起始相对秒',exact=True).fill('');p.get_by_label('结束相对秒',exact=True).fill('0');btn.click();panel.wait_for();assert panel.locator('tbody tr').count()==1
   # Actual current endpoint response is held after completion; navigate away before delivery.
   held=[]
   def delay(route):held.append((route,route.fetch()))
   p.route('**/analysis/current?*',delay);btn.click()
   for _ in range(100):
    p.wait_for_timeout(50)
    if held:break
   assert held;p.evaluate("location.hash='#/analysis?case=EMPTY-W122'");p.get_by_label('本船',exact=True).select_option('A')
   route,response=held.pop();route.fulfill(response=response);p.wait_for_timeout(150);assert panel.count()==0
   p.unroute('**/analysis/current?*',delay);p.get_by_label('目标船',exact=True).select_option('B');btn.click();panel.wait_for();assert '没有可配对同刻点' in panel.inner_text()
   p.go_back();p.get_by_label('本船',exact=True).select_option('A');p.get_by_label('目标船',exact=True).select_option('B');assert panel.count()==0;btn.click();panel.wait_for()
   # Current role revocation is enforced by real service on repeat computation.
   db=sqlite3.connect(str(Path(d)/'browser.db'))
   policy={'matrix':{'LeadInvestigator':{'ais_sim':'Deny'}}}
   db.execute("INSERT INTO access_policies (case_id,key,doc,created_utc,updated_utc) VALUES (?,?,?,?,?)",('SYNTHETIC-W122','policy',json.dumps(policy),'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z'));db.commit();db.close()
   btn.click();p.get_by_role('alert').filter(has_text='当前身份无权').wait_for();assert panel.count()==0
   assert not errors,errors
   b.close()
  print('W12.2 real browser: C# calculation, 205 rows/pagination, provenance/escape, empty, input invalidation, duplicate click, held response/case/back, real permission revocation,1440/1920 screenshots passed')
 finally:
  for proc in [web,service]:os.killpg(proc.pid,signal.SIGTERM);proc.wait()
  log.close()
