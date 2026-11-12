"""Two real services/browser; lost response simulated only AFTER real committed save."""
import os,signal,subprocess,tempfile,time,urllib.request,json,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent
with tempfile.TemporaryDirectory(prefix='knowledge-archive-') as tmp:
 procs=[]
 try:
  for i in (0,1):
   env={**os.environ,'MCIS_DATA_DIR':f'{tmp}/data{i}','MCIS_API':f'http://127.0.0.1:{15990+i}','PYTHONPATH':str(ROOT/'service'),'ARCHIVE_PORT':str(15990+i),'ARCHIVE_SEED':str(1-i)}
   procs.append(subprocess.Popen([str(ROOT/'service/.venv/bin/python'),str(HERE/'server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True))
   procs.append(subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',str(15992+i),'--strictPort'],cwd=ROOT/'web',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True))
  for port in (15990,15991,15992,15993):
   for _ in range(150):
    try:urllib.request.urlopen(f'http://127.0.0.1:{port}'+('/api/v1/health' if port<15992 else '/'),timeout=1);break
    except Exception:time.sleep(.1)
   else:raise RuntimeError('synthetic services startup failed')
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.environ['MCIS_BROWSER_BIN'],headless=True,args=['--no-sandbox']);p=browser.new_page();p.set_default_timeout(10000);errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
   p.add_init_script("if(!localStorage.getItem('mcis.role'))localStorage.setItem('mcis.role','LeadInvestigator')")
   def open_panel():p.get_by_text('全局知识库独立归档（首席限定）',exact=True).click()
   p.goto('http://127.0.0.1:15992/#/knowledge');open_panel()
   with p.expect_download() as dl:p.get_by_role('button',name='导出当前在线快照',exact=True).click()
   path=tmp+'/source.json';dl.value.save_as(path);raw=Path(path).read_bytes();sha=hashlib.sha256(raw).hexdigest();envelope=json.loads(raw)
   assert len(envelope['cards'])==3 and len(envelope['auditSnapshots']['items'])==7
   p.goto('http://127.0.0.1:15993/#/knowledge');open_panel()
   def prepare():
    p.get_by_label('选择 UTF-8 JSON（最多 8 MiB，非 ZIP）',exact=True).set_input_files(path)
    p.get_by_label('我已核对摘要与范围，明确保存为独立只读历史，不恢复或公开在线知识卡',exact=True).check()
   prepare();posts=[]
   def lose_after_commit(route):
    result=route.fetch();assert result.status==201;posts.append(result.json());route.fulfill(status=503,json={'code':'SIMULATED_LOST_SUCCESS'})
   pattern='**/api/v1/knowledge/archives';p.route(pattern,lose_after_commit)
   p.get_by_role('button',name='确认保存历史',exact=True).click();p.get_by_text('503 SIMULATED_LOST_SUCCESS',exact=True).wait_for();p.unroute(pattern,lose_after_commit)
   assert len(posts)==1 and p.get_by_label('选择 UTF-8 JSON（最多 8 MiB，非 ZIP）',exact=True).is_disabled()
   p.get_by_label('重新选择原包（必须与待核摘要完全相同）',exact=True).set_input_files(path)
   p.get_by_label('我确认仅重试同一原包，不创建新操作',exact=True).check()
   p.get_by_role('button',name='用完全相同原包重试',exact=True).click();p.get_by_text('已核验历史保存回执',exact=False).wait_for()
   base='http://127.0.0.1:15991/api/v1/knowledge';headers={'X-MCIS-Role':'LeadInvestigator'}
   assert p.request.get(base+'/archives',headers=headers).json()['total']==1
   assert p.request.get(base+'/cards',headers={'X-MCIS-Role':'Public'}).json()['total']==0
   assert p.request.get(base+'/audit',headers=headers).json()==[]
   p.get_by_role('button',name='读取只读历史列表',exact=True).click();p.get_by_role('button',name='浏览历史原文',exact=True).click();p.get_by_role('heading',name='历史原文（不是当前在线状态）',exact=True).wait_for()
   assert json.loads(p.locator('.w19-archive pre').inner_text())==envelope
   with p.expect_download() as dl:p.get_by_role('button',name='校验并下载历史原包',exact=True).click()
   assert Path(dl.value.path()).read_bytes()==raw
   p.reload();open_panel();p.get_by_role('button',name='读取只读历史列表',exact=True).click();p.get_by_role('button',name='浏览历史原文',exact=True).click();p.get_by_role('heading',name='历史原文（不是当前在线状态）',exact=True).wait_for()
   p.locator('select[title="X-MCIS-Role"]').select_option('Investigator');p.wait_for_timeout(100);assert p.locator('.w19-archive pre').count()==0 and sha not in p.locator('body').inner_text()
   p.locator('select[title="X-MCIS-Role"]').select_option('LeadInvestigator');open_panel();prepare()
   def precheck_reject(route):
    request_headers={**route.request.headers,'x-archive-sha256':'f'*64};route.continue_(headers=request_headers)
   p.route(pattern,precheck_reject);p.get_by_role('button',name='确认保存历史',exact=True).click();p.get_by_text('409 KNOWLEDGE_ARCHIVE_CHANGED',exact=True).wait_for();p.unroute(pattern,precheck_reject)
   assert not p.get_by_label('选择 UTF-8 JSON（最多 8 MiB，非 ZIP）',exact=True).is_disabled()
   assert p.request.get(base+'/archives',headers=headers).json()['total']==1
   assert not errors,errors;browser.close()
  print('PASS real two-service browser: source export, explicit preview/save, committed-response503 then exact-byte retry, one history/no online activation, exact download/reopen, role clears body, real pretransaction409 marker releases lock.')
 finally:
  for p in procs:
   if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
  for p in procs:p.wait()
