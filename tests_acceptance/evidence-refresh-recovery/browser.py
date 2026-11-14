import os,json,tempfile,subprocess,time,urllib.request,signal
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];OUT=Path(os.environ.get('MCIS_QA_OUT',tempfile.mkdtemp(prefix='mcis-refresh-review-')));OUT.mkdir(parents=True,exist_ok=True);fixed=os.environ.get('EXPECT_FIXED','1')=='1'
API=18942;PORT=15942;data=Path(tempfile.mkdtemp(prefix='feedback-'));procs=[]
env=dict(os.environ,MCIS_DATA_DIR=str(data),MCIS_API=f'http://127.0.0.1:{API}',MCIS_AGENT_BASE_URL='',MCIS_AGENT_MODEL='',PYTHONPATH=str(ROOT/'service'))
def start(cmd,cwd,name):
 p=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=open(OUT/name,'w'),stderr=subprocess.STDOUT,start_new_session=True);procs.append(p)
def req(path,body=None,headers={}):
 r=urllib.request.Request(f'http://127.0.0.1:{API}'+path,data=json.dumps(body).encode() if body else None,headers={'Content-Type':'application/json',**headers});return json.load(urllib.request.build_opener(urllib.request.ProxyHandler({})).open(r))
def wait(url):
 for _ in range(100):
  try:urllib.request.urlopen(url,timeout=1);return
  except Exception:time.sleep(.1)
 raise RuntimeError('startup')
