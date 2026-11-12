"""New ECFC UI API-double checks. Not a real-service or professional acceptance claim."""
import copy,json,os,signal,subprocess,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
PROFILE='MCIS-ECFC-DRAFT-1'
HEADERS={'Cache-Control':'no-store','Content-Type':'application/json'}
server=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15873','--strictPort'],cwd=ROOT/'web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
try:
 for _ in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:15873',timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1280,'height':900});page.set_default_timeout(8000)
  page.add_init_script("if(!localStorage.getItem('mcis.role')){localStorage.setItem('mcis.role','LeadInvestigator');localStorage.setItem('mcis.operator','Synthetic UI')}")
  mode={'save':'ok','audit':'ok','get':'ok'};docs={};receipts={};events={};posts=[];held=[];errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  def validation(d):
   by={n['id']:n for n in d['nodes']}
   return {'coreVersion':'mcis-ecfc-draft/1','nodes':[{**n,'isPresumptive':True} for n in d['nodes']],'edges':[{**e,'kind':'Sequence' if by[e['from']]['kind']=='Event' else 'Influence','bold':by[e['from']]['kind']=='Event' and by[e['from']]['lane']==0 and by[e['to']]['lane']==0} for e in d['edges']],'issues':[{'code':'ECFC-E06','isError':True,'message':'Synthetic method hint, not a fact','nodeId':None,'edgeId':None}]}
  def envelope(cid,doc):return {'profile':PROFILE,'caseId':cid,'document':doc,'sourceStatus':'unchanged' if doc else 'none','persisted':bool(doc),'identityMode':'local-role-header'}
  def fulfill(r,value,status=200):r.fulfill(status=status,body=json.dumps(value),headers=HEADERS)
  def route(r):
   cid=r.request.url.split('/cases/')[1].split('/')[0];action=r.request.url.rsplit('/',1)[1]
   if r.request.method=='GET' and mode['get']=='403':fulfill(r,{'code':'FORBIDDEN'},403);return
   if action=='context':fulfill(r,{'profile':PROFILE,'caseId':cid,'sources':[],'writeAllowed':True,'identityMode':'local-role-header','sourceBinding':'registered-metadata-only','archiveSupported':False})
   elif action=='draft':fulfill(r,envelope(cid,docs.get(cid)))
   elif action=='audit':
    if mode['audit']=='403':fulfill(r,{},403)
    else:fulfill(r,{'profile':PROFILE,'caseId':cid,'events':list(reversed(events.get(cid,[])))})
   else:
    body=r.request.post_data_json
    if action=='preview':fulfill(r,{'profile':PROFILE,'caseId':cid,'draft':body['draft'],'validation':validation(body['draft']),'persisted':False});return
    assert body['acknowledgeArchiveLimitation'] is True;posts.append(copy.deepcopy(body));rid=body['requestId']
    if rid not in receipts:
     rev=docs.get(cid,{}).get('revision',0)+1;doc={'caseId':cid,'revision':rev,'digest':str(rev%10)*64,'draft':body['draft'],'sources':body['expectedSources'],'validation':validation(body['draft']),'status':'Draft','strength':'ToBeVerified','origin':'Investigator','savedBy':urllib.parse.unquote(r.request.headers['x-mcis-operator']),'savedRole':r.request.headers['x-mcis-role'],'savedUtc':'2026-11-12T13:00:00Z'};docs[cid]=doc;receipts[rid]=envelope(cid,doc);events.setdefault(cid,[]).append({'revision':rev,'utc':doc['savedUtc'],'operator':doc['savedBy'],'role':doc['savedRole'],'action':'ecfc.draft.save','requestId':rid,'beforeDigest':body['expectedDigest'],'afterDigest':doc['digest'],'prevHash':'0'*64,'hash':'a'*64})
    if mode['save']=='hold':held.append((r,copy.deepcopy(receipts[rid])))
    elif mode['save']=='503':fulfill(r,{},503)
    elif mode['save']=='bad':fulfill(r,{**receipts[rid],'caseId':'WRONG'})
    elif mode['save']=='403':fulfill(r,{},403)
    else:fulfill(r,receipts[rid])
  page.route('**/api/v1/cases/**/ecfc/*',route)
  def fresh():
   mode.update(save='ok',audit='ok',get='ok');docs.clear();events.clear();receipts.clear();posts.clear();page.goto('http://127.0.0.1:15873/tests/ecfc-harness.html');page.evaluate("sessionStorage.clear();localStorage.setItem('mcis.role','LeadInvestigator');localStorage.setItem('mcis.operator','Synthetic UI')");page.reload();page.get_by_label('调查范围 / 假设说明',exact=True).wait_for()
  def fill():page.get_by_label('调查范围 / 假设说明',exact=True).fill('Synthetic UI hypothesis')
  def acknowledge():page.get_by_label('我了解保存后整个案件暂不能导出',exact=False).check()
  def save():page.get_by_role('button',name='保存 ECFC 人工草稿',exact=True).click()
  fresh();fill();assert page.get_by_role('button',name='保存 ECFC 人工草稿',exact=True).is_disabled();page.get_by_role('button',name='预览结构与方法提示（不保存）',exact=True).click();page.get_by_text('原核心 error 提示',exact=False).wait_for();assert not posts
  acknowledge();page.get_by_role('button',name='保存 ECFC 人工草稿',exact=True).evaluate('(b)=>{b.click();b.click()}');page.get_by_text('此请求的保存回执已核验',exact=False).wait_for();assert len(posts)==1 and page.evaluate('sessionStorage.length')==0
  page.get_by_role('button',name='重新打开服务端草稿（放弃未保存修改）',exact=True).click();page.get_by_text('已读取保存版本 1',exact=False).wait_for();assert page.get_by_label('调查范围 / 假设说明',exact=True).input_value()=='Synthetic UI hypothesis'
  page.get_by_role('button',name='添加人工节点',exact=True).click();page.get_by_label('节点描述 1',exact=True).fill('Synthetic vessel turns');assert page.get_by_label('相对时间秒 1（留空未知）',exact=True).input_value()=='';acknowledge();save();page.get_by_text('此请求的保存回执已核验',exact=False).wait_for();assert posts[-1]['draft']['nodes'][0]['timeSeconds'] is None
  # Real rendered semantics, full graph, desktop and narrow-screen layout (API doubles).
  fresh();fill();page.get_by_role('button',name='添加人工节点',exact=True).click();page.get_by_label('节点描述 1',exact=True).fill('Synthetic vessel turns');page.get_by_role('button',name='添加人工节点',exact=True).click();page.get_by_label('节点类型 2',exact=True).select_option('Condition');page.get_by_label('节点描述 2',exact=True).fill('Synthetic fog');page.get_by_label('泳道 2（0 为主序列）',exact=True).fill('1');page.get_by_role('button',name='添加人工连线',exact=True).click();page.get_by_label('起点 ID 1',exact=True).fill('N2');page.get_by_label('终点 ID 1',exact=True).fill('N1');page.get_by_role('button',name='预览结构与方法提示（不保存）',exact=True).click();page.get_by_role('img',name='人工 ECFC 假设示意图',exact=True).wait_for();assert page.locator('svg ellipse').count()==1 and page.locator('svg rect').count()==1 and page.locator('svg line').get_attribute('stroke-dasharray')=='7 5';page.screenshot(path='/tmp/ecfc-ui-desktop.png',full_page=True);page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1');page.screenshot(path='/tmp/ecfc-ui-mobile.png',full_page=True);page.set_viewport_size({'width':1280,'height':900})
  # Maximum 40-node single-lane graph remains 1:1 readable and horizontally scrollable.
  maximum={'scope':'Synthetic maximum graph','nodes':[{'id':f'M{i}','kind':'Event','text':f'Synthetic event {i}','timeSeconds':None,'lane':0,'isPrimaryIncident':i==0,'evidenceIds':[]} for i in range(40)],'edges':[]}
  docs['SYNTHETIC-A']={'caseId':'SYNTHETIC-A','revision':1,'digest':'1'*64,'draft':maximum,'sources':[],'validation':validation(maximum),'status':'Draft','strength':'ToBeVerified','origin':'Investigator','savedBy':'Synthetic UI','savedRole':'LeadInvestigator','savedUtc':'2026-11-12T13:00:00Z'}
  page.get_by_role('button',name='重新打开服务端草稿（放弃未保存修改）',exact=True).click();page.locator('svg rect').nth(39).wait_for();graph=page.locator('.ecfc-graph');svg=graph.locator('svg');assert svg.evaluate('(s)=>s.getBoundingClientRect().width')>=11650;assert svg.evaluate('(s)=>s.getScreenCTM().a')>=.99;assert graph.evaluate('(g)=>g.scrollWidth>g.clientWidth');graph.screenshot(path='/tmp/ecfc-ui-maximum-left.png');graph.evaluate('(g)=>g.scrollLeft=g.scrollWidth');assert graph.evaluate('(g)=>{const n=g.querySelectorAll("svg rect")[39].getBoundingClientRect(),b=g.getBoundingClientRect();return n.left>=b.left&&n.right<=b.right}');graph.screenshot(path='/tmp/ecfc-ui-maximum-right.png');assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
  # Save commits but response is lost. Same-body retry must be identical.
  fresh();fill();acknowledge();mode['save']='503';save();page.get_by_role('heading',name='保存结果待核对',exact=True).wait_for();assert page.get_by_label('调查范围 / 假设说明',exact=True).is_disabled();assert 'Synthetic UI hypothesis' not in page.evaluate('JSON.stringify(sessionStorage)');first=copy.deepcopy(posts[-1]);mode['save']='ok';page.get_by_role('button',name='重试同一保存请求（原内容和请求 ID）',exact=True).click();page.get_by_text('此请求的保存回执已核验',exact=False).wait_for();assert posts[-1]==first and len(events['SYNTHETIC-A'])==1
  # Reload loses body, retains lock, no new POST until explicit read/abandon/fresh reopen.
  fresh();fill();acknowledge();mode['save']='bad';save();page.get_by_role('heading',name='保存结果待核对',exact=True).wait_for();n=len(posts);page.reload();page.get_by_text('原请求正文已不在内存',exact=False).wait_for();assert len(posts)==n and page.get_by_role('button',name='保存 ECFC 人工草稿',exact=True).is_disabled();page.get_by_role('button',name='读取最新草稿及审计以核对待核请求',exact=True).click();page.get_by_label('我已核对最新草稿及审计',exact=False).check();page.get_by_role('button',name='明确放弃本地等待并重新读取最新草稿',exact=True).click();page.get_by_text('已读取保存版本 1',exact=False).wait_for();assert len(posts)==n and page.evaluate('sessionStorage.length')==0
  # Late committed save after case change never displays old body.
  fresh();fill();acknowledge();mode['save']='hold';save()
  for _ in range(100):
   if held:break
   page.wait_for_timeout(10)
  assert held;page.get_by_role('button',name='Switch case',exact=True).click();page.get_by_text('案件 SYNTHETIC-B',exact=False).wait_for();r,value=held.pop();fulfill(r,value);page.wait_for_timeout(100);assert 'Synthetic UI hypothesis' not in page.locator('body').inner_text();assert page.evaluate('sessionStorage.length')==1
  # Late committed save after identity change and close does not populate a new session.
  for button in ['Switch identity','Close or reopen']:
   fresh();fill();acknowledge();mode['save']='hold';save()
   for _ in range(100):
    if held:break
    page.wait_for_timeout(10)
   assert held;page.get_by_role('button',name=button,exact=True).click();r,value=held.pop();fulfill(r,value);page.wait_for_timeout(100);assert page.get_by_text('此请求的保存回执已核验',exact=False).count()==0 and page.evaluate('sessionStorage.length')==1
  # Permission rejection hides already-read graph and audit rather than leaving stale body.
  fresh();fill();acknowledge();save();page.get_by_text('此请求的保存回执已核验',exact=False).wait_for();mode['audit']='403';page.get_by_role('button',name='读取审计摘要',exact=True).click();page.get_by_text('当前原文权限已被拒绝',exact=False).wait_for();assert page.get_by_label('调查范围 / 假设说明',exact=True).count()==0
  # Storage write failure prevents POST, never silently proceeds without a lock.
  fresh();fill();acknowledge();page.evaluate("()=>{Storage.prototype.setItem=function(){throw Error('blocked')}}");save();page.get_by_text('未发送新保存',exact=False).wait_for();assert len(posts)==0
  assert not errors,errors
  browser.close();print('ECFC new browser API-double checks passed: acknowledgement, preview, save/reopen/edit, double click, exact retry, metadata-only reload/abandon, late-case discard, permission hide, storage refusal.')
finally:
 os.killpg(server.pid,signal.SIGTERM);server.wait()
