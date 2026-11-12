from pathlib import Path
import os,subprocess,time,urllib.request,json,signal,traceback,zipfile,io,tempfile,sys
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];SCRIPT=Path(__file__).resolve().parent
OUT=Path(os.environ.get('MCIS_W83_ARTIFACT_DIR',tempfile.mkdtemp(prefix='mcis-w83-qa-')));OUT.mkdir(parents=True,exist_ok=True)
SERVICE=Path(os.environ.get('MCIS_W83_SERVICE_ROOT',ROOT/'service'))
PY=Path(os.environ.get('MCIS_W83_PYTHON',SERVICE/'.venv/bin/python'))
BIN=os.environ.get('MCIS_BROWSER_BIN')
if not BIN: raise RuntimeError('Set MCIS_BROWSER_BIN to your installed Chromium executable')
checks=[];procs=[];errors=[]
def ck(name,v):
 checks.append({'name':name,'passed':bool(v)});assert v,name
base='http://127.0.0.1:15883'
env=dict(os.environ,MCIS_DATA_DIR=tempfile.mkdtemp(prefix='mcis-w83-data-'),PYTHONPATH=os.pathsep.join([str(SERVICE),str(SCRIPT)]),MCIS_W83_ARTIFACT_DIR=str(OUT),MCIS_API='http://127.0.0.1:18883')
def start(cmd,cwd,name):
 p=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=open(OUT/name,'w'),stderr=subprocess.STDOUT,start_new_session=True);procs.append(p)
def wait(url):
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 for _ in range(100):
  try:opener.open(url,timeout=1);return
  except Exception:time.sleep(.1)
 raise Exception('server not ready '+url)
