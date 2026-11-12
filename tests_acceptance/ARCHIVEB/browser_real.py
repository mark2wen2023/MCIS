"""Actual browser download/import/reopen across two isolated synthetic services."""
import os,signal,subprocess,tempfile,time,urllib.request,json,io,zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent
with tempfile.TemporaryDirectory(prefix='archiveb-browser-') as tmp:
 procs=[]
 try:
  for i in (0,1):
   env={**os.environ,'MCIS_DATA_DIR':f'{tmp}/data{i}','MCIS_API':f'http://127.0.0.1:{15980+i}','PYTHONPATH':str(ROOT/'service'),'MCIS_DOTNET':os.environ.get('MCIS_DOTNET',str(Path.home()/'.dotnet/dotnet')),'DOTNET_CLI_HOME':tmp+'/dotnet','ARCHIVE_PORT':str(15980+i),'ARCHIVE_SEED':str(1-i)}
   procs.append(subprocess.Popen([str(ROOT/'service/.venv/bin/python'),str(HERE/'server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True))
   procs.append(subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',str(15982+i),'--strictPort'],cwd=ROOT/'web',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True))
  for port in (15980,15981,15982,15983):
   for _ in range(200):
    try:urllib.request.urlopen(f'http://127.0.0.1:{port}'+('/api/v1/health' if port<15982 else '/'),timeout=1);break
    except Exception:time.sleep(.1)
   else:raise RuntimeError('synthetic servers failed to start')
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.environ['MCIS_BROWSER_BIN'],headless=True,args=['--no-sandbox'],env={**os.environ,'HOME':tmp,'XDG_CONFIG_HOME':tmp+'/config'})
   page=browser.new_page();page.add_init_script("localStorage.setItem('mcis.role','LeadInvestigator')");errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto('http://127.0.0.1:15982/#/lobby')
   with page.expect_download() as download:page.get_by_role('button',name='导出案件包：Synthetic working archive',exact=True).click()
   path=tmp+'/actual.mcase';download.value.save_as(path)
   with zipfile.ZipFile(path) as z:original=json.loads(z.read('working-records/backup.v1.json'))
   rid=original['interviews'][0]['key'];rpt=original['reports'][0]['key']
   page.goto('http://127.0.0.1:15983/#/lobby');page.get_by_role('button',name='选择基础资料包',exact=True).click()
   page.get_by_label('基础资料 .mcase 文件',exact=True).set_input_files(path)
   page.get_by_role('button',name='上传并预览基础资料',exact=True).click();page.get_by_text('服务端受限恢复范围预览',exact=True).wait_for()
   confirm=page.get_by_role('button',name='确认首次导入',exact=True);assert confirm.is_disabled()
   page.get_by_role('checkbox',name='我已核对案号').check();confirm.click();page.get_by_text('已核验服务端导入回执',exact=True).wait_for()
   page.goto('http://127.0.0.1:15983/#/interview?case=SYN-ARCHIVE-B&record='+rid)
   page.get_by_role('heading',name='此对象包含恢复历史',exact=True).first.wait_for()
   assert '原回答0' in page.locator('body').inner_text()
   page.reload();page.get_by_role('heading',name='此对象包含恢复历史',exact=True).first.wait_for()
   page.goto('http://127.0.0.1:15983/#/report?case=SYN-ARCHIVE-B&report='+rpt)
   page.get_by_role('heading',name='此对象包含恢复历史',exact=True).wait_for()
   page.locator('select[title="X-MCIS-Role"]').select_option('Investigator')
   page.wait_for_timeout(300)
   assert page.get_by_role('heading',name='此对象包含恢复历史',exact=True).count()==0
   page.locator('select[title="X-MCIS-Role"]').select_option('LeadInvestigator')
   page.goto('http://127.0.0.1:15983/#/evidence?case=SYN-ARCHIVE-B')
   page.get_by_role('button',name='＋ 登记已有文件副本 / 查看登记原件',exact=True).click()
   page.get_by_role('button',name='读取当前证据登记回执（只读）',exact=True).click()
   page.get_by_role('complementary',name='历史原件访问').wait_for()
   with page.expect_download() as history_download:page.get_by_role('button',name='记录访问并下载历史原件',exact=True).click()
   history_path=tmp+'/history.bin';history_download.value.save_as(history_path)
   assert Path(history_path).read_bytes()=='SYNTHETIC ONLY: 中文🚢原件\n'.encode()
   # Only delay a genuine provenance request; revoke policy on the real service.
   held=[]
   def hold_provenance(route):held.append(route)
   pattern='**/archive-history/provenance/report/*'
   page.route(pattern,hold_provenance)
   page.goto('http://127.0.0.1:15983/#/report?case=SYN-ARCHIVE-B&report='+rpt)
   page.locator('.rpt-sentence').first.wait_for()
   for _ in range(100):
    if held:break
    page.wait_for_timeout(20)
   assert held
   policy_url='http://127.0.0.1:15981/api/v1/cases/SYN-ARCHIVE-B/access-policy';headers={'X-MCIS-Role':'LeadInvestigator'}
   policy=page.request.get(policy_url,headers=headers).json()
   import copy
   revoked=copy.deepcopy(policy);revoked['matrix']['LeadInvestigator']['audit']='Deny'
   assert page.request.put(policy_url,headers=headers,data=revoked).status==200
   with page.expect_response(lambda r:'/archive-history/provenance/report/' in r.url) as response:held.pop().continue_()
   assert response.value.status==403
   page.wait_for_function("document.querySelectorAll('.rpt-sentence').length===0")
   assert page.get_by_role('heading',name='此对象包含恢复历史',exact=True).count()==0
   page.unroute(pattern,hold_provenance)
   assert page.request.put(policy_url,headers=headers,data=policy).status==200
   page.goto('http://127.0.0.1:15983/#/lobby')
   with page.expect_download() as download:page.get_by_role('button',name='导出案件包：Synthetic working archive',exact=True).click()
   path2=tmp+'/again.mcase';download.value.save_as(path2)
   with zipfile.ZipFile(path2) as z:
    again=json.loads(z.read('working-records/backup.v1.json'))
    for key in ('interviews','reports','reportSnapshots','manualReceipts'):assert again[key]==original[key]
   assert not errors,errors;browser.close()
  print('PASS actual browser/services: source export, target preview/explicit-confirm import, transcript/report provenance and reload, identity clears label, re-export exact records. No API doubles.')
 finally:
  for p in procs:
   if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
  for p in procs:p.wait()
