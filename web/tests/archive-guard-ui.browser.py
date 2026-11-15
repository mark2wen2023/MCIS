"""UI/API doubles: refusal message and no download, not backend acceptance."""
import subprocess,time,urllib.request,os,signal
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
s=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15854','--strictPort'],cwd=ROOT/'web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
try:
 for _ in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:15854',timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox']);p=b.new_page();p.set_default_timeout(8000);downloads=[];p.on('download',lambda d:downloads.append(d))
  def route(r):
   if r.request.url.endswith('/cases'):r.fulfill(json=[dict(caseId='SYNTHETIC',title='Archive synthetic',isFictionalDemo=True)])
   elif r.request.url.endswith('/export'):r.fulfill(status=409,json=dict(code='ARCHIVE_RESTORE_UNSUPPORTED',message='private detail'))
   else:r.fulfill(status=403,json=dict(code='FORBIDDEN'))
  p.route('**/api/v1/**',route);p.goto('http://127.0.0.1:15854/#/lobby');p.get_by_label('导出案件包：Archive synthetic',exact=True).click()
  p.get_by_text('整个案件包导出已拒绝',exact=False).wait_for();assert not downloads;assert 'private detail' not in p.locator('body').inner_text()
  p.goto('http://127.0.0.1:15854/#/report?case=SYNTHETIC');p.get_by_text('报告文件导出不等于案件备份',exact=False).wait_for()
  p.goto('http://127.0.0.1:15854/#/interview?case=SYNTHETIC');p.get_by_text('笔录仅在匹配版本的受限归档全部校验通过时支持同案号新案恢复',exact=False).wait_for()
  p.unroute_all(behavior='ignoreErrors');b.close()
 print('Archive guard browser:409 refused/no download;report/interview warnings visible(API doubles)')
finally:os.killpg(s.pid,signal.SIGTERM);s.wait()
