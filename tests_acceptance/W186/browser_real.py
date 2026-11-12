"""Actual browser download/import/reopen across two isolated synthetic services."""
import os,signal,subprocess,tempfile,time,urllib.request,json,io,zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent
with tempfile.TemporaryDirectory(prefix='w186-browser-') as tmp:
 procs=[]
 try:
  for i in (0,1):
   env={**os.environ,'MCIS_DATA_DIR':f'{tmp}/data{i}','MCIS_API':f'http://127.0.0.1:{15990+i}','PYTHONPATH':str(ROOT/'service'),'MCIS_DOTNET':os.environ.get('MCIS_DOTNET',str(Path.home()/'.dotnet/dotnet')),'DOTNET_CLI_HOME':tmp+'/dotnet','W186_PORT':str(15990+i),'W186_SEED':str(1-i)}
   procs.append(subprocess.Popen([str(ROOT/'service/.venv/bin/python'),str(HERE/'server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True))
   procs.append(subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',str(15992+i),'--strictPort'],cwd=ROOT/'web',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True))
  for port in (15990,15991,15992,15993):
   for _ in range(200):
    try:urllib.request.urlopen(f'http://127.0.0.1:{port}'+('/api/v1/health' if port<15992 else '/'),timeout=1);break
    except Exception:time.sleep(.1)
   else:raise RuntimeError('synthetic servers failed to start')
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.environ['MCIS_BROWSER_BIN'],headless=True,args=['--no-sandbox'],env={**os.environ,'HOME':tmp,'XDG_CONFIG_HOME':tmp+'/config'})
   page=browser.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto('http://127.0.0.1:15992/#/hf?case=SYN-W186')
   page.get_by_role('button',name='人工分类草稿（可保存）',exact=True).click()
   page.get_by_label('调查范围 / 工作任务情境',exact=True).fill('合成可恢复任务 🛳')
   page.get_by_role('button',name='添加人工条目',exact=True).click()
   page.get_by_label('条目 ID 1',exact=True).fill('F1');page.get_by_label('项目分类 1',exact=True).select_option('UA-ERR-DEC')
   page.get_by_label('情境描述 1',exact=True).fill('合成情境');page.get_by_label('人工分类理由 1',exact=True).fill('待核查，不是事实确认')
   page.get_by_role('button',name='保存人工分类草稿',exact=True).click();page.get_by_text('已核验此请求的保存回执',exact=False).wait_for()
   page.goto('http://127.0.0.1:15992/#/lobby')
   with page.expect_download() as download:page.get_by_role('button',name='导出案件包：合成备份验收',exact=True).click()
   path=tmp+'/actual.mcase';download.value.save_as(path)
   def archive(path):
    with zipfile.ZipFile(path) as z:
     assert json.loads(z.read('manifest.json'))['packageVersion']=='1.1.0'
     return json.loads(z.read('hfacs/backup.v1.json'))
   original=archive(path);assert len(original['revisionAudit'])==1
   page.goto('http://127.0.0.1:15993/#/lobby');page.get_by_role('button',name='选择基础资料包',exact=True).click()
   page.get_by_label('基础资料 .mcase 文件',exact=True).set_input_files(path)
   page.get_by_role('button',name='上传并预览基础资料',exact=True).click();page.get_by_text('服务端基础资料预览',exact=True).wait_for()
   assert page.get_by_label('HFACS扩展范围',exact=True).get_by_text('历史回执仅归档',exact=False).is_visible()
   assert page.get_by_text('历史请求回执数',exact=True).is_visible()
   confirm=page.get_by_role('button',name='确认首次导入',exact=True);assert confirm.is_disabled()
   page.get_by_role('checkbox',name='我已核对案号').check();confirm.click();page.get_by_text('已核验服务端导入回执',exact=True).wait_for()
   page.goto('http://127.0.0.1:15993/#/hf?case=SYN-W186');page.get_by_role('button',name='人工分类草稿（可保存）',exact=True).click()
   scope=page.get_by_label('调查范围 / 工作任务情境',exact=True);scope.wait_for();assert scope.input_value()=='合成可恢复任务 🛳'
   page.reload();page.get_by_role('button',name='人工分类草稿（可保存）',exact=True).click();scope.wait_for();assert scope.input_value()=='合成可恢复任务 🛳'
   page.goto('http://127.0.0.1:15993/#/lobby')
   with page.expect_download() as download:page.get_by_role('button',name='导出案件包：合成备份验收',exact=True).click()
   path2=tmp+'/restored.mcase';download.value.save_as(path2);assert archive(path2)==original
   assert not errors,errors;browser.close()
  print('PASS actual browser/API/CLI: manual draft save, real ZIP download, confirmed import into second empty service, reload/reopen, re-export complete HFACS archive equality; no API doubles.')
 finally:
  for p in procs:
   if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
  for p in procs:p.wait()
