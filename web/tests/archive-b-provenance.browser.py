"""API-double provenance lifecycle coverage, not actual backend provenance validation."""
import subprocess,time,urllib.request,os,signal
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
s=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15856','--strictPort'],cwd=ROOT/'web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
try:
 for _ in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:15856',timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox']);p=b.new_page();p.set_default_timeout(8000);held=[];mode={'hold':False,'error':False}
  provenance={'origin':'restored-history','sourceArchiveSha256':'a'*64,'importedUtc':'2026-11-12T00:00:00Z','originalDocumentSha256':'b'*64,'currentDocumentSha256':'c'*64,'changedSinceImport':True}
  def route(r):
   u=r.request.url;case='SYNTHETIC-B' if 'SYNTHETIC-B' in u else 'SYNTHETIC-A';rid=u.rsplit('/',1)[1]
   data={'caseId':case,'kind':'interview','recordId':rid,'provenance':None if rid=='IR-02' else provenance}
   if mode['hold'] and case=='SYNTHETIC-A' and rid=='IR-01':held.append((r,data))
   elif mode['error'] or r.request.headers.get('x-mcis-role')=='Investigator':r.fulfill(status=409 if mode['error'] in [409,'unsupported'] else 403,json={'code':'ARCHIVE_HISTORY_UNSUPPORTED' if mode['error']=='unsupported' else 'ARCHIVE_HISTORY_INTEGRITY' if mode['error']==409 else 'FORBIDDEN'})
   else:r.fulfill(json=data)
  p.add_init_script("localStorage.setItem('mcis.role','LeadInvestigator')");p.route('**/api/v1/**',route);p.goto('http://127.0.0.1:15856/tests/archive-b-provenance-harness.html')
  p.get_by_text('此对象包含恢复历史',exact=True).wait_for();assert '不把当前所有状态都称为历史状态' in p.locator('body').inner_text()
  mode['error']=409;p.reload();p.get_by_text('此对象恢复来源未能核验',exact=False).wait_for();assert 'PROTECTED-PARENT-TEXT' in p.locator('body').inner_text()
  mode['error']='unsupported';p.reload();p.get_by_text('旧来源包版本暂不支持恢复来源核验',exact=False).wait_for();assert 'PROTECTED-PARENT-TEXT' in p.locator('body').inner_text();assert '未因此丢失或删除' in p.locator('body').inner_text()
  mode['error']=False;mode['hold']=True;p.reload()
  for _ in range(50):
   p.wait_for_timeout(20)
   if held:break
  assert held;mode['hold']=False;p.get_by_role('button',name='Advance content revision',exact=True).click();p.get_by_text('此对象包含恢复历史',exact=True).wait_for()
  r,data=held.pop();data['provenance']={**provenance,'sourceArchiveSha256':'e'*64};r.fulfill(json=data);p.wait_for_timeout(100);assert 'e'*64 not in p.locator('body').inner_text()
  mode['hold']=True;p.reload()
  for _ in range(50):
   p.wait_for_timeout(20)
   if held:break
  assert held;p.get_by_role('button',name='Switch record',exact=True).click();p.get_by_text('服务未返回此对象的本次恢复关联',exact=False).wait_for()
  r,data=held.pop();r.fulfill(json=data);p.wait_for_timeout(100);assert p.get_by_text('此对象包含恢复历史',exact=True).count()==0
  p.reload()
  for _ in range(50):
   p.wait_for_timeout(20)
   if held:break
  assert held;p.get_by_role('button',name='Switch case',exact=True).click();p.get_by_text('此对象包含恢复历史',exact=True).wait_for()
  r,data=held.pop();data['provenance']={**provenance,'sourceArchiveSha256':'d'*64};r.fulfill(json=data);p.wait_for_timeout(100);assert 'd'*64 not in p.locator('body').inner_text()
  p.get_by_role('button',name='Switch identity',exact=True).click();p.get_by_text('Parent protected content cleared',exact=True).wait_for();assert 'PROTECTED-PARENT-TEXT' not in p.locator('body').inner_text() and 'a'*64 not in p.locator('body').inner_text() and p.get_by_text('服务未返回此对象的本次恢复关联',exact=False).count()==0
  p.unroute_all(behavior='ignoreErrors');b.close()
 print('Archive B provenance browser:changed-history label,explicit null,late record/case suppression,revision refresh+late suppression,integrity409distinct,identity403parentclear/no inferred history passed(API doubles)')
finally:os.killpg(s.pid,signal.SIGTERM);s.wait()
