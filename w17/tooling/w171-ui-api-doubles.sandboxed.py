"""Chromium lifecycle tests using explicit API doubles, not backend acceptance."""
import json,subprocess,time,urllib.request,os,signal
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path('/workspace/mcis-w4-3ae5166');server=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15717','--strictPort'],cwd=ROOT/'web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
def data(case):return dict(caseId=case,policy={'matrix':{'Investigator':{'audit':'ReadOnly'}},'fieldRules':[]},policySource='default',policyAudit={'events':[],'limit':50,'hasMore':False},identityMode='local-role-header',readOnly=True)
try:
 for _ in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:15717',timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,chromium_sandbox=True);page=browser.new_page(viewport={'width':1440,'height':1000});requests=[];pending=[]
  def route(r):
   requests.append((r.request.method,r.request.url))
   if '/access-workbench' in r.request.url:
    case=r.request.url.split('/cases/')[1].split('/')[0]
    if r.request.headers.get('x-mcis-role')=='Public':r.fulfill(status=403,json={});return
    if case=='DELAY':pending.append(r);return
    if case=='FAIL':r.fulfill(status=500,json={});return
    r.fulfill(json=data(case));return
   r.fulfill(json=[])
  page.route('**/api/v1/**',route)
  page.goto('http://127.0.0.1:15717/#/access?case=CASE-A');page.get_by_role('heading',name='案件：CASE-A',exact=True).wait_for()
  assert page.get_by_text('本地自报角色，不是真实身份认证。',exact=True).is_visible()
  assert page.get_by_text('暂无策略变更审计记录。',exact=True).is_visible()
  assert page.get_by_role('button',name='刷新权限工作台',exact=True).is_visible()
  assert page.get_by_role('button',name='保存',exact=True).count()==0
  page.evaluate("location.hash='/access?case=DELAY'");page.get_by_text('正在读取权限配置与审计…',exact=True).wait_for();assert page.get_by_role('heading',name='案件：CASE-A',exact=True).count()==0
  page.evaluate("location.hash='/access?case=CASE-B'");page.get_by_role('heading',name='案件：CASE-B',exact=True).wait_for()
  for r in pending:
   try:r.fulfill(json=data('DELAY'))
   except Exception:pass
  page.wait_for_timeout(100);assert page.get_by_role('heading',name='案件：DELAY',exact=True).count()==0
  page.locator('select[title="X-MCIS-Role"]').select_option('Public');page.get_by_role('alert').wait_for();assert page.get_by_role('heading',name='案件：CASE-B',exact=True).count()==0
  assert '当前身份不是调查组' in page.get_by_role('alert').inner_text()
  page.locator('select[title="X-MCIS-Role"]').select_option('Investigator');page.get_by_role('heading',name='案件：CASE-B',exact=True).wait_for()
  page.evaluate("location.hash='/access?case=FAIL'");page.get_by_role('alert').wait_for();assert page.get_by_role('heading',name='案件：CASE-B',exact=True).count()==0
  assert all(method=='GET' for method,url in requests);assert not any('access-policy' in url for method,url in requests)
  page.evaluate("location.hash='/access?case=CASE-A'");page.get_by_role('heading',name='案件：CASE-A',exact=True).wait_for()
  out=Path('/workspace/mcis-w17-report/screenshots/simulated-dom');out.mkdir(parents=True,exist_ok=True);page.screenshot(path=str(out/'access-default.png'),full_page=True)
  browser.close()
 print('W17.1 Chromium passed: matrix empty/default, explicit local identity, no writes/fallback, case switch delayed suppression, role403 clear, server error clear; API doubles only')
finally:os.killpg(server.pid,signal.SIGTERM);server.wait()
