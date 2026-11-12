"""Real API/core/browser acceptance; only explicit binding/race probes modify response delivery."""
import os,signal,subprocess,tempfile,time,urllib.request,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent
with tempfile.TemporaryDirectory(prefix='w183-accept-') as tmp:
 env={**os.environ,'MCIS_DATA_DIR':tmp+'/data','MCIS_API':'http://127.0.0.1:15987','PYTHONPATH':str(ROOT/'service'),'MCIS_DOTNET':os.environ.get('MCIS_DOTNET',str(Path.home()/'.dotnet/dotnet')),'DOTNET_CLI_HOME':tmp+'/dotnet'}
 back=subprocess.Popen([str(ROOT/'service/.venv/bin/python'),str(HERE/'server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 front=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15988','--strictPort'],cwd=ROOT/'web',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 try:
  for port,path in [(15987,'/api/v1/health'),(15988,'/')]:
   for _ in range(100):
    try:urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',timeout=1);break
    except Exception:time.sleep(.1)
   else:raise RuntimeError('local startup failed')
  with sync_playwright() as p:
   browser=p.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox'],env={**os.environ,'HOME':tmp,'XDG_CONFIG_HOME':tmp+'/config'})
   page=browser.new_page();errors=[];posted=[];held=[];mode=['normal']
   page.on('pageerror',lambda e:errors.append(str(e)))
   def intercept(route):
    posted.append(route.request.post_data_json);response=route.fetch()
    assert response.status==200
    if mode[0]=='503':mode[0]='normal';route.fulfill(status=503,json={'code':'HFACS_SAVE_FAILED','message':'synthetic response loss after commit'})
    elif mode[0]=='hold':mode[0]='normal';held.append((route,response))
    else:route.fulfill(response=response)
   page.route('**/hfacs:save',intercept)
   page.goto('http://127.0.0.1:15988/#/hf?case=CASE-A')
   page.get_by_role('button',name='人工分类草稿（可保存）',exact=True).click()
   scope=page.get_by_label('调查范围 / 工作任务情境',exact=True);scope.wait_for();assert scope.input_value()==''
   assert page.get_by_text('当前分类草稿尚未纳入案件包导入/导出；保存仅在当前服务数据库。',exact=True).is_visible()
   scope.fill('合成操作情境 🛳');page.get_by_role('button',name='添加人工条目',exact=True).click()
   page.get_by_label('条目 ID 1',exact=True).fill('F1');page.get_by_label('项目分类 1',exact=True).select_option('UA')
   assert '分组/根类别草稿' in page.get_by_label('项目分类 1',exact=True).inner_text()
   description=page.get_by_label('情境描述 1',exact=True);description.fill('人工待核验假设')
   page.get_by_label('人工分类理由 1',exact=True).fill('合成方法测试，不是责任结论')
   save=page.get_by_role('button',name='保存人工分类草稿',exact=True)
   mode[0]='503';save.click();retry=page.get_by_role('button',name='重试同一保存请求',exact=False)
   retry.wait_for();page.get_by_text('服务暂不可用或保存状态未确认',exact=False).wait_for()
   assert description.is_disabled();assert page.get_by_text('已核验此请求的保存回执',exact=False).count()==0
   retry.click();page.get_by_text('已核验此请求的保存回执',exact=False).wait_for();assert posted[0]==posted[1]
   def server(action):return page.request.get('http://127.0.0.1:15987/api/v1/cases/CASE-A/human-factors/hfacs:'+action).json()
   assert server('draft')['document']['revision']==1 and len(server('audit')['events'])==1
   page.get_by_role('button',name='重新打开服务端草稿',exact=False).click();description.wait_for();assert description.input_value()=='人工待核验假设'
   # Genuine committed response delivered after case switch must not overwrite new case state.
   description.fill('second hypothetical');mode[0]='hold';save.click()
   for _ in range(200):
    if held:break
    page.wait_for_timeout(20)
   assert held
   page.evaluate("location.hash='/hf?case=CASE-B'")
   page.get_by_role('button',name='人工分类草稿（可保存）',exact=True).click();scope.wait_for();assert scope.input_value()==''
   route,response=held.pop();route.fulfill(response=response);page.wait_for_timeout(100)
   assert scope.input_value()=='' and page.get_by_text('已核验此请求的保存回执',exact=False).count()==0
   # Switch back, then revoke actual current role before submitting. No interception here.
   page.evaluate("location.hash='/hf?case=CASE-A'")
   page.get_by_role('button',name='人工分类草稿（可保存）',exact=True).click();description.wait_for()
   description.fill('third hypothetical');mode[0]='hold';save.click()
   for _ in range(200):
    if held:break
    page.wait_for_timeout(20)
   assert held
   page.locator('select[title="X-MCIS-Role"]').select_option('Public')
   route,response=held.pop();route.fulfill(response=response);page.wait_for_timeout(150)
   assert description.count()==0
   page.locator('select[title="X-MCIS-Role"]').select_option('Investigator')
   page.get_by_role('button',name='人工分类草稿（可保存）',exact=True).click();description.wait_for()
   page.unroute('**/hfacs:save',intercept)
   # Modify only the synthetic fixture's policy from a separate process.
   code="from pathlib import Path;from mcis_service.main import create_app;from mcis_service.config import Settings;from mcis_service.db import put_doc;from mcis_service.redaction.models import AccessPolicyRow;from mcis_service.redaction.policy import default_policy;import os;app=create_app(Settings(data_dir=Path(os.environ['MCIS_DATA_DIR']),seed_demo=False));p=default_policy();p['matrix']['Investigator']['agent_drafts']='Deny';s=app.state.db.SessionLocal();put_doc(s,AccessPolicyRow,'CASE-A','policy',p);s.commit();s.close()"
   subprocess.run([str(ROOT/'service/.venv/bin/python'),'-c',code],env=env,check=True,capture_output=True)
   description.fill('must not save after revoke');save.click()
   page.get_by_text('当前权限已不允许保存，旧草稿及来源已隐藏',exact=False).wait_for()
   assert description.count()==0 and scope.count()==0
   assert not errors,errors
   browser.close()
  print('PASS real browser/API/CLI: committed503 same-request retry single revision/audit; reopen; late case/identity responses suppressed; actual revoked policy403 clears editor.')
 finally:
  for proc in (front,back):os.killpg(proc.pid,signal.SIGTERM);proc.wait()
