"""Independent real-browser/real-HTTP W9.1 tests. Explicit faults are labeled."""
import asyncio,json,pathlib,sys,traceback,uuid,re
from playwright.async_api import async_playwright,expect
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'W82'))
from harness import servers,request,payload
OUT=pathlib.Path(__file__).parent/'artifacts';OUT.mkdir(exist_ok=True)
results=[]
async def run():
 with servers(web=True) as (api,web):
  for cid,fictional in [('W91-browser-A',True),('W91-browser-B',True),('W91-browser-real',False)]:
   body=payload(cid);body['isFictionalDemo']=fictional;body['title']=cid+' synthetic fixture'
   assert request(api,'/cases',body)[0]==201
  async with async_playwright() as pw:
   browser=await pw.chromium.launch(executable_path='/tmp/w8-headless/chrome-headless-shell-linux64/chrome-headless-shell',headless=True,args=['--no-sandbox'])
   context=await browser.new_context(viewport={'width':1440,'height':1000})
   page=await context.new_page();posts=[];errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.on('request',lambda r:posts.append(r.post_data_json) if r.method=='POST' and '/vessels' in r.url else None)
   async def go(cid='W91-browser-A'):
    await page.goto(web+'/?run='+uuid.uuid4().hex+'#/ships?case='+cid)
    await page.locator('.role-select').select_option('Investigator')
    await expect(page.locator('.w9-case')).to_contain_text(cid)
   async def form(vid='test',name='Independent synthetic ship'):
    await page.get_by_role('button',name='＋ 新增船舶').click()
    await page.get_by_label('船舶编号（必填，案件内唯一）',exact=True).fill(vid)
    await page.get_by_label('船名（必填）',exact=True).fill(name)
   async def submit():await page.get_by_role('button',name='保存船舶',exact=True).click()
   async def success():await expect(page.get_by_role('heading',name='船舶已保存')).to_be_visible()
   async def check(name,fn):
    try:
     print('RUN',name,flush=True);await fn();results.append({'name':name,'status':'PASS'})
    except Exception as e:
     results.append({'name':name,'status':'FAIL','error':str(e)});traceback.print_exc()
     await page.screenshot(path=str(OUT/(name+'-failure.png')),full_page=True)
    finally:await page.unroute_all(behavior='ignoreErrors')
   async def normal():
    await go();await expect(page.locator('.w9-page')).to_contain_text('本案尚无船舶参数')
    await form('W91-saved','Synthetic <script>alert(1)</script>')
    await page.get_by_label('总长（m）（可选）',exact=True).fill('210.125')
    await page.get_by_label('总长（m） · 来源',exact=True).fill('Synthetic plan page 2')
    await page.get_by_label('总长（m） · 口径',exact=False).select_option('Derived')
    await page.get_by_label('首吃水（m）（可选）',exact=True).fill('0')
    await page.locator('.main').evaluate('e=>e.scrollTop=0')
    await page.screenshot(path=str(OUT/'form-1440.png'),full_page=True)
    await page.get_by_role('button',name='保存船舶',exact=True).scroll_into_view_if_needed()
    await page.screenshot(path=str(OUT/'form-bottom-1440.png'),full_page=True)
    before=len(posts)
    # Two synchronous submit events exercise the ref gate rather than relying on disabled timing.
    await page.locator('.w9-create form').evaluate("f=>{f.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));f.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))}")
    await success();assert len(posts)==before+1
    data=request(api,'/cases/W91-browser-A/vessels')[1]
    assert len(data)==1 and data[0]['loaM']==210.125 and data[0]['draftForeM']==0 and 'beamM' not in data[0]
    await expect(page.locator('.w9-vessel')).to_contain_text('【推算】Synthetic plan page 2')
    await page.reload();await expect(page.locator('.w9-vessel')).to_contain_text('W91-saved')
    await expect(page.locator('.w9-vessel')).to_contain_text('Synthetic <script>alert(1)</script>')
    assert await page.locator('.w9-vessel script').count()==0
    await page.screenshot(path=str(OUT/'saved-1440.png'),full_page=True)
    style=await page.get_by_role('button',name='＋ 新增船舶').evaluate('e=>({fg:getComputedStyle(e).color,bg:getComputedStyle(e).backgroundColor})')
    OUT.joinpath('button-colors.json').write_text(json.dumps(style))
    def luminance(css):
     rgb=[int(n)/255 for n in re.findall(r'\d+',css)[:3]]
     linear=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
     return sum(v*w for v,w in zip(linear,[.2126,.7152,.0722]))
    a,b=sorted([luminance(style['fg']),luminance(style['bg'])]);assert (b+.05)/(a+.05)>=4.5,'enabled button contrast' 
    await page.get_by_role('link',name='返回案件大厅').click()
    await page.get_by_role('link',name='进入案件：W91-browser-A synthetic fixture').click()
    await page.locator('a[href*="/ships"]').click()
    assert 'case=W91-browser-A' in page.url
    await expect(page.locator('.w9-vessel')).to_contain_text('W91-saved')
    await page.go_back();await page.go_forward();await expect(page.locator('.w9-vessel')).to_contain_text('W91-saved')
   await check('real-create-double-submit-reopen-navigation',normal)
   async def validation():
    await go('W91-browser-real');await form('W91-real','Synthetic real-case fixture')
    before=len(posts);await submit();await expect(page.get_by_role('alert')).to_contain_text('来源');assert len(posts)==before
    await page.get_by_label('船名 · 来源',exact=True).fill('Synthetic registry record')
    await page.get_by_label('型宽（m）（可选）',exact=True).fill('Infinity')
    await submit();await expect(page.get_by_role('alert')).to_contain_text('正数');assert len(posts)==before
    await page.get_by_label('型宽（m）（可选）',exact=True).fill('32.5')
    await submit();await expect(page.get_by_role('alert')).to_contain_text('来源');assert len(posts)==before
    await page.get_by_label('型宽（m） · 来源',exact=True).fill('Synthetic plan page 8')
    await page.get_by_label('型宽（m） · 口径',exact=False).select_option('Estimated')
    await page.set_viewport_size({'width':768,'height':1000})
    await page.locator('.main').evaluate('e=>e.scrollTop=0')
    await page.screenshot(path=str(OUT/'form-768.png'),full_page=True)
    await page.get_by_role('button',name='保存船舶',exact=True).scroll_into_view_if_needed()
    await page.screenshot(path=str(OUT/'form-bottom-768.png'),full_page=True)
    width=await page.evaluate('document.documentElement.scrollWidth')
    baseline=await context.new_page();await baseline.set_viewport_size({'width':768,'height':1000})
    await baseline.goto(web+'/#/evidence?case=W91-browser-real');await expect(baseline.locator('.case-chip')).to_contain_text('synthetic fixture')
    baseline_width=await baseline.evaluate('document.documentElement.scrollWidth');await baseline.close()
    OUT.joinpath('narrow-layout-baseline.json').write_text(json.dumps({'viewport':768,'ships':width,'existing_evidence':baseline_width}))
    assert width<=768,'W9 must not cause horizontal viewport overflow (Evidence baseline '+str(baseline_width)+')'
    assert await page.locator('.w9-page').evaluate('e=>e.scrollWidth<=e.clientWidth'),'W9 content itself must fit' 
    await submit();await success();await page.reload()
    await expect(page.locator('.w9-vessel')).to_contain_text('【估计】Synthetic plan page 8')
    await page.screenshot(path=str(OUT/'saved-768.png'),full_page=True)
    await page.set_viewport_size({'width':1440,'height':1000})
   await check('real-source-and-number-validation-responsive',validation)
   async def cancel_roles():
    await go('W91-browser-B');await form('discard','Discard me');before=len(posts)
    await page.get_by_role('button',name='关闭',exact=True).click();await page.get_by_role('button',name='＋ 新增船舶').click()
    await expect(page.get_by_label('船舶编号（必填，案件内唯一）',exact=True)).to_have_value('')
    assert len(posts)==before and request(api,'/cases/W91-browser-B/vessels')[1]==[]
    for role in ['Public','ExternalExpert','InterestedState']:
     await page.locator('.role-select').select_option(role)
     await expect(page.get_by_role('button',name='＋ 新增船舶')).to_have_count(0)
     await expect(page.locator('.w9-page')).to_contain_text('当前身份仅可查看')
    await page.locator('.role-select').select_option('LeadInvestigator');await expect(page.get_by_role('button',name='＋ 新增船舶')).to_be_visible()
   await check('real-cancel-role-restrictions',cancel_roles)
   async def duplicate():
    await go();await form('W91-saved','DO NOT OVERWRITE');before=request(api,'/cases/W91-browser-A/vessels')[1]
    await submit();await expect(page.get_by_role('alert')).to_contain_text('已存在')
    await expect(page.get_by_label('船名（必填）',exact=True)).to_have_value('DO NOT OVERWRITE')
    assert request(api,'/cases/W91-browser-A/vessels')[1]==before
   await check('real-duplicate-preserves-existing-and-draft',duplicate)
   async def unknown_saved():
    await go('W91-browser-B');await form('lost-response','Saved but response lost')
    async def lose(route):
     if route.request.method=='POST':await route.fetch();await route.abort('failed')
     else:await route.continue_()
    await page.route('**/api/v1/cases/W91-browser-B/vessels',lose)
    before=len(posts);await submit();await expect(page.get_by_role('alert')).to_contain_text('尚未确认')
    assert len(posts)==before+1
    await expect(page.get_by_role('button',name='保存船舶',exact=True)).to_have_count(0)
    await page.get_by_role('button',name='核查保存结果（只读）').click();await success()
    assert len(posts)==before+1
    assert len(request(api,'/cases/W91-browser-B/vessels')[1])==1
   await check('fault-lost-success-response-read-only-recovery',unknown_saved)
   async def unknown_not_saved():
    await go('W91-browser-B');await form('not-saved','Never reached server')
    async def block(route):
     if route.request.method=='POST':await route.abort('failed')
     else:await route.continue_()
    await page.route('**/api/v1/cases/W91-browser-B/vessels',block)
    before=len(posts);await submit();await expect(page.get_by_role('alert')).to_contain_text('尚未确认')
    await page.get_by_role('button',name='核查保存结果（只读）').click()
    await expect(page.get_by_role('alert')).to_contain_text('未找到');assert len(posts)==before+1
    await page.unroute_all();await submit();await success();assert len(posts)==before+2
   await check('fault-unconfirmed-not-written-manual-retry-only',unknown_not_saved)
   async def identity_race():
    await go('W91-browser-B');await form('identity-race','Identity old draft')
    release=asyncio.Event();started=asyncio.Event()
    async def delay(route):
     if route.request.method=='POST':
      response=await route.fetch();started.set();await release.wait();await route.fulfill(response=response)
     else:await route.continue_()
    await page.route('**/api/v1/cases/W91-browser-B/vessels',delay)
    await submit();await started.wait()
    await page.locator('.role-select').select_option('Public');await expect(page.locator('.w9-page')).to_contain_text('当前身份仅可查看')
    release.set();await page.wait_for_timeout(200)
    await expect(page.get_by_role('heading',name='船舶已保存')).to_have_count(0)
    await expect(page.get_by_role('button',name='＋ 新增船舶')).to_have_count(0)
    await page.locator('.role-select').select_option('Investigator');await expect(page.locator('.w9-vessel').filter(has_text='identity-race')).to_have_count(1)
   await check('fault-identity-switch-during-success-response',identity_race)
   async def case_race():
    await go('W91-browser-B');await form('case-race','Case B delayed')
    release=asyncio.Event();started=asyncio.Event()
    async def delay(route):
     if route.request.method=='POST':
      response=await route.fetch();started.set();await release.wait();await route.fulfill(response=response)
     else:await route.continue_()
    await page.route('**/api/v1/cases/W91-browser-B/vessels',delay)
    await submit();await started.wait()
    await page.evaluate("location.hash='/ships?case=W91-browser-A'")
    await expect(page.locator('.w9-case')).to_contain_text('W91-browser-A');release.set();await page.wait_for_timeout(200)
    await expect(page.locator('.w9-page')).not_to_contain_text('Case B delayed')
    await expect(page.get_by_role('heading',name='船舶已保存')).to_have_count(0)
    assert not any(v['vesselId']=='case-race' for v in request(api,'/cases/W91-browser-A/vessels')[1])
   await check('fault-case-switch-during-success-response',case_race)
   async def refresh_cancel():
    await go('W91-browser-B');await form('discard-refresh','Unsaved refresh draft');before=len(posts)
    await page.get_by_role('button',name='刷新已保存船舶（放弃未保存输入）').click()
    await expect(page.get_by_role('button',name='＋ 新增船舶')).to_be_visible()
    await page.get_by_role('button',name='＋ 新增船舶').click()
    await expect(page.get_by_label('船名（必填）',exact=True)).to_have_value('')
    assert len(posts)==before
   await check('real-explicit-refresh-discards-local-draft',refresh_cancel)
   async def rejected():
    await go('W91-browser-B');await form('policy-reject','Preserve rejected draft')
    async def forbidden(route):
     if route.request.method=='POST':await route.fulfill(status=403,json={'code':'READ_ONLY','message':'Synthetic policy denial'})
     else:await route.continue_()
    await page.route('**/api/v1/cases/W91-browser-B/vessels',forbidden)
    before=len(posts);await submit();await expect(page.get_by_role('alert')).to_contain_text('权限')
    await expect(page.get_by_label('船名（必填）',exact=True)).to_have_value('Preserve rejected draft')
    assert len(posts)==before+1 and not any(v['vesselId']=='policy-reject' for v in request(api,'/cases/W91-browser-B/vessels')[1])
   await check('fault-server-forbidden-keeps-draft-no-retry',rejected)
   async def extra_widths():
    await go('W91-browser-real')
    for width in [390,1920]:
     await page.set_viewport_size({'width':width,'height':1000})
     await expect(page.locator('.w9-vessel')).to_contain_text('W91-real')
     await page.screenshot(path=str(OUT/f'saved-{width}.png'),full_page=True)
     assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth'),'overflow at '+str(width)
    await page.set_viewport_size({'width':1440,'height':1000})
   await check('real-extra-widths-390-and-1920',extra_widths)
   async def unknown_case():
    await page.goto(web+'/#/ships?case=W91-unknown');await expect(page.get_by_role('alert')).to_contain_text('案件不存在')
    await expect(page.get_by_role('button',name='＋ 新增船舶')).to_have_count(0)
    await expect(page.locator('.w9-page')).not_to_contain_text('Lily')
   await check('real-unknown-case-no-demo-fallback',unknown_case)
   results.append({'name':'javascript-console-errors','status':'PASS' if not errors else 'FAIL','errors':errors})
   await browser.close()
 OUT.joinpath('result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
 print(json.dumps(results,ensure_ascii=False,indent=2))
 if any(x['status']=='FAIL' for x in results):raise SystemExit(1)
asyncio.run(run())