try:
 fixture=ROOT/'web/tests/evidence-intake-w42.fixture.py'
 start([str(ROOT/'service/.venv/bin/python'),'-c',f"import importlib.util,uvicorn;s=importlib.util.spec_from_file_location('f',{str(fixture)!r});m=importlib.util.module_from_spec(s);s.loader.exec_module(m);uvicorn.run(m.app,host='127.0.0.1',port={API})"],ROOT,'service.log');wait(f'http://127.0.0.1:{API}/api/v1/health')
 start(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',str(PORT),'--strictPort'],ROOT/'web','vite.log');wait(f'http://127.0.0.1:{PORT}')
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1000});console=[];page.on('console',lambda m:console.append({'type':m.type,'text':m.text}) if m.type in ('error','warning') else None);errors=[];page.on('pageerror',lambda e:errors.append(str(e)));writes=[];page.on('request',lambda r:writes.append(r.url) if r.url.endswith('evidence-intakes:commit') else None)
  page.goto(f'http://127.0.0.1:{PORT}/#/evidence?case=QA-W42-A');page.get_by_role('button',name='＋ 登记已有文件副本 / 查看登记原件',exact=True).click()
  for label,value in [('证据标题（必填）','synthetic conflict'),('原来源 / 取得或移交方式（必填）','synthetic declared source'),('提取人（必填，非当前登记人默认值）','synthetic collector'),('提取时间 UTC（整秒，必填）','2026-01-01T00:00:00Z')]:page.get_by_label(label,exact=True).fill(value)
  page.get_by_label('原件文件（最多 8 MiB，可为零字节）',exact=True).set_input_files({'name':'synthetic.bin','mimeType':'application/octet-stream','buffer':b'synthetic original'})
  page.get_by_text('本地文件：synthetic.bin',exact=False).wait_for()
  with page.expect_response(lambda r:r.url.endswith('evidence-intakes:preview')) as response:page.get_by_role('button',name='服务端预览（不登记）',exact=True).click()
  response=response.value;preview=response.json();body=response.request.post_data_json
  heads={k:v for k,v in response.request.headers.items() if k in ('x-mcis-role','x-mcis-operator')}
  saved=req('/api/v1/cases/QA-W42-A/evidence-intakes:commit',{**body,'requestDigest':preview['requestDigest'],'confirmed':True},heads)
  paths=list(data.rglob('source.bin'));assert len(paths)==1;paths[0].write_bytes(b'synthetic local mutation')
  page.get_by_label('我已核对目标案件',exact=False).check()
  with page.expect_response(lambda r:r.url.endswith('evidence-intakes:commit')) as response:page.get_by_role('button',name='确认登记文件副本',exact=True).click()
  result=response.value;assert result.status==409 and result.json()['code']=='INTAKE_INTEGRITY'
  page.wait_for_timeout(300)
  locked=page.get_by_label('证据标题（必填）',exact=True).is_disabled()
  assert locked==fixed,{'locked':locked,'fixed':fixed}
  if fixed:
   assert page.get_by_role('button',name='只读核查本次登记',exact=True).count()==1
   assert page.get_by_role('button',name='同一内容幂等重试登记',exact=True).count()==0
   page.get_by_role('button',name='只读核查本次登记',exact=True).click();page.wait_for_timeout(300);assert page.get_by_label('证据标题（必填）',exact=True).is_disabled()
  assert len(writes)==1 and req('/api/v1/cases/QA-W42-A/custody:verify-chain')['count']==1
  page.screenshot(path=str(OUT/('after.png' if fixed else 'before.png')),full_page=True)
  result={'browserVersion':b.version,'fixed':fixed,'url':page.url,'title':page.title(),'status':409,'code':'INTAKE_INTEGRITY','locked':locked,'browserCommitPosts':len(writes),'registerCount':1,'pageErrors':errors,'console':console,'body':page.locator('.w42-panel').inner_text()}
  assert not errors and page.locator('vite-error-overlay').count()==0
  if fixed:
   page.goto(f'http://127.0.0.1:{PORT}/#/evidence?case=QA-W42-B');page.get_by_role('button',name='＋ 登记已有文件副本 / 查看登记原件',exact=True).click()
   for label,value in [('证据标题（必填）','synthetic lost response'),('原来源 / 取得或移交方式（必填）','synthetic declared source'),('提取人（必填，非当前登记人默认值）','synthetic collector'),('提取时间 UTC（整秒，必填）','2026-01-01T00:00:00Z')]:page.get_by_label(label,exact=True).fill(value)
   page.get_by_label('原件文件（最多 8 MiB，可为零字节）',exact=True).set_input_files({'name':'lost.bin','mimeType':'application/octet-stream','buffer':b'synthetic committed bytes'})
   page.get_by_text('本地文件：lost.bin',exact=False).wait_for()
   page.get_by_role('button',name='服务端预览（不登记）',exact=True).click();page.get_by_label('我已核对目标案件',exact=False).check()
   def lose_response(route):
    real=route.fetch();assert real.status==200;route.abort('failed')
   page.route('**/QA-W42-B/evidence-intakes:commit',lose_response)
   page.get_by_role('button',name='确认登记文件副本',exact=True).click()
   page.get_by_text('登记结果未确认，服务器可能已经保存。',exact=False).wait_for()
   assert page.get_by_label('证据标题（必填）',exact=True).is_disabled()
   assert page.get_by_role('button',name='同一内容幂等重试登记',exact=True).count()==0
   assert req('/api/v1/cases/QA-W42-B/custody:verify-chain')['count']==1
   page.screenshot(path=str(OUT/'unknown.png'),full_page=True)
   marker=page.evaluate("JSON.parse(sessionStorage.getItem('mcis.evidence-intake.pending.v1:QA-W42-B'))")
   assert set(marker)=={'caseId','requestDigest','sourceSha256','byteLength'}
   page.reload();page.get_by_role('button',name='＋ 登记已有文件副本 / 查看登记原件',exact=True).click()
   assert page.get_by_label('证据标题（必填）',exact=True).is_disabled() and page.get_by_label('证据标题（必填）',exact=True).input_value()==''
   assert page.get_by_label('原件文件（最多 8 MiB，可为零字节）',exact=True).input_value()==''
   assert len(writes)==2
   recovery_url='**/QA-W42-B/evidence-intakes/'+marker['requestDigest']
   page.route(recovery_url,lambda route:route.fulfill(status=404,json={'code':'INTAKE_NOT_FOUND'}))
   page.get_by_role('button',name='只读核查本次登记',exact=True).click();page.get_by_text('核查时尚无回执',exact=False).wait_for()
   assert page.get_by_label('证据标题（必填）',exact=True).is_disabled()
   assert page.evaluate("sessionStorage.getItem('mcis.evidence-intake.pending.v1:QA-W42-B')")
   page.unroute(recovery_url)
   policy=req('/api/v1/cases/QA-W42-B/access-policy')
   denied=json.loads(json.dumps(policy));denied['matrix']['Investigator']['evidence_meta']='Deny'
   def put_policy(value):
    request=urllib.request.Request(f'http://127.0.0.1:{API}/api/v1/cases/QA-W42-B/access-policy',data=json.dumps(value).encode(),headers={'Content-Type':'application/json','X-MCIS-Role':'LeadInvestigator'},method='PUT')
    return json.load(urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request))
   put_policy(denied)
   with page.expect_response(lambda r:r.url.endswith(marker['requestDigest'])) as denied_response:page.get_by_role('button',name='只读核查本次登记',exact=True).click()
   assert denied_response.value.status==403
   assert page.evaluate("sessionStorage.getItem('mcis.evidence-intake.pending.v1:QA-W42-B')")
   assert page.get_by_label('证据标题（必填）',exact=True).is_disabled()
   put_policy(policy)
   page.screenshot(path=str(OUT/'refresh-404.png'),full_page=True)
   page.get_by_role('button',name='只读核查本次登记',exact=True).click()
   page.get_by_role('heading',name='已核对登记回执 · EV-001',exact=True).wait_for()
   assert page.evaluate("sessionStorage.getItem('mcis.evidence-intake.pending.v1:QA-W42-B')") is None

   assert len(writes)==2 and req('/api/v1/cases/QA-W42-B/custody:verify-chain')['count']==1
   result['lostResponse']='actual commit200 then injected transport loss; reload restores only marker; injected GET404 and real policy403 retain marker; restored policy real GET recovers; no second commit'
  (OUT/('after.json' if fixed else 'before.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='body'},ensure_ascii=False));b.close()
finally:
 for p in procs:os.killpg(p.pid,signal.SIGTERM)
 for p in procs:p.wait(timeout=10)
