"""Chromium acceptance. Real localhost service unless explicitly FAULT-INJECTED.
Run system Python (Playwright installed), not service venv.
"""
import asyncio,json,pathlib,sys,traceback,uuid
from playwright.async_api import async_playwright,expect
from harness import servers,request,payload
OUT=pathlib.Path(__file__).resolve().parent/'artifacts'; OUT.mkdir(exist_ok=True)
results=[]
async def run():
 with servers(web=True) as (api,web):
  async with async_playwright() as pw:
   browser=await pw.chromium.launch(executable_path='/tmp/w8-headless/chrome-headless-shell-linux64/chrome-headless-shell',headless=True,args=['--no-sandbox'])
   context=await browser.new_context(viewport={'width':1440,'height':1000},timezone_id='America/Los_Angeles')
   page=await context.new_page(); posts=[]
   page.on('request',lambda r:posts.append(r.post_data_json) if r.method=='POST' and r.url.endswith('/api/v1/cases') else None)
   async def check(name,fn):
    try:
     print('RUN',name,flush=True); await fn(); results.append({'name':name,'result':'PASS'})
    except Exception as e:
     results.append({'name':name,'result':'FAIL','error':str(e)}); traceback.print_exc()
     await page.screenshot(path=str(OUT/(name+'.png')),full_page=True)
    finally: await page.unroute_all(behavior='ignoreErrors')
   async def fresh(cid=None,fictional='true'):
    await page.goto(web+'/?run='+uuid.uuid4().hex+'#/lobby');await page.locator('.role-select').select_option('Investigator')
    await page.get_by_role('button',name='＋ 新建案件').click()
    cid=cid or 'W82-B-'+uuid.uuid4().hex[:10]
    for label,val in [('案号',cid),('案件名称','独立浏览器 <script>alert(1)</script>'),('事故时间（UTC）','2026-11-12T08:30:00Z'),('经度（°）','180'),('纬度（°）','-90'),('水域 / 地点','独立验收地点')]:
     await page.get_by_label(label,exact=False).fill(val)
    await page.get_by_label('事故类型',exact=False).select_option('Collision')
    await page.get_by_label('数据性质',exact=False).select_option(fictional)
    return cid
   submit=lambda:page.get_by_role('button',name='创建案件',exact=True).click()
   verify=lambda:page.get_by_role('button',name='核查创建结果（只读）').click()
   async def success():await expect(page.get_by_role('heading',name='案件已创建')).to_be_visible()
   async def normal(width,fictional):
    await page.set_viewport_size({'width':width,'height':1000});cid=await fresh(fictional=fictional); before=len(posts)
    await page.screenshot(path=str(OUT/f'form-{width}.png'),full_page=True)
    await page.get_by_role('button',name='创建案件',exact=True).scroll_into_view_if_needed()
    await page.screenshot(path=str(OUT/f'form-bottom-{width}.png'),full_page=True)
    assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'page horizontal overflow'
    await submit();await success();assert len(posts)==before+1
    body=posts[-1]; assert body['incidentTimeUtc']==body['caseEpochUtc']=='2026-11-12T08:30:00Z' and body['displayTimeZoneOffsetMinutes']==0
    assert body['incidentLocation']=={'latDeg':-90,'lonDeg':180}; assert 'durationSec' not in body
    assert request(api,'/cases/'+cid)==(200,body)
    await expect(page.locator('.w8-lobby')).to_contain_text(cid)
    await page.get_by_role('link',name='进入新案件 →').click();await expect(page.locator('.case-chip')).to_contain_text(cid)
    await expect(page.locator('.demo-banner')).to_contain_text('独立浏览器')
    await expect(page.locator('.page-title').first).to_contain_text('证据中心')
    await page.wait_for_timeout(500)
    text=await page.locator('body').inner_text();assert 'Lily' not in text and 'Mary' not in text and '公开报告' not in text and 'UTC+8' not in text
    await expect(page.locator('canvas')).to_have_count(0)
    await expect(page.locator('body')).to_contain_text('暂无证据')
    assert '加载中' not in text
    assert ('非虚构案件' if fictional=='false' else '示例数据（虚构）') in text
    assert len(request(api,'/cases/'+cid+'/audit')[1])==1
    await page.screenshot(path=str(OUT/f'evidence-{width}.png'),full_page=True)
    await page.go_back();await expect(page.get_by_role('button',name='＋ 新建案件')).to_be_visible()
    await page.go_forward();await expect(page.locator('.case-chip')).to_contain_text(cid)
   for width,fictional in [(1440,'true'),(768,'false')]:await check(f'real-create-evidence-{width}',lambda w=width,f=fictional:normal(w,f))
   await page.set_viewport_size({'width':1440,'height':1000})
   async def offset_regression():
    for offset,stamp,expected,label in [(0,'2026-12-31T23:45:00Z','12-31 23:45','UTC'),(480,'2026-12-31T23:45:00Z','01-01 07:45','UTC+08:00'),(-330,'2026-01-01T02:15:00Z','12-31 20:45','UTC-05:30')]:
     cid='W82-offset-'+str(offset);body=payload(cid);body['displayTimeZoneOffsetMinutes']=offset
     assert request(api,'/cases',body)[0]==201
     ev=dict(title='Offset reference evidence',source='Independent temporary fixture',extractedBy='Acceptance',extractedUtc=stamp,sha256='0'*64)
     assert request(api,'/cases/'+cid+'/evidence',ev)[0]==201
     await page.goto(web+'/#/evidence?case='+cid)
     await expect(page.locator('body')).to_contain_text(label)
     await expect(page.locator('td.mono').filter(has_text=expected)).to_have_count(1)
     got=await page.evaluate("""async ({stamp,offset}) => {const m=await import('/src/cases/evidenceTime.ts');return [m.toLocal(stamp,true,offset),m.simToClock(stamp,0,true,offset),m.timeZoneLabel(offset),m.distanceTooltip(stamp,0,2.345,offset)]}""",{'stamp':stamp,'offset':offset})
     assert got==[expected,expected[-5:]+':00',label,expected[-5:]+':00 距离 2.35 nm'],got
    await page.screenshot(path=str(OUT/'offset-negative-cross-day.png'),full_page=True)
   await check('real-offset-UTC-positive-negative-cross-day-evidence',offset_regression)
   async def validation():
    await fresh();before=len(posts)
    for label,invalid,valid in [('案号','ab','W82-valid'),('案号','中文','W82-valid'),('案件名称','  ','valid'),('事故时间（UTC）','0000-01-01T00:00:00Z','2026-11-12T08:30:00Z'),('事故时间（UTC）','2026-02-30T08:30:00Z','2026-11-12T08:30:00Z'),('事故时间（UTC）','2026-11-12T08:30:00+08:00','2026-11-12T08:30:00Z'),('经度（°）','','180'),('经度（°）','Infinity','180'),('经度（°）','180.00001','180'),('纬度（°）','-90.00001','-90')]:
     await page.get_by_label(label,exact=False).fill(invalid);await submit();await expect(page.get_by_role('alert')).to_be_visible();assert len(posts)==before;await page.get_by_label(label,exact=False).fill(valid)
    await page.get_by_role('button',name='关闭',exact=True).click();await page.get_by_role('button',name='＋ 新建案件').click();await expect(page.get_by_label('案号',exact=False)).to_have_value('')
    for role in ['Public','ExternalExpert','InterestedState']:
     await page.locator('.role-select').select_option(role);await expect(page.get_by_role('button',name='＋ 新建案件')).to_have_count(0)
    await page.locator('.role-select').select_option('LeadInvestigator');await expect(page.get_by_role('button',name='＋ 新建案件')).to_be_visible()
   await check('browser-validation-roles-reset',validation)
   async def sequential():
    cid=await fresh();before=len(posts);await submit();await success()
    await page.get_by_role('button',name='继续新建').click()
    await expect(page.get_by_label('案号',exact=False)).to_have_value('')
    second=cid+'-second'
    for label,val in [('案号',second),('案件名称','Second independent case'),('事故时间（UTC）','2026-11-12T08:31Z'),('经度（°）','-180'),('纬度（°）','90')]:
     await page.get_by_label(label,exact=False).fill(val)
    await page.get_by_label('事故类型',exact=False).select_option('Other')
    await page.get_by_label('数据性质',exact=False).select_option('false')
    await submit();await success();assert len(posts)==before+2
    assert posts[-1]['incidentTimeUtc']=='2026-11-12T08:31:00Z' and 'placeName' not in posts[-1]
    assert len(request(api,'/cases/'+second+'/audit')[1])==1
    await fresh()
    await page.route('**/api/v1/cases',lambda r:r.abort('failed') if r.request.method=='POST' else r.continue_())
    before=len(posts);await submit();await expect(page.get_by_role('alert')).to_contain_text('尚未确认')
    await page.get_by_role('button',name='关闭表单（不撤销已发请求）').click()
    await page.get_by_role('button',name='＋ 新建案件').click()
    await expect(page.get_by_label('案号',exact=False)).to_have_value('')
    assert len(posts)==before+1
   await check('real-sequential-create-and-uncertain-close-reset',sequential)
   async def errors():
    cid=await fresh(); await submit();await success()
    await page.get_by_role('button',name='继续新建').click()
    # reopen through fresh navigation clears all prior state
    await fresh(cid);before=len(posts);await submit();await expect(page.get_by_role('alert')).to_contain_text('已存在');assert len(posts)==before+1
    assert len(request(api,'/cases/'+cid+'/audit')[1])==1
    for status in [403,422]:
     async def reject(route):
      if route.request.method=='POST': await route.fulfill(status=status,json={'code':'INJECTED','message':'fault injection'})
      else: await route.continue_()
     await page.route('**/api/v1/cases',reject)
     before=len(posts);await submit();await expect(page.get_by_role('alert')).to_contain_text('无权' if status==403 else '修正');await expect(page.get_by_label('案号',exact=False)).to_have_value(cid);assert len(posts)==before+1
     await page.unroute_all()
   await check('real-409-injected-403-422',errors)
   async def lost_response():
    cid=await fresh();before=len(posts)
    async def lost(route):
     if route.request.method=='POST':
      response=await route.fetch(); assert response.status==201;await route.abort('failed')
     else:await route.continue_()
    await page.route('**/api/v1/cases',lost);await submit();await expect(page.get_by_role('alert')).to_contain_text('尚未确认')
    await expect(page.get_by_label('案号',exact=False)).to_be_disabled()
    assert len(posts)==before+1 and request(api,'/cases/'+cid)[0]==200
    # Simulated read failure, then real read recovery; no additional POST.
    await page.route('**/api/v1/cases/'+cid,lambda route:route.fulfill(status=503,json={'code':'INJECTED'}))
    await verify();await expect(page.get_by_role('alert')).to_contain_text('暂时无法核查')
    await page.unroute('**/api/v1/cases/'+cid);await verify();await success();assert len(posts)==before+1
    assert len(request(api,'/cases/'+cid+'/audit')[1])==1
   await check('real-write-lost-response-read-failure-recovery',lost_response)
   async def uncertain():
    cid=await fresh();before=len(posts)
    await page.route('**/api/v1/cases',lambda r:r.fulfill(status=500,json={'code':'INJECTED'}) if r.request.method=='POST' else r.continue_())
    await submit();await expect(page.get_by_role('alert')).to_contain_text('尚未确认');await verify();await expect(page.get_by_role('alert')).to_contain_text('未找到');assert len(posts)==before+1
    await page.unroute_all();await submit();await success();assert len(posts)==before+2
    cid=await fresh();before=len(posts)
    await page.route('**/api/v1/cases',lambda r:r.fulfill(status=201,json={}) if r.request.method=='POST' else r.continue_())
    await submit();await expect(page.get_by_role('alert')).to_contain_text('尚未确认')
    await page.route('**/api/v1/cases/'+cid,lambda r:r.fulfill(status=200,json={'caseId':cid,'title':'different'}))
    await verify();await expect(page.get_by_role('alert')).to_contain_text('内容与本次提交不同');assert len(posts)==before+1
    await expect(page.get_by_label('案号',exact=False)).to_be_disabled()
   await check('injected-5xx-404-explicit-retry-invalid-success-conflict',uncertain)
   async def interruption(kind):
    cid=await fresh();before=len(posts);release=asyncio.Event();started=asyncio.Event()
    async def delayed(route):
     if route.request.method=='POST':
      response=await route.fetch();started.set();await release.wait();await route.fulfill(response=response)
     else:await route.continue_()
    await page.route('**/api/v1/cases',delayed)
    await page.get_by_role('button',name='创建案件',exact=True).evaluate('(el)=>{el.click();el.click()}');await asyncio.wait_for(started.wait(),10)
    await expect(page.get_by_role('button',name='关闭',exact=True)).to_be_disabled()
    if kind=='identity':await page.locator('.role-select').select_option('Public')
    else:await page.locator('.nav-item').filter(has_text='证据中心').click()
    release.set();await page.wait_for_timeout(500);assert len(posts)==before+1
    await expect(page.get_by_role('heading',name='案件已创建')).to_have_count(0)
    if kind=='identity':
     await page.locator('.role-select').select_option('Investigator');await page.get_by_role('button',name='＋ 新建案件').click();await expect(page.get_by_label('案号',exact=False)).to_have_value('')
    else:
     await page.go_back();await expect(page.get_by_role('button',name='＋ 新建案件')).to_be_visible()
    assert len(request(api,'/cases/'+cid+'/audit')[1])==1
   for kind in ['identity','navigation']:await check('real-delayed-doubleclick-'+kind,lambda k=kind:interruption(k))
   await browser.close()
 print(json.dumps(results,ensure_ascii=False,indent=2));(OUT/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
 return any(r['result']=='FAIL' for r in results)
if __name__=='__main__':sys.exit(asyncio.run(run()))
