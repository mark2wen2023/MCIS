"""W11 existing ECFC editor: real sandboxed Chrome -> real loopback FastAPI + real C# CLI -> temporary SQLite.
Preview (zero write) -> one explicit save -> restart the service on the same SQLite -> reopen in the existing page.
No API doubles, no route interception of /api. Fictional data only. Not layout/source-link/archive/replay acceptance."""
import hashlib,json,os,socket,sqlite3,subprocess,sys,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent
OUT=Path(os.environ.get('W11_SAVE_OUT','/tmp/w11-ecfc-real-save-out'));OUT.mkdir(parents=True,exist_ok=True)
PY=os.environ['W11_SERVICE_PYTHON'];CHROME=os.environ.get('MCIS_BROWSER_BIN','/opt/google/chrome/google-chrome');CID='W11-REAL-SAVE-FICTIONAL'
receipt={'chrome':CHROME,'sandbox':'chromium_sandbox=True, no --no-sandbox','apiDoubles':False,'checks':{},'phases':{},'console':[],'pageerrors':[],'blockedExternal':[]}
def check(v,label):receipt['checks'][label]=bool(v);assert v,label
data=Path(tempfile.mkdtemp(prefix='w11-ecfc-real-save-'));receipt['tempData']=str(data)
def counts():
 with sqlite3.connect(data/'mcis.db') as s:return [s.execute('select count(*) from '+t).fetchone()[0] for t in ('ecfc_drafts','ecfc_draft_audit','ecfc_draft_requests')]
log=open(OUT/'services.log','w');procs={}
def free_port():
 s=socket.socket();s.bind(('127.0.0.1',0));p=s.getsockname()[1];s.close();return p
apiport,webport=free_port(),free_port()
def start_api(tag):
 l=socket.socket();l.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);l.bind(('127.0.0.1',apiport));l.listen(128)
 env={**os.environ,'PYTHONPATH':str(ROOT/'service'),'W11_SAVE_DATA':str(data),'W11_SAVE_FD':str(l.fileno())}
 log.write(f'--- api start {tag} pid ---\n');log.flush()
 p=subprocess.Popen([PY,'-B',str(HERE/'server.py')],env=env,pass_fds=(l.fileno(),),stdout=log,stderr=subprocess.STDOUT);l.close();procs['api']=p
 wait(apiport,'/api/v1/health',p);receipt['phases'][tag]={'apiPid':p.pid}
def stop(name):
 p=procs.pop(name,None)
 if p and p.poll() is None:
  p.terminate()
  try:p.wait(10)
  except subprocess.TimeoutExpired:p.kill();p.wait()
 return p.returncode if p else None
def wait(port,path,p):
 for _ in range(600):
  if p.poll() is not None:raise RuntimeError(f'owned process exited {p.returncode}')
  try:urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',timeout=1);return
  except Exception:time.sleep(.1)
 raise RuntimeError('owned server unavailable')
