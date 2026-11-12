"""Independent real API + browser acceptance, disposable data; no mock response."""
import os,signal,subprocess,tempfile,time,urllib.request,json,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
SERV=ROOT/'service'
with tempfile.TemporaryDirectory(prefix='w85-accept-') as tmp:
 env={**os.environ,'MCIS_DATA_DIR':tmp+'/data','MCIS_SEED_DEMO':'0','MCIS_PORT':'15886','MCIS_API':'http://127.0.0.1:15886'}
 raw=subprocess.check_output([str(SERV/'.venv/bin/python'),'-c',f'import sys;sys.path.insert(0,{str(Path(__file__).parent)!r});from test_intake_independent import files,package;sys.stdout.buffer.write(package(files()))'],cwd=SERV)
 back=subprocess.Popen([str(SERV/'.venv/bin/python'),'-m','mcis_service'],cwd=SERV,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 front=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15887','--strictPort'],cwd=ROOT/'web',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 try:
  for port,path in [(15886,'/api/v1/health'),(15887,'/')]:
   for _ in range(100):
    try:urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',timeout=1);break
    except Exception:time.sleep(.1)
   else:raise RuntimeError('local startup failed')
  with sync_playwright() as p:
   browser=p.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox'],env={**os.environ,'HOME':tmp,'XDG_CONFIG_HOME':tmp+'/config'});page=browser.new_page()
   errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto('http://127.0.0.1:15887/#/lobby')
   page.get_by_role('button',name='选择基础资料包',exact=True).click()
   page.get_by_label('基础资料 .mcase 文件',exact=True).set_input_files({'name':'independent.mcase','mimeType':'application/zip','buffer':raw})
   page.get_by_role('button',name='上传并预览基础资料',exact=True).click()
   page.get_by_text('服务端基础资料预览',exact=True).wait_for()
   assert page.get_by_role('button',name='确认首次导入',exact=True).is_disabled()
   page.get_by_role('checkbox',name='我已核对案号').check()
   page.get_by_role('button',name='确认首次导入',exact=True).click()
   page.get_by_text('已核验服务端导入回执',exact=True).wait_for()
   assert page.get_by_role('button',name='确认首次导入',exact=True).is_disabled()
   page.get_by_role('button',name='只读查询回执',exact=True).click()
   page.get_by_text('已存在的同包回执',exact=False).wait_for()
   page.get_by_role('link',name='进入导入案件',exact=True).click()
   assert 'case=CASE-ACCEPT-W85' in page.url
   archive=Path(tmp)/'data/blobs/CASE-ACCEPT-W85/_package_intake/source.mcase'
   assert archive.read_bytes()==raw
   receipt=json.load(urllib.request.urlopen('http://127.0.0.1:15886/api/v1/packages/intakes/'+hashlib.sha256(raw).hexdigest()))
   assert receipt['caseId']=='CASE-ACCEPT-W85' and receipt['replayed'] is True
   assert not errors,errors
   browser.close()
  print('PASS: real API preview -> explicit confirmation -> commit receipt -> GET recovery -> case link; original archive byte-identical; no page errors.')
 finally:
  for proc in (front,back):
   os.killpg(proc.pid,signal.SIGTERM);proc.wait()
