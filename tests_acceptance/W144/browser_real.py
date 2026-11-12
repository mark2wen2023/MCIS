"""Real API/core/browser acceptance; only explicit binding/race probes modify response delivery."""
import os,signal,subprocess,tempfile,time,urllib.request,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent
with tempfile.TemporaryDirectory(prefix='w144-accept-') as tmp:
 env={**os.environ,'MCIS_DATA_DIR':tmp+'/data','MCIS_API':'http://127.0.0.1:15944','PYTHONPATH':str(ROOT/'service'),'MCIS_DOTNET':os.environ.get('MCIS_DOTNET',str(Path.home()/'.dotnet/dotnet')),'DOTNET_CLI_HOME':tmp+'/dotnet'}
 back=subprocess.Popen([str(ROOT/'service/.venv/bin/python'),str(HERE/'server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 front=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15945','--strictPort'],cwd=ROOT/'web',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 try:
  for port,path in [(15944,'/api/v1/health'),(15945,'/')]:
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
   page.route('**/nomoto:preview',intercept)
   page.goto('http://127.0.0.1:15945/#/whatif?case=CASE-A')
   def fill():
    values={'初始航向（度，0≤值<360）':'0','固定速度（节，0–40）':'10','K（1/秒，0.000001–0.5）':'0.1','T（秒，1–1000）':'20','参考速度（节，0.1–40）':'10','最大舵角（度，0.1–45）':'35','舵速（度/秒，0.01–20）':'2','固定舵令（有符号度数）':'10','时长（整秒，1–300）':'10','参数来源说明（必填）':'合成显式参数 🛳','不确定性说明（必填）':'未经过实船校准'}
    for label,value in values.items():page.get_by_label(label,exact=True).fill(value)
    page.get_by_role('checkbox',name='EV-001').check()
   page.get_by_label('初始航向（度，0≤值<360）',exact=True).wait_for()
   assert page.get_by_label('初始航向（度，0≤值<360）',exact=True).input_value()==''
   assert page.get_by_label('参数来源说明（必填）',exact=True).input_value()==''
   fill();page.get_by_role('button',name='运行单船假设预览（不保存）',exact=True).click()
   page.get_by_role('heading',name='单船假设响应 · 未保存',exact=True).wait_for()
   assert '两条均不是实测原始轨迹' in page.locator('.w144-result').inner_text()
   assert '不是置信区间' in page.locator('.w144-result').inner_text()
   assert page.locator('.w144-result tbody tr').count()==22
   assert page.get_by_role('img',name='两条假设轨迹，等比例东向与北向米坐标，非地图').count()==1
   # Plot uses a square physical plotting region, not stretched unequal metre axes.
   assert page.locator('.w144-result svg rect').get_attribute('width')==page.locator('.w144-result svg rect').get_attribute('height')
   assert page.locator('.case-chip b').inner_text()=='CASE-A'
   # Wrong input binding must be rejected, even if totals/coverage are plausible.
   page.get_by_label('固定舵令（有符号度数）',exact=True).fill('11')
   assert page.locator('.w144-result').count()==0
   mode['next']='wrong-hash'
   page.get_by_role('button',name='运行单船假设预览（不保存）',exact=True).click()
   page.get_by_role('alert').wait_for(timeout=5000)
   assert page.locator('.w144-result').count()==0
   # Late genuine result after edit must not restore prior data.
   mode['next']='hold';page.get_by_role('button',name='运行单船假设预览（不保存）',exact=True).click()
   for _ in range(200):
    if held:break
    page.wait_for_timeout(20)
   assert held
   page.get_by_label('固定舵令（有符号度数）',exact=True).fill('12')
   route,reply=held.pop();route.fulfill(response=reply);page.wait_for_timeout(100)
   assert page.locator('.w144-result').count()==0
   # Repeat with identity and case changes while result is pending.
   for change in ['case','identity']:
    if change=='identity':fill()
    mode['next']='hold'
    page.get_by_role('button',name='运行单船假设预览（不保存）',exact=True).click()
    for _ in range(200):
     if held:break
     page.wait_for_timeout(20)
    assert held
    if change=='case':
     page.evaluate("location.hash='/whatif?case=CASE-B'")
     page.get_by_label('初始航向（度，0≤值<360）',exact=True).wait_for()
     assert page.get_by_label('初始航向（度，0≤值<360）',exact=True).input_value()==''
     assert page.locator('.case-chip b').inner_text()=='CASE-B'
    else:page.evaluate("async()=>{const api=await import('/src/api.ts');api.setIdentity('Public','Independent');}")
    route,reply=held.pop();route.fulfill(response=reply);page.wait_for_timeout(100)
    assert page.locator('.w144-result').count()==0
   page.get_by_role('alert').wait_for()
   assert not errors,errors
   browser.close()
  print('PASS real CLI/API/browser: blank explicit inputs/notes, hypothetical equal-metre plot/state table, no accuracy/safety verdict, wrong hash rejected, edits/case/identity invalidate delayed output.')
 finally:
  for proc in (front,back):os.killpg(proc.pid,signal.SIGTERM);proc.wait()