code=1
try:
 start_api('first')
 procs['web']=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',str(webport),'--strictPort'],cwd=ROOT/'web',env={**os.environ,'MCIS_API':f'http://127.0.0.1:{apiport}'},stdout=log,stderr=subprocess.STDOUT)
 wait(webport,'/',procs['web'])
 origin=f'http://127.0.0.1:{webport}';url=origin+'/#/ecfc?case='+CID
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=CHROME,headless=True,chromium_sandbox=True);receipt['browserVersion']=browser.version
  def context():
   c=browser.new_context(viewport={'width':1280,'height':900})
   c.add_init_script("localStorage.setItem('mcis.role','LeadInvestigator');localStorage.setItem('mcis.operator','Synthetic W11 Save')")
   def guard(r):
    if r.request.url.startswith(origin+'/'):r.continue_()
    else:receipt['blockedExternal'].append(r.request.url);r.abort()
   c.route('**/*',guard)
   pg=c.new_page();pg.set_default_timeout(30000)
   pg.on('console',lambda m:receipt['console'].append(f'{m.type}: {m.text}'));pg.on('pageerror',lambda e:receipt['pageerrors'].append(str(e)))
   return c,pg
  api=[]
  def track(pg):pg.on('response',lambda r:api.append({'method':r.request.method,'path':r.url.split(origin)[-1],'status':r.status}) if '/api/v1/cases/' in r.url else None)
  ctx,page=context();track(page)
  page.goto(url);scope=page.get_by_label('调查范围 / 假设说明',exact=True);scope.wait_for()
  check(counts()==[0,0,0],'empty before any action')
  scope.fill('W11 fictional save/reopen hypothesis')
  page.get_by_role('button',name='添加人工节点',exact=True).click();page.get_by_label('节点描述 1',exact=True).fill('Fictional vessel alters course')
  page.get_by_role('button',name='添加人工节点',exact=True).click();page.get_by_label('节点类型 2',exact=True).select_option('Condition');page.get_by_label('节点描述 2',exact=True).fill('Fictional restricted visibility')
  page.get_by_role('button',name='添加人工连线',exact=True).click();page.get_by_label('起点 ID 1',exact=True).fill('N2');page.get_by_label('终点 ID 1',exact=True).fill('N1')
  page.locator('.ecfc-source input').check();page.get_by_label('标记为核心事故候选',exact=False).first.check()
  page.get_by_role('button',name='预览结构与方法提示（不保存）',exact=True).click();page.get_by_role('heading',name='结构已接受 · 方法提示单列',exact=True).wait_for()
  check(counts()==[0,0,0],'preview through real CLI is zero-write')
  page.screenshot(path=str(OUT/'01-preview-zero-write.png'),full_page=True)
  page.get_by_label('我了解保存后整个案件暂不能导出',exact=False).check()
  page.get_by_role('button',name='保存 ECFC 人工草稿',exact=True).click();page.get_by_text('此请求的保存回执已核验。',exact=False).wait_for()
  check(counts()==[1,1,1],'one explicit save commits exactly once')
  page.screenshot(path=str(OUT/'02-saved-receipt.png'),full_page=True)
  def server_draft(pg):return pg.evaluate("async(u)=>{const r=await fetch(u,{headers:{'X-MCIS-Role':'LeadInvestigator','X-MCIS-Operator':'Synthetic W11 Save'},cache:'no-store'});return {status:r.status,body:await r.json()}}",f'/api/v1/cases/{CID}/ecfc/draft')
  before=server_draft(page);receipt['savedEnvelope']=before
  check(before['status']==200 and before['body']['document']['revision']==1,'saved revision 1 readable')
  ctx.close()
  receipt['phases']['first']['apiExit']=stop('api')
  dbsha=hashlib.sha256((data/'mcis.db').read_bytes()).hexdigest();receipt['dbSha256BetweenRestarts']=dbsha
  start_api('restart')
  check(receipt['phases']['restart']['apiPid']!=receipt['phases']['first']['apiPid'],'service process restarted')
  ctx,page=context();track(page)
  page.goto(url);page.get_by_label('调查范围 / 假设说明',exact=True).wait_for();page.get_by_text('已读取保存版本 1。',exact=False).wait_for()
  after=server_draft(page);receipt['reopenedEnvelope']=after
  d0,d1=before['body']['document'],after['body']['document']
  check(d1['revision']==d0['revision']==1 and d1['digest']==d0['digest'],'same revision and digest after restart')
  check(d1['draft']==d0['draft'],'same draft (scope, nodes, edges, times, evidence) after restart')
  check(d1['caseId']==CID and d1['sources']==d0['sources'],'same case and sources')
  check(page.get_by_label('调查范围 / 假设说明',exact=True).input_value()=='W11 fictional save/reopen hypothesis','page shows saved scope')
  try:page.get_by_label('节点描述 1',exact=False).wait_for(timeout=5000)
  except Exception:
   page.screenshot(path=str(OUT/'99-failure.png'),full_page=True);receipt['failureLabels']=page.eval_on_selector_all('label','ls=>ls.map(l=>l.textContent.slice(0,60))')[:80];raise
  # textarea content is part of its wrapping label's accessible name, so match by prefix
  check(page.get_by_label('节点描述 1',exact=False).input_value()=='Fictional vessel alters course' and page.get_by_label('节点描述 2',exact=False).input_value()=='Fictional restricted visibility','page shows saved nodes')
  check(page.get_by_label('起点 ID 1',exact=True).input_value()=='N2' and page.get_by_label('终点 ID 1',exact=True).input_value()=='N1','page shows saved edge endpoints')
  page.get_by_role('button',name='预览结构与方法提示（不保存）',exact=True).click();page.get_by_role('heading',name='结构已接受 · 方法提示单列',exact=True).wait_for()
  titles=page.eval_on_selector_all('svg[aria-label="人工 ECFC 假设示意图"] title','ts=>ts.map(t=>t.textContent)');receipt['graphTitlesAfterRestart']=titles
  check(len([t for t in titles if t.startswith('N1') or t.startswith('N2')])==2 and any(t.startswith('e1') or 'N2 → N1' in t for t in titles),'same graph nodes and edge rendered after restart')
  check(counts()==[1,1,1],'re-preview after restart is zero-write')
  page.get_by_role('button',name='读取审计摘要',exact=True).click();page.get_by_text('版本 1 ·',exact=False).wait_for()
  check(page.get_by_text('版本 1 ·',exact=False).count()==1 and page.get_by_text('版本 2 ·',exact=False).count()==0,'audit shows exactly one save')
  page.screenshot(path=str(OUT/'03-reopened-after-restart.png'),full_page=True)
  with sqlite3.connect(data/'mcis.db') as s:
   receipt['auditRows']=[dict(zip([c[0] for c in s.execute('select * from ecfc_draft_audit').description],r)) for r in s.execute('select * from ecfc_draft_audit')]
  check(len(receipt['auditRows'])==1,'database audit has exactly one row')
  ctx.close();browser.close()
 receipt['apiResponses']=api
 receipt['saveCalls']=len([a for a in api if a['method']=='POST' and a['path'].endswith('/save')])
 check(receipt['saveCalls']==1,'exactly one save POST across both phases')
 check(not receipt['pageerrors'] and not receipt['blockedExternal'],'no page errors, no external requests')
 receipt['finalCounts']=counts();code=0
except Exception as e:
 receipt['exception']=repr(e);code=1
 try:
  page.screenshot(path=str(OUT/'99-failure.png'),full_page=True);receipt['failureLabels']=page.eval_on_selector_all('label','ls=>ls.map(l=>l.textContent.slice(0,60))')[:60]
 except Exception as e2:receipt['failureCapture']=repr(e2)
finally:
 receipt['phases'].setdefault('restart',{})['apiExit']=stop('api');receipt['webExit']=stop('web');log.close()
 receipt['exitCode']=code
 receipt['files']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(OUT.glob('*.png'))}
 (OUT/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=1,default=str))
 print(json.dumps({'checks':receipt['checks'],'exception':receipt.get('exception'),'exit':code},ensure_ascii=False))
sys.exit(code)