try:
 start([str(PY),'-m','uvicorn','qa_app:app','--host','127.0.0.1','--port','18883'],ROOT,'browser-service.log');wait('http://127.0.0.1:18883/api/v1/health')
 start(['npm','run','dev','--','--port','15883'],ROOT/'web','browser-vite.log');wait(base)
 subprocess.run([str(PY),str(SCRIPT/'http_test.py')],check=True,env=env)
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=BIN,headless=True,args=['--no-sandbox','--disable-gpu'])
  page=b.new_page(viewport={'width':1440,'height':900},accept_downloads=True)
  page.on('pageerror',lambda e:errors.append(str(e)))
  requests=[];page.on('request',lambda r:requests.append(r.url) if '/packages:verify' in r.url or '/export' in r.url else None)
  page.goto(base+'/#/lobby');page.get_by_role('button',name='导出案件包：',exact=False).first.wait_for()
  ck('page identity and no blank/overlay',page.title()!='' and page.get_by_role('heading',name='案件大厅').count()==1 and page.locator('vite-error-overlay').count()==0)
  with page.expect_download() as event:page.get_by_role('button',name='导出案件包：',exact=False).first.click()
  d=event.value;d.save_as(str(OUT/'browser-export.mcase'))
  ck('real browser download is readable ZIP',zipfile.is_zipfile(OUT/'browser-export.mcase'))
  ck('download message not false save claim','已交给浏览器下载' in page.locator('body').inner_text())
  page.get_by_role('button',name='选择案件包预检',exact=True).click();file=page.get_by_label('选择 .mcase 文件')
  before=len(requests);file.set_input_files(str(OUT/'browser-export.mcase'));ck('selection alone sends nothing',len(requests)==before)
  page.get_by_role('button',name='上传并预检',exact=True).click();page.get_by_role('heading',name='清单哈希检查通过',exact=True).wait_for()
  ck('real exported file verifies and caveats',all(s in page.locator('body').inner_text() for s in ['CASE-2026-DEMO-LILY-MARY','本次没有导入案件','不代表来源真实']))
  page.screenshot(path=str(OUT/'verified-desktop.png'),full_page=True)
  for name,expected in [('tampered','清单哈希检查未通过'),('missing','清单哈希检查未通过'),('extra','清单哈希检查通过')]:
   file.set_input_files(str(OUT/(name+'.mcase')));ck(name+' selection clears report',page.get_by_role('heading',name='清单哈希检查通过',exact=True).count()==0)
   page.get_by_role('button',name='上传并预检',exact=True).click();page.get_by_role('heading',name=expected,exact=True).wait_for();ck(name+' real result rendered',True)
  ck('extra warning rendered','清单外文件未被清单哈希覆盖' in page.locator('body').inner_text())
  file.set_input_files({'name':'empty.mcase','mimeType':'application/zip','buffer':b''});ck('empty file disabled with error',not page.get_by_role('button',name='上传并预检',exact=True).is_enabled() and '案件包为空' in page.locator('body').inner_text())
  file.set_input_files({'name':'bad.txt','mimeType':'text/plain','buffer':b'x'});ck('extension rejected',not page.get_by_role('button',name='上传并预检',exact=True).is_enabled())
  file.set_input_files({'name':'bad.mcase','mimeType':'application/zip','buffer':b'x'});page.get_by_role('button',name='上传并预检',exact=True).click();page.get_by_role('alert').filter(has_text='服务拒绝案件包').wait_for();ck('422 visible not success',page.get_by_role('heading',name='清单哈希检查通过',exact=True).count()==0)
  for status,payload in [(403,{'code':'FORBIDDEN'}),(500,{'code':'FAIL'}),(200,{'isValid':True})]:
   page.route('**/packages:verify',lambda r,_request,status=status,payload=payload:r.fulfill(status=status,json=payload))
   file.set_input_files(str(OUT/'valid.mcase'));page.get_by_role('button',name='上传并预检',exact=True).click();page.get_by_role('alert').wait_for();ck('HTTP '+str(status)+' or malformed fails closed',page.get_by_role('heading',name='清单哈希检查通过',exact=True).count()==0);page.unroute('**/packages:verify')
  valid={'isValid':True,'tamperedFiles':[],'missingFiles':[],'extraFiles':[],'caseId':'LATE-OLD'}
  def hold():
   held=[];page.route('**/packages:verify',lambda r:held.append(r));return held
  def late(held):
   for r in held:
    try:r.fulfill(json=valid)
    except Exception:pass
   page.unroute('**/packages:verify')
  held=hold();file.set_input_files(str(OUT/'valid.mcase'));before=len(requests);page.get_by_role('button',name='上传并预检',exact=True).dblclick();ck('browser double click sends one',len(requests)==before+1)
  page.get_by_role('button',name='停止等待').click();late(held);ck('cancel late result suppressed','LATE-OLD' not in page.locator('body').inner_text())
  held=hold();page.get_by_role('button',name='上传并预检',exact=True).click();page.get_by_role('button',name='关闭预检').click();late(held);page.get_by_role('button',name='选择案件包预检',exact=True).click();ck('close reopen clears selection and stale result',not page.get_by_role('button',name='上传并预检',exact=True).is_enabled() and 'LATE-OLD' not in page.locator('body').inner_text())
  file=page.get_by_label('选择 .mcase 文件');held=hold();file.set_input_files(str(OUT/'valid.mcase'));page.get_by_role('button',name='上传并预检',exact=True).click();page.locator('select.role-select').select_option('Public');late(held);ck('Public hides upload and export',page.get_by_role('button',name='选择案件包预检',exact=True).count()==0 and page.get_by_role('button',name='导出案件包：',exact=False).count()==0)
  page.locator('select.role-select').select_option('Investigator');page.get_by_role('button',name='选择案件包预检',exact=True).click();ck('return identity has clean form',not page.get_by_role('button',name='上传并预检',exact=True).is_enabled())
  held=hold();file=page.get_by_label('选择 .mcase 文件');file.set_input_files(str(OUT/'valid.mcase'));page.get_by_role('button',name='上传并预检',exact=True).click();page.get_by_role('link',name='进入案件：',exact=False).first.click();page.wait_for_url('**/#/evidence?case=*');late(held);page.go_back();(OUT/'after-back.txt').write_text(page.url+'\n'+page.locator('body').inner_text());page.get_by_role('heading',name='案件大厅',exact=True).wait_for();ck('fast navigation Back no stale package report','LATE-OLD' not in page.locator('body').inner_text())
  
  if page.get_by_role('button',name='选择案件包预检',exact=True).count():page.get_by_role('button',name='选择案件包预检',exact=True).click()
  page.get_by_role('link',name='进入案件：',exact=False).first.click();page.locator('.w4-page').wait_for();page.go_back();page.get_by_role('button',name='选择案件包预检',exact=True).wait_for();ck('normal navigation Back resets form',True)
  page.go_forward();page.locator('.w4-page').wait_for();page.go_back();page.get_by_role('button',name='选择案件包预检',exact=True).wait_for();ck('Forward and Back do not restore precheck',page.get_by_role('heading',name='清单哈希检查通过',exact=True).count()==0)
  page.get_by_role('link',name='船舶参数',exact=False).first.click();page.wait_for_url('**/#/ships*');page.locator('.w9-page').wait_for();page.go_back();page.get_by_role('heading',name='案件大厅',exact=True).wait_for();ck('integrated W9 ships navigation and Back',page.get_by_role('heading',name='清单哈希检查通过',exact=True).count()==0)
  # Explicit delayed export race: navigating must not deliver the old package.
  held_exports=[];downloads=[];page.on('download',lambda d:downloads.append(d))
  page.route('**/export',lambda r:held_exports.append(r));page.get_by_role('button',name='导出案件包：',exact=False).first.click()
  page.get_by_role('link',name='进入案件：',exact=False).first.click();page.wait_for_url('**/#/evidence?case=*')
  for r in held_exports:
   try:r.fulfill(body=(OUT/'valid.mcase').read_bytes(),content_type='application/zip')
   except Exception:pass
  page.unroute('**/export');page.go_back();page.get_by_role('heading',name='案件大厅',exact=True).wait_for();ck('delayed export after navigation does not download',not downloads)
  if page.get_by_role('button',name='选择案件包预检',exact=True).count():page.get_by_role('button',name='选择案件包预检',exact=True).click()
  for width,height in [(1440,900),(1920,1080)]:
   page.set_viewport_size({'width':width,'height':height});ck(str(width)+' desktop no horizontal overflow',page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'));page.screenshot(path=str(OUT/('desktop-'+str(width)+'.png')),full_page=False)
  page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(OUT/'mobile.png'),full_page=True)
  mobile=page.evaluate('document.documentElement.scrollWidth');hide=page.add_style_tag(content='.w83-package,.w83-export{display:none!important}');baseline=page.evaluate('document.documentElement.scrollWidth');hide.evaluate('(e)=>e.remove()')
  checks.append({'name':'390px shared-shell overflow','passed':mobile<=390,'knownDefect':mobile>390 and mobile==baseline,'widthWithW83':mobile,'widthWithW83Hidden':baseline})
  ck('W83 adds no mobile overflow beyond existing shell',mobile==baseline)
  ck('no JS runtime exceptions',not errors);b.close()
except Exception:
 try:
  (OUT/'failure-body.txt').write_text(page.url+'\n'+page.locator('body').inner_text());page.screenshot(path=str(OUT/'failure.png'),full_page=True)
 except Exception:pass
 (OUT/'browser-error.txt').write_text(traceback.format_exc());raise
finally:
 (OUT/'browser-results.json').write_text(json.dumps({'checks':checks,'errors':errors},ensure_ascii=False,indent=2))
 for p in procs:
  try:os.killpg(p.pid,signal.SIGTERM)
  except ProcessLookupError:pass
print(f"{sum(c['passed'] for c in checks)} browser checks passed; {sum(bool(c.get('knownDefect')) for c in checks)} known shared-shell defect")
