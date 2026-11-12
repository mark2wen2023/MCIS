"""Real synthetic service browser; only delivery delay is intercepted."""
import os,signal,subprocess,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent
with tempfile.TemporaryDirectory(prefix='archive-a-browser-') as tmp:
 env={**os.environ,'MCIS_DATA_DIR':tmp+'/data','MCIS_API':'http://127.0.0.1:15972','PYTHONPATH':str(ROOT/'service')}
 back=subprocess.Popen([str(ROOT/'service/.venv/bin/python'),str(HERE/'server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 front=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15973','--strictPort'],cwd=ROOT/'web',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 try:
  for port,path in [(15972,'/api/v1/health'),(15973,'/')]:
   for _ in range(100):
    try:urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',timeout=1);break
    except Exception:time.sleep(.1)
   else:raise RuntimeError('local startup failed')
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.environ['MCIS_BROWSER_BIN'],headless=True,args=['--no-sandbox'],env={**os.environ,'HOME':tmp,'XDG_CONFIG_HOME':tmp+'/config'})
   page=browser.new_page();errors=[];held=[];page.on('pageerror',lambda e:errors.append(str(e)))
   api='http://127.0.0.1:15972/api/v1/cases/SYN-ARCHIVE-A';headers={'X-MCIS-Role':'LeadInvestigator'}
   r=page.request.post(api+'/reports',headers=headers,data={'templateId':'imo-cic','lang':'zh'})
   assert r.status==201,r.text();rid=r.json()['reportId']
   page.add_init_script("localStorage.setItem('mcis.role','LeadInvestigator')")
   page.goto('http://127.0.0.1:15973/#/report?case=SYN-ARCHIVE-A&report='+rid)
   page.get_by_text('当前案件包不能完整恢复已存报告与操作快照',exact=False).wait_for()
   page.goto('http://127.0.0.1:15973/#/lobby')
   button=page.get_by_role('button',name='导出案件包：Synthetic archive',exact=True)
   button.wait_for();downloads=[];page.on('download',lambda d:downloads.append(d))
   with page.expect_response(lambda r:r.url.endswith('/SYN-ARCHIVE-A/export')) as response:button.click()
   assert response.value.status==409
   page.get_by_text('本案件包含当前案件包尚不支持完整恢复的',exact=False).wait_for()
   assert not downloads
   page.locator('select[title="X-MCIS-Role"]').select_option('Investigator')
   with page.expect_response(lambda r:r.url.endswith('/SYN-ARCHIVE-A/export')) as response:button.click()
   assert response.value.status==403
   page.get_by_text('当前身份无权限。未自动重试，请核实身份。',exact=True).wait_for()
   assert page.get_by_text('本案件包含当前案件包尚不支持完整恢复的',exact=False).count()==0
   assert not downloads
   page.locator('select[title="X-MCIS-Role"]').select_option('LeadInvestigator')
   page.goto('http://127.0.0.1:15973/#/interview?case=SYN-ARCHIVE-A')
   page.get_by_role('region',name='人工笔录录入').wait_for()
   assert '完整' in page.locator('body').inner_text() and '.mcase' in page.locator('body').inner_text()
   assert not errors,errors
   browser.close();print('PASS real service report creation/page, lobby export409/no-download, identity403/no stale denial detail, transcript warning.')
 finally:
  for proc in [front,back]:
   try:os.killpg(proc.pid,signal.SIGTERM)
   except ProcessLookupError:pass
