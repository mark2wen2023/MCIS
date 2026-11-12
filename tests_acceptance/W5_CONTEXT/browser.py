"""Independent Chromium QA: real localhost app/API plus explicitly labeled delayed/mismatched response injection."""
import asyncio,json,pathlib,traceback,uuid,urllib.parse
from playwright.async_api import async_playwright,expect
from fixtures import servers,request,case,record,getdoc,document,DEMO
OUT=pathlib.Path(__file__).parent/'artifacts';OUT.mkdir(exist_ok=True)
results=[]
async def run():
 with servers(web=True) as (api,web):
  for cid in [DEMO,'W5-BROWSER-A','W5-BROWSER-B']:
   case(api,cid,True)
   for rid in ['IR-01','IR-02','IR-03']:record(api,cid,rid)
  A,B='W5-BROWSER-A','W5-BROWSER-B'
  case(api,'W5-EMPTY',False)
  async with async_playwright() as pw:
   browser=await pw.chromium.launch(executable_path='/tmp/w8-headless/chrome-headless-shell-linux64/chrome-headless-shell',headless=True,args=['--no-sandbox'])
   context=await browser.new_context(viewport={'width':1440,'height':1000});page=await context.new_page()
   errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   posts=[];page.on('request',lambda r:posts.append((r.url,r.post_data_json)) if r.method=='POST' and '/interview-compare/' in r.url else None)
   async def nav(cid, fresh=False):
    if fresh:await page.goto(web+'/?run='+uuid.uuid4().hex+'#/interview?case='+urllib.parse.quote(cid,safe=''))
    else:await page.evaluate('(cid)=>location.hash="/interview?case="+encodeURIComponent(cid)',cid)
   async def ready(cid,rid='IR-01'):
    await expect(page.locator('[data-testid="ic-transcript"]')).to_contain_text(f'SYNTHETIC-PRIVATE-{cid}-{rid}')
   async def role(value):await page.locator('.role-select').select_option(value)
   async def check(name,fn):
    try:
     print('RUN',name,flush=True);await fn();results.append({'name':name,'result':'PASS'})
    except Exception as e:
     results.append({'name':name,'result':'FAIL','error':str(e)});traceback.print_exc()
     await page.screenshot(path=str(OUT/(name+'.png')),full_page=True)
    finally:
     await page.unroute_all(behavior='ignoreErrors')
     await page.evaluate('localStorage.setItem("mcis.role","Investigator")')
   async def ui_create_empty():
    await page.goto(web+'/?run='+uuid.uuid4().hex+'#/lobby')
    await page.get_by_role('button',name='＋ 新建案件').click()
    cid='W5-UI-CREATED'
    for label,val in [('案号',cid),('案件名称','独立 W5 新案'),('事故时间（UTC）','2026-11-12T08:30:00Z'),('经度（°）','10'),('纬度（°）','20'),('水域 / 地点','合成水域')]:await page.get_by_label(label,exact=False).fill(val)
    await page.get_by_label('事故类型',exact=False).select_option('Collision')
    await page.get_by_label('数据性质',exact=False).select_option('false')
    await page.get_by_role('button',name='创建案件',exact=True).click()
    await page.get_by_role('link',name='进入新案件 →').click()
    await page.locator('a.nav-item[href*="/interview"]').click()
    await expect(page.locator('[data-testid="ic-roster"]')).to_contain_text('当前案件暂无询问笔录')
    await expect(page.locator('.case-chip')).to_contain_text(cid)
    text=await page.locator('body').inner_text()
    assert not any(x in text for x in ['Lily','Mary','公开报告','人物均为虚构'])
    assert await page.locator('[data-testid="ic-actions"]').count()==0
    assert request(api,f'/cases/{cid}/interview-compare')[1]['records']==[]
    await page.screenshot(path=str(OUT/'new-case-empty.png'),full_page=True)
   await check('real-ui-create-to-interview-empty',ui_create_empty)
   async def defaults():
    await page.goto(web+'/?run='+uuid.uuid4().hex+'#/interview')
    await ready(DEMO,'IR-03')
    await expect(page.locator('.case-chip')).to_contain_text(DEMO)
    await nav(A);await ready(A)
    await expect(page.locator('[data-record="IR-01"]')).to_have_class('ic-person sel')
    await page.locator('a.nav-item[href*="/evidence"]').click()
    assert 'case='+A in page.url
    await page.locator('a.nav-item[href*="/interview"]').click();await ready(A)
    await page.screenshot(path=str(OUT/'active-case-loaded.png'),full_page=True)
   await check('demo-default-and-active-navigation',defaults)
   async def mutate(action,sid):
    cid='W5-UI-'+action;peer=cid+'-PEER'
    for c in [cid,peer]:case(api,c,True);record(api,c)
    before=getdoc(api,peer);await nav(cid,True);await ready(cid)
    await page.locator('tr[data-sid="'+sid+'"]').click()
    await page.get_by_placeholder('理由 / 备注（驳回、修改、重新比对必填）').fill('独立验收理由')
    if action=='revise':await page.get_by_placeholder('修改后的陈述摘要').fill('独立更正内容')
    if action=='recheck':await page.get_by_placeholder('数据值（如 14:22:15）').fill('synthetic observed')
    n=len(posts);await page.get_by_test_id('btn-'+action).click()
    await expect(page.locator('.toast')).to_contain_text('已写入审计')
    assert len(posts)==n+1
    url,body=posts[-1]
    assert '/cases/'+cid+'/interview-compare/IR-01/' in url and url.endswith(sid+':'+action)
    assert getdoc(api,peer)==before
    doc=getdoc(api,cid);st=next(x for x in doc['statements'] if x['statementId']==sid)
    if action=='confirm':assert st['reviewStatus']=='Confirmed'
    if action=='reject':assert st['reviewStatus']=='Rejected'
    if action=='revise':assert st['summary']=='独立更正内容' and st['revision']==2
    if action=='recheck':assert any(x['statementId']==sid and x['observedText']=='synthetic observed' for x in doc['crossChecks'])
   for action in ['confirm','reject','revise','recheck']:await check('real-ui-'+action+'-isolated',lambda a=action:mutate(a,'S-'+a))
   async def record_race():
    await nav(A,True);await ready(A)
    await page.get_by_placeholder('理由 / 备注（驳回、修改、重新比对必填）').fill('DO-NOT-LEAK-OLD-FORM')
    gate=asyncio.Event();entered=asyncio.Event()
    async def delay(route):
     response=await route.fetch();entered.set();await gate.wait();await route.fulfill(response=response)
    await page.route('**/cases/'+A+'/interview-compare/IR-02',delay)
    await page.locator('[data-record="IR-02"]').click();await entered.wait()
    assert await page.locator('[data-testid="ic-transcript"]').count()==0
    assert await page.locator('[data-testid="ic-actions"]').count()==0
    await page.locator('[data-record="IR-03"]').click();await ready(A,'IR-03')
    await expect(page.get_by_placeholder('理由 / 备注（驳回、修改、重新比对必填）')).to_have_value('')
    gate.set();await page.wait_for_timeout(200)
    await ready(A,'IR-03')
    assert 'IR-02' not in await page.locator('[data-testid="ic-transcript"]').inner_text()
   await check('fault-delayed-record-form-isolation',record_race)
   async def case_race(detail):
    await nav(B,True);await ready(B)
    gate=asyncio.Event();entered=asyncio.Event()
    pattern='**/cases/'+A+'/interview-compare'+('/IR-01' if detail else '')
    async def delay(route):
     response=await route.fetch();entered.set();await gate.wait();await route.fulfill(response=response)
    await page.route(pattern,delay)
    await nav(A);await entered.wait()
    assert await page.locator('[data-testid="ic-actions"]').count()==0
    await nav(B);await ready(B)
    gate.set();await page.wait_for_timeout(200);await ready(B)
    await page.go_back();await ready(A)
    await page.go_forward();await ready(B)
   for detail in [False,True]:await check('fault-delayed-case-'+('detail' if detail else 'roster')+'-back-forward',lambda d=detail:case_race(d))
   async def identity_race():
    await nav(A,True);await ready(A)
    gate=asyncio.Event();entered=asyncio.Event()
    async def delay(route):
     response=await route.fetch();entered.set();await gate.wait();await route.fulfill(response=response)
    await page.route('**/cases/'+A+'/interview-compare/IR-02',delay)
    await page.locator('[data-record="IR-02"]').click();await entered.wait()
    await role('Public')
    await expect(page.locator('[role="alert"]')).to_contain_text('后端错误')
    gate.set();await page.wait_for_timeout(200)
    assert await page.locator('[data-testid="ic-transcript"]').count()==0
    assert 'SYNTHETIC-PRIVATE' not in await page.locator('body').inner_text()
    await role('Investigator');await ready(A)
    await page.get_by_placeholder('理由 / 备注（驳回、修改、重新比对必填）').fill('IDENTITY-FORM')
    await page.evaluate('async()=>{const api=await import("/src/api.ts");api.setIdentity("Investigator","Changed synthetic operator")}')
    await ready(A)
    await expect(page.get_by_placeholder('理由 / 备注（驳回、修改、重新比对必填）')).to_have_value('')
   await check('fault-late-protected-detail-after-role-and-operator-switch',identity_race)
   async def late_write(fail):
    cid='W5-LATE-'+str(fail);case(api,cid,True);record(api,cid)
    await nav(cid,True);await ready(cid)
    gate=asyncio.Event();entered=asyncio.Event()
    async def delay(route):
     response=None if fail else await route.fetch()
     entered.set();await gate.wait()
     if fail:await route.fulfill(status=500,json={'code':'SYNTHETIC_FAILURE','message':'OLD-CASE-ERROR'})
     else:await route.fulfill(response=response)
    await page.route('**/cases/'+cid+'/interview-compare/IR-01/rows/S-confirm:confirm',delay)
    n=len(posts)
    await page.get_by_test_id('btn-confirm').evaluate('(e)=>{e.click();e.click()}')
    await entered.wait();assert len(posts)==n+1
    await expect(page.get_by_test_id('btn-confirm')).to_be_disabled()
    await nav(B);await ready(B)
    gate.set();await page.wait_for_timeout(200)
    assert await page.locator('.toast').count()==0
    await ready(B)
    await expect(page.get_by_test_id('btn-confirm')).to_be_enabled()
    doc=getdoc(api,cid)
    assert next(x for x in doc['statements'] if x['statementId']=='S-confirm')['reviewStatus']==('Draft' if fail else 'Confirmed')
   for fail in [False,True]:await check('fault-late-mutation-'+('error' if fail else 'success')+'-duplicate-guard',lambda f=fail:late_write(f))
   async def mismatch(detail):
    response=request(api,f'/cases/{A}/interview-compare'+('/IR-01' if detail else ''))[1]
    response['caseId']='WRONG-CASE'
    pattern='**/cases/'+A+'/interview-compare'+('/IR-01' if detail else '')
    await page.route(pattern,lambda route:route.fulfill(json=response))
    await nav(A,True)
    await expect(page.locator('[role="alert"]')).to_contain_text('不一致')
    assert await page.locator('[data-testid="ic-actions"]').count()==0
    assert await page.locator('[data-testid="ic-transcript"]').count()==0
   for detail in [False,True]:await check('fault-mismatch-'+('detail' if detail else 'roster'),lambda d=detail:mismatch(d))
   async def encoded_statement():
    cid='W5-ENCODED';case(api,cid,True)
    doc=document(cid);sid='S &?#汉字'
    doc['statements'][0]['statementId']=sid;doc['crossChecks'][0]['statementId']=sid
    assert request(api,f'/cases/{cid}/interviews',doc)[0]==201
    await nav(cid,True);await ready(cid)
    n=len(posts);await page.get_by_test_id('btn-confirm').click()
    await expect(page.locator('.toast')).to_contain_text('已写入审计')
    assert len(posts)==n+1
    assert posts[-1][0].endswith('/rows/'+urllib.parse.quote(sid,safe="~!*'()")+':confirm')
    assert next(st for st in getdoc(api,cid)['statements'] if st['statementId']==sid)['reviewStatus']=='Confirmed'
   await check('real-special-statement-id-url-encoding',encoded_statement)
   async def record_mismatch(nested):
    response=request(api,f'/cases/{A}/interview-compare/IR-01')[1]
    if nested:response['record']['recordId']='IR-02'
    else:response['recordId']='IR-02'
    await page.route('**/cases/'+A+'/interview-compare/IR-01',lambda route:route.fulfill(json=response))
    await nav(A,True)
    await expect(page.locator('[role="alert"]')).to_contain_text('不一致')
    assert await page.locator('[data-testid="ic-transcript"]').count()==0
    assert await page.locator('[data-testid="ic-actions"]').count()==0
   for nested in [False,True]:await check('fault-record-id-mismatch-'+str(nested),lambda n=nested:record_mismatch(n))
   async def redacted_role():
    await nav(A,True);await ready(A)
    await role('ExternalExpert')
    await expect(page.locator('[data-testid="ic-transcript"]')).to_contain_text('[已遮盖]')
    assert 'SYNTHETIC-PRIVATE' not in await page.locator('[data-testid="ic-transcript"]').inner_text()
    before=getdoc(api,A)
    await page.get_by_test_id('btn-confirm').click()
    await expect(page.locator('.toast')).to_contain_text('只读')
    assert getdoc(api,A)==before
   await check('real-external-role-redaction-write-rejection',redacted_role)
   async def missing():
    await nav('W5-NO-SUCH-CASE',True)
    await expect(page.locator('[role="alert"]')).to_contain_text('后端错误')
    assert 'Lily' not in await page.locator('body').inner_text()
    assert await page.locator('[data-testid="ic-actions"]').count()==0
   await check('real-missing-case-no-demo-fallback',missing)
   assert not errors,errors
   await browser.close()
 OUT.joinpath('results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
 print(json.dumps(results,ensure_ascii=False,indent=2))
 if any(r['result']!='PASS' for r in results):raise SystemExit(1)
asyncio.run(run())
