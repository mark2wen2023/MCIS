"""Real synthetic service browser; only delivery delay is intercepted."""
import os,signal,subprocess,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent
with tempfile.TemporaryDirectory(prefix='w162-browser-') as tmp:
 env={**os.environ,'MCIS_DATA_DIR':tmp+'/data','MCIS_API':'http://127.0.0.1:15952','PYTHONPATH':str(ROOT/'service')}
 back=subprocess.Popen([str(ROOT/'service/.venv/bin/python'),str(HERE/'server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 front=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15953','--strictPort'],cwd=ROOT/'web',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 try:
  for port,path in [(15952,'/api/v1/health'),(15953,'/')]:
   for _ in range(100):
    try:urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',timeout=1);break
    except Exception:time.sleep(.1)
   else:raise RuntimeError('local startup failed')
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.environ['MCIS_BROWSER_BIN'],headless=True,args=['--no-sandbox'],env={**os.environ,'HOME':tmp,'XDG_CONFIG_HOME':tmp+'/config'})
   page=browser.new_page();errors=[];held=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto('http://127.0.0.1:15953/#/interview?case=SYN-W52A')
   warning=page.get_by_text('当前身份无权访问笔录原文。受保护内容已清空',exact=False);warning.wait_for()
   assert 'SYNTHETIC-ANSWER' not in page.locator('body').inner_text()
   page.locator('select[title="X-MCIS-Role"]').select_option('LeadInvestigator')
   page.get_by_text('SYNTHETIC-ANSWER-IR-01',exact=True).wait_for()
   page.reload();page.get_by_text('SYNTHETIC-ANSWER-IR-01',exact=True).wait_for()
   def delay(route):held.append((route,route.fetch()))
   page.route('**/interview-compare/IR-02',delay)
   page.locator('[data-record="IR-02"]').click()
   for _ in range(100):
    if held:break
    page.wait_for_timeout(20)
   assert held
   page.locator('[data-record="IR-01"]').click();page.get_by_text('SYNTHETIC-ANSWER-IR-01',exact=True).wait_for()
   route,response=held.pop();route.fulfill(response=response);page.wait_for_timeout(100)
   assert page.locator('.ic-person.sel').get_attribute('data-record')=='IR-01'
   assert 'SYNTHETIC-ANSWER-IR-02' not in page.locator('body').inner_text()
   page.locator('[data-record="IR-02"]').click()
   for _ in range(100):
    if held:break
    page.wait_for_timeout(20)
   assert held
   page.locator('select[title="X-MCIS-Role"]').select_option('Investigator');warning.wait_for()
   route,response=held.pop();route.fulfill(response=response);page.wait_for_timeout(100)
   assert 'SYNTHETIC-ANSWER' not in page.locator('body').inner_text()
   page.unroute('**/interview-compare/IR-02',delay)
   page.locator('select[title="X-MCIS-Role"]').select_option('LeadInvestigator')
   page.get_by_text('SYNTHETIC-ANSWER-IR-01',exact=True).wait_for()
   # Revoke actual policy while current text is visible, then reload permissions.
   url='http://127.0.0.1:15952/api/v1/cases/SYN-W52A/access-policy';headers={'X-MCIS-Role':'LeadInvestigator'}
   policy=page.request.get(url,headers=headers).json();policy['matrix']['LeadInvestigator']['testimony']='Deny'
   assert page.request.put(url,headers=headers,data=policy).status==200
   page.locator('[data-record="IR-02"]').click();warning.wait_for()
   assert 'SYNTHETIC-ANSWER' not in page.locator('body').inner_text()
   assert not errors,errors;browser.close()
  print('PASS real synthetic service browser: default denial; Lead reads/reopens; late record/identity detail discarded; actual policy revocation clears original text. No API doubles.')
 finally:
  for proc in (front,back):os.killpg(proc.pid,signal.SIGTERM);proc.wait()
