"""Real API/core/browser acceptance; only explicit binding/race probes modify response delivery."""
import os,signal,subprocess,tempfile,time,urllib.request,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent
with tempfile.TemporaryDirectory(prefix='w183-accept-') as tmp:
 env={**os.environ,'MCIS_DATA_DIR':tmp+'/data','MCIS_API':'http://127.0.0.1:15983','PYTHONPATH':str(ROOT/'service'),'MCIS_DOTNET':os.environ.get('MCIS_DOTNET',str(Path.home()/'.dotnet/dotnet')),'DOTNET_CLI_HOME':tmp+'/dotnet'}
 back=subprocess.Popen([str(ROOT/'service/.venv/bin/python'),str(HERE/'server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 front=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15984','--strictPort'],cwd=ROOT/'web',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 try:
  for port,path in [(15983,'/api/v1/health'),(15984,'/')]:
   for _ in range(100):
    try:urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',timeout=1);break
    except Exception:time.sleep(.1)
   else:raise RuntimeError('local startup failed')
  with sync_playwright() as p:
   browser=p.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox'],env={**os.environ,'HOME':tmp,'XDG_CONFIG_HOME':tmp+'/config'})
   page=browser.new_page();errors=[];held=[];mode={'next':'real'}
   page.on('pageerror',lambda e:errors.append(str(e)))
   def intercept(route):
    reply=route.fetch()
    if mode['next']=='wrong-hash':
     mode['next']='real';d=reply.json();d['inputSha256']='f'*64;route.fulfill(response=reply,json=d)
    elif mode['next']=='hold':mode['next']='real';held.append((route,reply))
    else:route.fulfill(response=reply)
   page.route('**/rest:preview',intercept)
   page.goto('http://127.0.0.1:15984/#/hf?case=CASE-A')
   def fill():
    page.get_by_label('记录起点 UTC',exact=True).fill('2026-01-01T00:00:00Z')
    page.get_by_label('记录终点 UTC',exact=True).fill('2026-01-01T12:00:00Z')
    page.get_by_label('开始 UTC 1',exact=True).fill('2026-01-01T00:00:00Z')
    page.get_by_label('结束 UTC 1',exact=True).fill('2026-01-01T04:00:00Z')
    page.get_by_label('类型 1',exact=True).select_option('Rest')
    page.get_by_role('checkbox',name='EV-001').check()
    page.get_by_role('checkbox',name='我理解这是人工录入').check()
   fill();page.get_by_role('button',name='运行技术预览（不保存）',exact=True).click()
   page.get_by_role('heading',name='工休技术预览 · 未保存',exact=True).wait_for()
   assert page.locator('.w183-totals').inner_text().count('8')==1
   assert '记录长度不足' in page.locator('.w183-result').inner_text()
   assert '不代表合规' in page.locator('.w183-result').inner_text()
   assert page.locator('.case-chip b').inner_text()=='CASE-A'
   # Wrong input binding must be rejected, even if totals/coverage are plausible.
   page.get_by_label('结束 UTC 1',exact=True).fill('2026-01-01T05:00:00Z')
   assert page.locator('.w183-result').count()==0
   page.get_by_role('checkbox',name='我理解这是人工录入').check();mode['next']='wrong-hash'
   page.get_by_role('button',name='运行技术预览（不保存）',exact=True).click()
   page.get_by_role('alert').wait_for(timeout=5000)
   assert page.locator('.w183-result').count()==0
   # Late genuine result after edit must not restore prior data.
   mode['next']='hold';page.get_by_role('button',name='运行技术预览（不保存）',exact=True).click()
   for _ in range(200):
    if held:break
    page.wait_for_timeout(20)
   assert held
   page.get_by_label('结束 UTC 1',exact=True).fill('2026-01-01T06:00:00Z')
   route,reply=held.pop();route.fulfill(response=reply);page.wait_for_timeout(100)
   assert page.locator('.w183-result').count()==0
   # Repeat with identity and case changes while result is pending.
   for change in ['case','identity']:
    if change=='identity':fill()
    page.get_by_role('checkbox',name='我理解这是人工录入').check();mode['next']='hold'
    page.get_by_role('button',name='运行技术预览（不保存）',exact=True).click()
    for _ in range(200):
     if held:break
     page.wait_for_timeout(20)
    assert held
    if change=='case':
     page.evaluate("location.hash='/hf?case=CASE-B'")
     page.get_by_label('记录起点 UTC',exact=True).wait_for()
     assert page.get_by_label('记录起点 UTC',exact=True).input_value()==''
     assert page.locator('.case-chip b').inner_text()=='CASE-B'
    else:page.evaluate("async()=>{const api=await import('/src/api.ts');api.setIdentity('Public','Independent');}")
    route,reply=held.pop();route.fulfill(response=reply);page.wait_for_timeout(100)
    assert page.locator('.w183-result').count()==0
   page.get_by_role('alert').wait_for()
   assert not errors,errors
   browser.close()
  print('PASS real CLI/API/browser: short coverage and Unknown warnings, noncompliance disclaimer, wrong binding rejected, edits/case/identity invalidate delayed results.')
 finally:
  for proc in (front,back):os.killpg(proc.pid,signal.SIGTERM);proc.wait()
