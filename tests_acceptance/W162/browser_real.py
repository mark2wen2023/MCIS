"""Real synthetic service browser; only delivery delay is intercepted."""
import os,signal,subprocess,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent
with tempfile.TemporaryDirectory(prefix='w162-browser-') as tmp:
 env={**os.environ,'MCIS_DATA_DIR':tmp+'/data','MCIS_API':'http://127.0.0.1:15962','PYTHONPATH':str(ROOT/'service')}
 back=subprocess.Popen([str(ROOT/'service/.venv/bin/python'),str(HERE/'server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 front=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15963','--strictPort'],cwd=ROOT/'web',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 try:
  for port,path in [(15962,'/api/v1/health'),(15963,'/')]:
   for _ in range(100):
    try:urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',timeout=1);break
    except Exception:time.sleep(.1)
   else:raise RuntimeError('local startup failed')
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.environ['MCIS_BROWSER_BIN'],headless=True,args=['--no-sandbox'],env={**os.environ,'HOME':tmp,'XDG_CONFIG_HOME':tmp+'/config'})
   page=browser.new_page();errors=[];held=[];downloads=[]
   page.on('pageerror',lambda e:errors.append(str(e)));page.on('download',lambda d:downloads.append(d))
   page.goto('http://127.0.0.1:15963/#/report?case=SYN-162')
   page.get_by_text('当前身份无权访问完整报告内容',exact=False).wait_for()
   page.locator('select[title="X-MCIS-Role"]').select_option('LeadInvestigator')
   generate=page.get_by_role('button',name='📄 生成双语报告',exact=True);generate.wait_for();generate.click()
   page.get_by_role('button',name='DOCX',exact=True).wait_for()
   for _ in range(100):
    if not page.get_by_role('button',name='DOCX',exact=True).is_disabled():break
    page.wait_for_timeout(50)
   assert page.locator('.rpt-audit').count()>0
   for name in ['DOCX','PDF 中文']:
    with page.expect_download() as d:page.get_by_role('button',name=name,exact=True).click()
    output=tmp+'/'+('out.docx' if name=='DOCX' else 'out.pdf');d.value.save_as(output)
    assert Path(output).stat().st_size>100
   downloads.clear()
   def delay(route):held.append((route,route.fetch()))
   page.route('**/reports/*/export?*',delay)
   page.get_by_role('button',name='DOCX',exact=True).click()
   for _ in range(100):
    if held:break
    page.wait_for_timeout(20)
   assert held
   page.locator('select[title="X-MCIS-Role"]').select_option('Investigator')
   page.get_by_text('当前身份无权访问完整报告内容',exact=False).wait_for()
   route,response=held.pop();route.fulfill(response=response);page.wait_for_timeout(200)
   assert not downloads and page.locator('.rpt-audit').count()==0
   page.unroute('**/reports/*/export?*',delay)
   page.locator('select[title="X-MCIS-Role"]').select_option('LeadInvestigator')
   for _ in range(100):
    if page.locator('.rpt-audit').count():break
    page.wait_for_timeout(50)
   assert page.locator('.rpt-audit').count()>0
   # Actual policy update through authorized service; next report read must clear old view.
   response=page.request.get('http://127.0.0.1:15962/api/v1/cases/SYN-162/access-policy',headers={'X-MCIS-Role':'LeadInvestigator'})
   policy=response.json();policy['matrix']['LeadInvestigator']['evidence_meta']='Deny'
   assert page.request.put('http://127.0.0.1:15962/api/v1/cases/SYN-162/access-policy',headers={'X-MCIS-Role':'LeadInvestigator'},data=policy).status==200
   page.evaluate("(()=>{const [route,query]=location.hash.split('?');const p=new URLSearchParams(query);p.set('lang',p.get('lang')==='en'?'zh':'en');location.hash=route+'?'+p.toString()})()")
   page.get_by_text('当前身份无权访问完整报告内容',exact=False).wait_for()
   assert page.locator('.rpt-audit').count()==0 and page.get_by_role('button',name='DOCX',exact=True).is_disabled()
   assert not errors,errors;browser.close()
  print('PASS actual service browser: default Investigator denied; Lead creates/reads audit/downloads actual DOCX/PDF; late download suppressed on identity change; real policy revocation clears view.')
 finally:
  for proc in (front,back):os.killpg(proc.pid,signal.SIGTERM);proc.wait()
