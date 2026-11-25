"""Real local API/browser plus delayed real response delivery; no production data."""
import os,signal,subprocess,tempfile,time,urllib.request,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent
SHOTS=os.environ.get('W171_SHOTS')  # optional: screenshot dir outside the repo
def shot(page,name):
 if SHOTS:page.wait_for_timeout(50);page.screenshot(path=os.path.join(SHOTS,name+'.png'),full_page=True)
with tempfile.TemporaryDirectory(prefix='w171-accept-') as tmp:
 env={**os.environ,'MCIS_DATA_DIR':tmp+'/data','MCIS_API':'http://127.0.0.1:15971','PYTHONPATH':str(ROOT/'service')}
 back=subprocess.Popen([str(ROOT/'service/.venv/bin/python'),str(HERE/'server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 front=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15972','--strictPort'],cwd=ROOT/'web',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 try:
  for port,path in [(15971,'/api/v1/health'),(15972,'/')]:
   for _ in range(100):
    try:urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',timeout=1);break
    except Exception:time.sleep(.1)
   else:raise RuntimeError('local startup failed')
  with sync_playwright() as p:
   browser=p.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,chromium_sandbox=True,env={**os.environ,'HOME':tmp,'XDG_CONFIG_HOME':tmp+'/config'})
   page=browser.new_page();errors=[];requests=[];held=[];delay={'next':False}
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.on('request',lambda r:requests.append((r.method,r.url)) if '/api/v1/' in r.url else None)
   def intercept(route):
    if delay['next']:
     delay['next']=False
     # Capture genuine backend response; defer only its delivery to this browser.
     reply=route.fetch();held.append((route,reply))
    else:route.continue_()
   page.route('**/access-workbench',intercept)
   page.goto('http://127.0.0.1:15972/#/access?case=CASE-A')
   page.get_by_text('CASE-A-SECRET-CONFIG',exact=True).wait_for()
   assert page.locator('.case-chip b').inner_text()=='CASE-A'
   assert 'case=CASE-A' in page.url
   assert page.get_by_text('当前案号：CASE-A',exact=True).count()==1
   page.get_by_text('本地自报角色，不是真实身份认证。',exact=True).wait_for()
   assert not any('/access-policy' in url for _,url in requests)
   shot(page,'1-case-A-loaded')
   delay['next']=True;page.get_by_role('button',name='刷新权限工作台',exact=True).click()
   for _ in range(100):
    if held:break
    page.wait_for_timeout(20)
   assert held and page.get_by_text('CASE-A-SECRET-CONFIG',exact=True).count()==0
   page.evaluate("location.hash='/access?case=CASE-B'")
   page.get_by_text('CASE-B-SECRET-CONFIG',exact=True).wait_for()
   assert page.locator('.case-chip b').inner_text()=='CASE-B'
   assert 'case=CASE-B' in page.url
   assert page.get_by_text('当前案号：CASE-B',exact=True).count()==1
   route,reply=held.pop();route.fulfill(response=reply)
   page.wait_for_timeout(100)
   assert page.get_by_text('CASE-A-SECRET-CONFIG',exact=True).count()==0
   assert page.get_by_text('CASE-B-SECRET-CONFIG',exact=True).count()==1
   shot(page,'2-case-B-after-stale-A-delivered')
   delay['next']=True;page.get_by_role('button',name='刷新权限工作台',exact=True).click()
   for _ in range(100):
    if held:break
    page.wait_for_timeout(20)
   assert held
   page.evaluate("async()=>{const api=await import('/src/api.ts');api.setIdentity('Public','Independent');}")
   page.get_by_role('alert').wait_for()
   route,reply=held.pop();route.fulfill(response=reply);page.wait_for_timeout(100)
   assert page.get_by_text('CASE-B-SECRET-CONFIG',exact=True).count()==0
   assert page.get_by_text('已返回的权限配置矩阵',exact=True).count()==0
   shot(page,'3-public-denied-after-stale-B-delivered')
   assert all(method=='GET' for method,_ in requests),requests
   assert not any('/access-policy' in url for _,url in requests),requests
   assert not errors,errors
   browser.close()
  print('PASS real browser/API: read-only config, no legacy fallback, refresh clears data, delayed old-case and old-identity responses cannot restore data, role denial, no page errors.')
 finally:
  for proc in (front,back):os.killpg(proc.pid,signal.SIGTERM);proc.wait()
