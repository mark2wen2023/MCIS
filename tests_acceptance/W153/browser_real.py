"""Real API/core/browser acceptance; only explicit binding/race probes modify response delivery."""
import os,signal,subprocess,tempfile,time,urllib.request,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent
with tempfile.TemporaryDirectory(prefix='w153-accept-') as tmp:
 env={**os.environ,'MCIS_DATA_DIR':tmp+'/data','MCIS_API':'http://127.0.0.1:15953','PYTHONPATH':str(ROOT/'service'),'MCIS_DOTNET':os.environ.get('MCIS_DOTNET',str(Path.home()/'.dotnet/dotnet')),'DOTNET_CLI_HOME':tmp+'/dotnet'}
 back=subprocess.Popen([str(ROOT/'service/.venv/bin/python'),str(HERE/'server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 front=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15954','--strictPort'],cwd=ROOT/'web',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 try:
  for port,path in [(15953,'/api/v1/health'),(15954,'/')]:
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
   page.route('**/bowtie:preview',intercept)
   page.goto('http://127.0.0.1:15954/#/systemic?case=CASE-A')
   def fill():
    page.get_by_label('危险源（背景条件，不等于事故结果）',exact=True).fill('合成危险源 🛳')
    page.get_by_label('顶事件 ID',exact=True).fill('TOP')
    page.get_by_label('顶事件描述',exact=True).fill('假设失控')
   assert page.get_by_label('顶事件 ID',exact=True).input_value()==''
   assert not page.locator('input[type=checkbox]:checked').count()
   fill()
   for i,(ident,kind) in enumerate([('T','Threat'),('C','Consequence')],1):
    page.get_by_role('button',name='添加节点',exact=True).click()
    page.get_by_label('节点 ID '+str(i),exact=True).fill(ident)
    page.get_by_label('节点名称 '+str(i),exact=True).fill('假设 '+ident)
    page.get_by_label('节点类型 '+str(i),exact=True).select_option(kind)
   for i,(a,b) in enumerate([('T','TOP'),('TOP','C')],1):
    page.get_by_role('button',name='添加连线',exact=True).click()
    page.get_by_label('起点 ID '+str(i),exact=True).fill(a)
    page.get_by_label('终点 ID '+str(i),exact=True).fill(b)
   page.get_by_role('checkbox',name='EV-001').check()
   page.get_by_role('button',name='运行结构核查（不保存）',exact=True).click()
   page.get_by_role('heading',name='核心结构核查结果 · 非事实确认',exact=True).wait_for()
   assert '不代表安全或因果成立' in page.locator('.w153-result').inner_text()
   assert page.locator('.case-chip b').inner_text()=='CASE-A'
   page.get_by_label('终点 ID 2',exact=True).fill('GHOST')
   page.get_by_role('button',name='运行结构核查（不保存）',exact=True).click()
   page.get_by_text('sys_unknown_node',exact=False).wait_for()
   assert '存在结构问题' in page.locator('.w153-result').inner_text()
   page.get_by_label('终点 ID 2',exact=True).fill('C')
   # Wrong input binding must be rejected, even if totals/coverage are plausible.
   page.get_by_label('顶事件描述',exact=True).fill('编辑后的假设')
   assert page.locator('.w153-result').count()==0
   mode['next']='wrong-hash'
   page.get_by_role('button',name='运行结构核查（不保存）',exact=True).click()
   page.get_by_role('alert').wait_for(timeout=5000)
   assert page.locator('.w153-result').count()==0
   # Late genuine result after edit must not restore prior data.
   mode['next']='hold';page.get_by_role('button',name='运行结构核查（不保存）',exact=True).click()
   for _ in range(200):
    if held:break
    page.wait_for_timeout(20)
   assert held
   page.get_by_label('顶事件描述',exact=True).fill('第二次编辑假设')
   route,reply=held.pop();route.fulfill(response=reply);page.wait_for_timeout(100)
   assert page.locator('.w153-result').count()==0
   # Repeat with identity and case changes while result is pending.
   for change in ['case','identity']:
    if change=='identity':fill()
    mode['next']='hold'
    page.get_by_role('button',name='运行结构核查（不保存）',exact=True).click()
    for _ in range(200):
     if held:break
     page.wait_for_timeout(20)
    assert held
    if change=='case':
     page.evaluate("location.hash='/systemic?case=CASE-B'")
     page.get_by_label('顶事件 ID',exact=True).wait_for()
     assert page.get_by_label('顶事件 ID',exact=True).input_value()==''
     assert page.locator('.case-chip b').inner_text()=='CASE-B'
    else:page.evaluate("async()=>{const api=await import('/src/api.ts');api.setIdentity('Public','Independent');}")
    route,reply=held.pop();route.fulfill(response=reply);page.wait_for_timeout(100)
    assert page.locator('.w153-result').count()==0
   page.get_by_role('alert').wait_for()
   assert not errors,errors
   browser.close()
  print('PASS real CLI/API/browser: blank hypothesis, no-barrier valid structure disclaimer, unknown endpoint diagnostic, wrong hash rejection, edits/case/identity discard delayed results.')
 finally:
  for proc in (front,back):os.killpg(proc.pid,signal.SIGTERM);proc.wait()
