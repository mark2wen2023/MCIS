"""Synthetic API doubles, not backend acceptance."""
import subprocess,time,urllib.request,os,signal,json,copy
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
server=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15853','--strictPort'],cwd=ROOT/'web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
C='SYNTHETIC';P='MCIS-MANUAL-INTERVIEW-1';R='IR-01';A='a'*64;B='b'*64
try:
 for _ in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:15853',timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox']);p=b.new_page();p.set_default_timeout(8000)
  db={'doc':None,'digest':A};receipts={};writes=[];held=[];mode={'bad':False,'unknown':False,'404':False,'conflict':False,'hold':False}
  def env(rec):return dict(profile=P,caseId=C,receipt=rec,replayed=False,sourceBinding='none',currentDigest=db['digest'],identityMode='local-role-header')
  def route(r):
   u=r.request.url
   if '/manual-interviews' in u:
    if r.request.method=='POST':
     data=r.request.post_data_json;writes.append(copy.deepcopy(data));rid=data['requestId'];append=u.endswith('/turns')
     if mode['conflict']:r.fulfill(status=409,json={'code':'INTERVIEW_VERSION_CONFLICT'});return
     if rid not in receipts:
      if not append:db['doc']=dict(caseId=C,recordId=R,interviewee=data['interviewee'],startUtc=data['startUtc'],signed=False,turns=[],statements=[],crossChecks=[])
      else:db['doc']['turns'].append(dict(round=len(db['doc']['turns'])+1,question=data['question'],answer=data['answer'],utc=data['utc']));db['digest']=B
      receipts[rid]=dict(requestId=rid,operation='append-turn' if append else 'create',recordId=R,beforeDigest=data.get('expectedDigest'),afterDigest=db['digest'],turnRound=len(db['doc']['turns']) if append else None,appliedUtc='2026-11-12T00:00:00Z')
     if mode['hold']:held.append((r,env(receipts[rid])));return
     if mode['unknown']:r.abort('failed');return
     if mode['bad']=='binding':r.fulfill(status=201,json={**env(receipts[rid]),'caseId':'OTHER'});return
     if mode['bad']=='html4xx':r.fulfill(status=422,body='unknown intermediary rejection',content_type='text/html');return
     if mode['bad']:r.fulfill(status=201,body='bad json',content_type='application/json');return
     r.fulfill(status=201,json=env(receipts[rid]));return
    if '/requests/' in u:
     rid=u.rsplit('/',1)[1]
     if mode['404'] or rid not in receipts:r.fulfill(status=404,json={'code':'INTERVIEW_REQUEST_NOT_FOUND'})
     else:r.fulfill(json={**env(receipts[rid]),'replayed':True})
     return
    if db['doc']:r.fulfill(json=dict(profile=P,caseId=C,record=db['doc'],documentDigest=db['digest'],sourceBinding='none',signed=False,identityMode='local-role-header'))
    else:r.fulfill(status=404,json={'code':'NOT_FOUND'})
   elif u.endswith('/interview-compare'):
    entries=[] if not db['doc'] else [dict(recordId=R,name='Synthetic',role='role',affiliation='unit',startUtc='2026-11-12T00:00:00Z',durationMin=None,signed=False,statementCount=0,confirmedContradictions=0,pendingCount=0,uncheckedCount=0,staleCount=0,status='NotChecked',label='unverified')]
    r.fulfill(json=dict(caseId=C,fictional=True,disclaimer='synthetic only',records=entries))
   elif '/interview-compare/' in u:r.fulfill(status=404,json={'code':'TEST_ONLY_NO_COMPARE'})
   elif u.endswith('/evidence'):r.fulfill(json=[])
   else:r.fulfill(status=404,json={})
  p.route('**/api/v1/**',route);p.add_init_script("localStorage.setItem('mcis.role','LeadInvestigator')");p.goto('http://127.0.0.1:15853/#/interview?case='+C)
  panel=p.get_by_role('region',name='人工笔录录入');panel.wait_for()
  assert '整个 .mcase 案件包' in panel.inner_text();assert panel.get_by_label('真实开始时间 UTC（必填，秒Z）',exact=True).input_value()==''
  for label,value in [('受询问人标识（必填）','person'),('受询问人姓名（必填）','Synthetic Name'),('职务（必填）','role'),('所属单位（必填）','unit'),('真实开始时间 UTC（必填，秒Z）','2026-11-12T00:00:00Z')]:panel.get_by_label(label,exact=True).fill(value)
  assert panel.get_by_role('button',name='保存空白人工笔录',exact=True).is_disabled()
  panel.get_by_role('checkbox').check();mode['bad']=True;panel.get_by_role('button',name='保存空白人工笔录',exact=True).evaluate('(el)=>{el.click();el.click()}')
  panel.get_by_text('存在结果未确认的',exact=False).wait_for();assert len(writes)==1 and writes[0]['backupAcknowledged'] is True
  mode['404']=True;panel.get_by_role('button',name='只读查询原请求回执',exact=True).click();panel.get_by_text('尚未查到原请求回执',exact=False).wait_for();assert len(writes)==1
  mode['404']=False;mode['bad']=False;panel.get_by_role('button',name='同ID原样重试',exact=True).click();panel.get_by_text('已核验此请求的保存回执',exact=True).wait_for();assert writes[0]==writes[1]
  panel.get_by_role('button',name='重新打开服务器当前笔录',exact=True).click();p.wait_for_url('**record=IR-01');panel.get_by_text('服务器当前原文 · IR-01',exact=True).wait_for()
  for label,value in [('问题原文（必填）',' Q exact\n'),('回答原文（必填）',' A exact\n')]:panel.get_by_label(label,exact=True).fill(value)
  panel.get_by_role('checkbox').check();mode['conflict']=True;panel.get_by_role('button',name='保存追加问答',exact=True).click();panel.get_by_text('INTERVIEW_VERSION_CONFLICT',exact=False).wait_for()
  assert panel.get_by_label('回答原文（必填）',exact=True).input_value()==' A exact\n';assert panel.get_by_role('button',name='保存追加问答',exact=True).is_disabled()
  mode['conflict']=False;panel.get_by_role('button',name='只读刷新当前原文',exact=True).click();panel.get_by_text('服务器当前原文 · IR-01',exact=True).wait_for()
  mode['unknown']=True;panel.get_by_role('button',name='保存追加问答',exact=True).click();panel.get_by_text('存在结果未确认的',exact=False).wait_for()
  last=copy.deepcopy(writes[-1]);assert last['expectedDigest']==A
  stored=p.evaluate("sessionStorage.getItem('mcis.manual-interview.pending.v1')");assert 'exact' not in stored and 'expectedDigest' not in stored
  mode['unknown']=False;p.reload();panel.get_by_text('原请求正文已不在内存',exact=False).wait_for();assert panel.get_by_role('button',name='同ID原样重试',exact=True).is_disabled()
  before=len(writes);mode['404']=True;panel.get_by_role('button',name='只读查询原请求回执',exact=True).click();panel.get_by_text('尚未查到原请求回执',exact=False).wait_for();assert len(writes)==before
  mode['404']=False;panel.get_by_role('button',name='只读查询原请求回执',exact=True).click();panel.get_by_text('已核验此请求的保存回执',exact=True).wait_for()
  panel.get_by_role('button',name='重新打开服务器当前笔录',exact=True).click();panel.get_by_text('服务器当前原文 · IR-01',exact=True).wait_for();assert 'Q exact' in panel.inner_text() and 'A exact' in panel.inner_text()
  assert len(writes)==before
  panel.get_by_label('问题原文（必填）',exact=True).fill('next Q');panel.get_by_label('回答原文（必填）',exact=True).fill('next A');panel.get_by_role('checkbox').check()
  panel.get_by_role('button',name='保存追加问答',exact=True).evaluate('(el)=>{el.click();el.click()}')
  panel.get_by_text('已核验此请求的保存回执',exact=True).wait_for();assert len(writes)==before+1 and writes[-1]['requestId']!=last['requestId'] and writes[-1]['expectedDigest']==B
  assert panel.get_by_label('回答原文（必填）',exact=True).input_value()==''
  for failure in ['binding','html4xx']:
   panel.get_by_role('button',name='重新打开服务器当前笔录',exact=True).click();panel.get_by_text('服务器当前原文 · IR-01',exact=True).wait_for()
   panel.get_by_label('问题原文（必填）',exact=True).fill(' Q '+failure);panel.get_by_label('回答原文（必填）',exact=True).fill(' A '+failure);panel.get_by_role('checkbox').check()
   mode['bad']=failure;panel.get_by_role('button',name='保存追加问答',exact=True).click();panel.get_by_text('存在结果未确认的',exact=False).wait_for();assert panel.get_by_label('回答原文（必填）',exact=True).input_value()==' A '+failure
   mode['bad']=False;panel.get_by_role('button',name='只读查询原请求回执',exact=True).click();panel.get_by_text('已核验此请求的保存回执',exact=True).wait_for();assert panel.get_by_label('回答原文（必填）',exact=True).input_value()==''
  panel.get_by_role('button',name='新建空白人工笔录',exact=True).click()
  assert panel.get_by_label('受询问人姓名（必填）',exact=True).input_value()=='' and panel.get_by_label('真实开始时间 UTC（必填，秒Z）',exact=True).input_value()==''
  # Dispatched write cannot be cancelled: late results must not affect another identity/case.
  def fill_new():
   panel.get_by_role('button',name='新建空白人工笔录',exact=True).click()
   for label,value in [('受询问人标识（必填）','person'),('受询问人姓名（必填）','Sensitive Manual Name'),('职务（必填）','role'),('所属单位（必填）','unit'),('真实开始时间 UTC（必填，秒Z）','2026-11-12T00:00:00Z')]:panel.get_by_label(label,exact=True).fill(value)
   panel.get_by_role('checkbox').check()
  fill_new();mode['hold']=True;panel.get_by_role('button',name='保存空白人工笔录',exact=True).click()
  for _ in range(50):
   p.wait_for_timeout(20)
   if held:break
  assert held
  p.evaluate("async()=>{const a=await import('/src/api.ts');a.setIdentity('LeadInvestigator','Different Operator')}")
  panel.get_by_text('原请求正文已不在内存',exact=False).wait_for();assert panel.get_by_role('button',name='同ID原样重试',exact=True).is_disabled()
  req,value=held.pop();req.fulfill(status=201,json=value);p.wait_for_timeout(100);assert panel.get_by_text('已核验此请求的保存回执',exact=True).count()==0
  assert p.evaluate("JSON.parse(sessionStorage.getItem('mcis.manual-interview.pending.v1')).length")==1
  p.evaluate("async()=>{const a=await import('/src/api.ts');a.setIdentity('LeadInvestigator','调查员 A')}");panel.get_by_text('原请求正文已不在内存',exact=False).wait_for()
  mode['hold']=False;panel.get_by_role('button',name='只读查询原请求回执',exact=True).click();panel.get_by_text('已核验此请求的保存回执',exact=True).wait_for()
  fill_new();mode['hold']=True;panel.get_by_role('button',name='保存空白人工笔录',exact=True).click()
  for _ in range(50):
   p.wait_for_timeout(20)
   if held:break
  assert held
  p.evaluate("location.hash='#/interview?case=OTHER'");p.wait_for_timeout(100)
  req,value=held.pop();req.fulfill(status=201,json=value);p.wait_for_timeout(100)
  assert 'case=OTHER' in p.url and '已核验此请求的保存回执' not in p.locator('body').inner_text() and 'Sensitive Manual Name' not in p.locator('body').inner_text()
  p.unroute_all(behavior='ignoreErrors');b.close()
 print('W5.2b browser: backup ack, create bad JSON uncertainty,404lock,exact retry,URL reopen,append conflict retains input,unknown append hard reload metadata-only recovery,late dispatched write identity/case isolation passed (API doubles)')
finally:os.killpg(server.pid,signal.SIGTERM);server.wait()
