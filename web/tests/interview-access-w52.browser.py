"""Synthetic API doubles only. Not backend permission acceptance."""
import subprocess,time,urllib.request,os,signal
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
server=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15852','--strictPort'],cwd=ROOT/'web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
case='SYNTHETIC';rec='IR-01'
record=dict(recordId=rec,name='synthetic',role='synthetic',affiliation='synthetic',startUtc='2026-11-12T00:00:00Z',durationMin=None,signed=False,statementCount=0,confirmedContradictions=0,pendingCount=0,uncheckedCount=0,staleCount=0,status='NotChecked',label='未比对')
roster=dict(caseId=case,fictional=True,disclaimer='synthetic only',records=[record,{**record,'recordId':'IR-02','role':'second-record'}])
segment=lambda text:dict(start=0,length=len(text),text=text,kinds=[],statementIds=[],contradiction='None')
detail=dict(caseId=case,recordId=rec,fictional=True,disclaimer='synthetic',record={**record,'interviewee':{'name':'synthetic','role':'synthetic','affiliation':'synthetic'}},turns=[dict(round=1,question='SECRET-QUESTION',answer='SECRET-ANSWER',utc=None,questionSegments=[segment('SECRET-QUESTION')],answerSegments=[segment('SECRET-ANSWER')])],rows=[],summary=dict(statementCount=0,contradictionCount=0,confirmedContradictionCount=0,pendingCount=0,uncheckedCount=0,staleCount=0,headerText='synthetic'),chart={'points':[],'axisStartUtc':None,'axisEndUtc':None},superseded=[],highlightSuppressed=False,redaction=[])
detail['rows']=[dict(statementId='S1',citation='synthetic',summary='synthetic claim',quote='',kind='Time',reviewStatus='Draft',statementRevision=1,statementMissing=False,outcome='Consistent',state='PendingConfirmation',dataDisplay='synthetic',delta=0,deltaUnit='s',rule='synthetic',statementVersion=1,isStale=False,isContradiction=False,decidedBy=None,note='',supersededCount=0)]
try:
 for _ in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:15852',timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox']);p=b.new_page();p.set_default_timeout(8000)
  mode={'queue403':False,'hold':False,'draft':False};held=[];requests=[]
  def route(r):
   u=r.request.url;requests.append(u)
   if r.request.method=='POST' and ('/interview-compare/' in u or '/agents/' in u):r.fulfill(status=403,body='secret policy',content_type='text/html');return
   if '/interview-compare' in u and r.request.headers.get('x-mcis-role')!='LeadInvestigator':r.fulfill(status=403,json={'code':'FORBIDDEN','message':'secret policy must not display'});return
   if u.endswith('/interview-compare'):r.fulfill(json=roster)
   elif '/interview-compare/IR-' in u:
    if mode['hold']:held.append(r)
    else:
     rid=u.rsplit('/',1)[1];r.fulfill(json={**detail,'recordId':rid,'record':{**detail['record'],'recordId':rid}})
   elif u.endswith('/agents'):r.fulfill(json=[{'agent':a,'name':a,'model':'synthetic','status':'configured'} for a in ['ships','timeline','environment','people_ops','causes_ecfc','aggregate']])
   elif u.endswith('/agents/drafts'):r.fulfill(status=403 if mode['queue403'] else 200,json={'code':'FORBIDDEN','message':'secret policy'} if mode['queue403'] else ([dict(caseId=case,draftId='AD-101',agent='people_ops',kind='statement_extraction',targetEntityType='interviewStatements',targetEntityId=rec,payload=dict(recordId=rec,sourceDigest='a'*64,statements=[dict(kind='Observation',subject='vessel.lookout',summary='SYNTHETIC-DRAFT',claim={'valueType':'Occurrence','occurred':True},round=1,field='Answer',quote='SECRET-ANSWER')]),citations=[dict(recordId=rec,round=1,quote='SECRET-ANSWER')],model='synthetic',status='PendingReview')] if mode['draft'] else []))
   else:r.fulfill(status=404,json={})
  p.route('**/api/v1/**',route);p.goto('http://127.0.0.1:15852/#/interview?case='+case)
  p.get_by_text('当前身份无权访问笔录原文。受保护内容已清空',exact=False).wait_for();assert 'secret policy' not in p.locator('body').inner_text();assert not any('/agents/drafts' in u for u in requests)
  p.evaluate("async()=>{const a=await import('/src/api.ts');a.setIdentity('LeadInvestigator','test')}")
  p.get_by_text('SECRET-ANSWER',exact=True).wait_for()
  p.get_by_test_id('btn-confirm').click()
  p.get_by_text('当前身份无权访问笔录原文。受保护内容已清空',exact=False).wait_for();assert 'SECRET-ANSWER' not in p.locator('body').inner_text()
  p.get_by_role('button',name='重新读取笔录权限',exact=True).click();p.get_by_text('SECRET-ANSWER',exact=True).wait_for()
  p.get_by_role('button',name='提取当前笔录为待审草稿',exact=True).click()
  p.get_by_text('当前身份无权访问笔录原文。受保护内容已清空',exact=False).wait_for();assert 'SECRET-ANSWER' not in p.locator('body').inner_text()
  mode['draft']=True;p.get_by_role('button',name='重新读取笔录权限',exact=True).click()
  p.get_by_text('SYNTHETIC-DRAFT',exact=True).wait_for();p.get_by_role('checkbox').check()
  p.get_by_role('button',name='确认以上陈述并写回',exact=True).click()
  p.get_by_text('当前身份无权访问笔录原文。受保护内容已清空',exact=False).wait_for();assert 'SYNTHETIC-DRAFT' not in p.locator('body').inner_text()
  mode['draft']=False;p.get_by_role('button',name='重新读取笔录权限',exact=True).click();p.get_by_text('SECRET-ANSWER',exact=True).wait_for()
  mode['hold']=True
  p.locator('[data-record="IR-02"]').click()
  for _ in range(50):
   p.wait_for_timeout(20)
   if held:break
  assert held and 'SECRET-ANSWER' not in p.locator('body').inner_text()
  mode['hold']=False;p.locator('[data-record="IR-01"]').click();p.get_by_text('SECRET-ANSWER',exact=True).wait_for()
  late=held.pop();late.fulfill(json={**detail,'recordId':'IR-02','record':{**detail['record'],'recordId':'IR-02'}})
  p.wait_for_timeout(100);assert p.locator('.ic-person.sel').get_attribute('data-record')=='IR-01'
  mode['hold']=True
  p.evaluate("async()=>{const a=await import('/src/api.ts');a.setIdentity('LeadInvestigator','new operator')}")
  for _ in range(50):
   p.wait_for_timeout(20)
   if held:break
  assert held and 'SECRET-ANSWER' not in p.locator('body').inner_text()
  p.evaluate("async()=>{const a=await import('/src/api.ts');a.setIdentity('Investigator','test')}")
  p.get_by_text('当前身份无权访问笔录原文。受保护内容已清空',exact=False).wait_for()
  held.pop().fulfill(json=detail);p.wait_for_timeout(100);assert 'SECRET-ANSWER' not in p.locator('body').inner_text()
  mode['hold']=False;mode['queue403']=True
  p.evaluate("async()=>{const a=await import('/src/api.ts');a.setIdentity('LeadInvestigator','test')}")
  p.get_by_text('当前身份无权访问笔录原文。受保护内容已清空',exact=False).wait_for();assert 'SECRET-ANSWER' not in p.locator('body').inner_text()
  for r in held:
   try:r.abort()
   except Exception:pass
  p.wait_for_timeout(100);p.unroute_all(behavior='ignoreErrors');b.close()
 print('W5.2a browser: raw/review/queue/extract/agent-review 403 (including HTML) clears protected content, no queue without raw access, record/identity clear and stale detail ignored (API doubles)')
finally:os.killpg(server.pid,signal.SIGTERM);server.wait()
