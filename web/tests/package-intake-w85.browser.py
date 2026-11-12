"""Frontend lifecycle tests with explicit API doubles; NOT backend acceptance."""
import hashlib,json,subprocess,time,urllib.request,os,signal
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
server=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15885','--strictPort'],cwd=ROOT/'web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
try:
 for _ in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:15885',timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
  page=browser.new_page();writes=[];reads=[];payload=b'synthetic frontend lifecycle test'
  p=dict(packageVersion='1.0.0',hfacsExtension=None,profile='MCIS-BASIC-INTAKE-1',caseId='TEST-W85',title='Synthetic test',sourceSha256=hashlib.sha256(payload).hexdigest(),byteLength=len(payload),counts={'evidence':0},warnings=[])
  def route(r):
   url=r.request.url
   if url.endswith('intakes:preview'):r.fulfill(json=p)
   elif url.endswith('intakes:commit'):writes.append(url);r.abort('failed')
   elif '/packages/intakes/' in url:reads.append(url);r.fulfill(json={**p,'importedUtc':'2026-11-12T00:00:00Z','replayed':False})
   elif url.endswith('/cases'):r.fulfill(json=[])
   else:r.fulfill(status=404,json={})
  page.route('**/api/v1/**',route)
  page.goto('http://127.0.0.1:15885/#/lobby')
  page.get_by_role('button',name='选择基础资料包',exact=True).click()
  page.get_by_label('基础资料 .mcase 文件',exact=True).set_input_files({'name':'test.mcase','mimeType':'application/zip','buffer':payload})
  page.get_by_role('button',name='上传并预览基础资料',exact=True).click()
  page.get_by_text('服务端受限恢复范围预览',exact=True).wait_for()
  commit=page.get_by_role('button',name='确认首次导入',exact=True);assert commit.is_disabled()
  page.get_by_role('checkbox',name='我已核对案号').check();commit.click()
  page.get_by_text('导入结果待核对',exact=False).wait_for();assert commit.is_disabled();assert len(writes)==1
  page.get_by_role('button',name='只读查询回执',exact=True).click()
  page.get_by_text('已核验服务端导入回执',exact=True).wait_for();assert len(writes)==1 and len(reads)==1
  page.get_by_role('link',name='进入导入案件',exact=True).click();assert 'case=TEST-W85' in page.url
  browser.close()
 print('W8.5 browser: explicit confirmation, unknown commit no retry, GET recovery, case link passed (API doubles)')
finally:os.killpg(server.pid,signal.SIGTERM);server.wait()
