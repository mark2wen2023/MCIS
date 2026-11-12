// Independently authored acceptance. Synthetic evidence; loopback fake model, never real LLM quality.
const {chromium}=require(process.env.MCIS_PLAYWRIGHT_MODULE || 'playwright');
const fs=require('fs'),assert=require('assert'),path=require('path');
const runDir=process.env.MCIS_W20UI_RUN_DIR, artifacts=process.env.MCIS_W20UI_ARTIFACT_DIR;
const web=process.env.MCIS_W20UI_WEB_URL;
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.MCIS_BROWSER_BIN || undefined,headless:true,args:['--no-sandbox']});
 try {
 const p=await browser.newPage({viewport:{width:1365,height:900}});p.setDefaultTimeout(12000);
 const api=JSON.parse(fs.readFileSync(path.join(runDir,'session.json'))).api+'/api/v1';
 const cid='CASE-W202-QA', base=api+'/cases/'+cid, panel=p.locator('.w20-agent');
 const gen=()=>panel.getByRole('button',{name:'提取当前笔录为待审草稿'}), confirm=()=>panel.getByRole('button',{name:'确认以上陈述并写回'}), check=()=>panel.getByRole('checkbox',{name:/已核对本条/});
 let passes=0;const ok=(v,m)=>{assert(v,m);console.log('PASS '+(++passes)+' '+m)};
 const req=async(path,body,role='Investigator')=>{const r=await fetch(base+path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json','X-MCIS-Role':role},body:body?JSON.stringify(body):undefined});return {status:r.status,data:await r.json()}};
 const ready=async()=>p.waitForFunction(()=>document.querySelector('.w20-run button')?.disabled===false);
 const refresh=async()=>{await panel.getByRole('button',{name:'读取服务器状态'}).click();await ready()};
 const mode=v=>fs.writeFileSync(path.join(runDir,'model-mode'),v);
 const errors=[];p.on('pageerror',e=>errors.push(String(e)));let posts=0;p.on('request',r=>{if(r.method()==='POST'&&r.url().includes('/agents/'))posts++});
 await p.goto(web+'/#/interview?case='+cid);await ready();
 const registry=await (await fetch(api+'/agents')).json();ok(registry.length===6&&registry.filter(x=>x.status==='not_connected').length===5,'six actual registry roles, five disconnected');
 ok((await panel.innerText()).includes('连接与能力未验证'),'configured explicitly not healthy/inference proof');
 for(const state of ['not_connected','invalid_configuration']){
 await p.route('**/api/v1/agents',r=>r.fulfill({json:registry.map(a=>a.agent==='people_ops'?{...a,status:state}:a)}));
 await panel.getByRole('button',{name:'读取服务器状态'}).click();await p.waitForTimeout(400);ok(await gen().isDisabled(),'injected registry '+state+' disables extraction');await p.unroute('**/api/v1/agents');
 }await refresh();
 await gen().focus();await p.keyboard.press('Enter');await confirm().waitFor();
 ok(await confirm().isDisabled(),'keyboard extraction, confirmation blocked before human check');
 ok((await req('/interviews/IR-90')).data.statements.length===0,'real backend PendingReview leaves statements unchanged');
 await check().focus();await p.keyboard.press('Space');await confirm().focus();await p.keyboard.press('Enter');await panel.getByText(/已经服务端确认并写回陈述/).waitFor();
 ok((await req('/interviews/IR-90')).data.statements.length===1,'keyboard confirmation appends once');await p.getByText('1 条陈述 · 0 条矛盾',{exact:true}).waitFor();ok(true,'W5 counts refreshed');
 await ready();await gen().click();await ready();await confirm().waitFor();const reject=panel.getByRole('button',{name:'驳回此草稿，不写回'});ok(await reject.isDisabled(),'reject requires reason');await panel.getByRole('textbox',{name:'审核备注（驳回必填）'}).fill('合成测试：解读不支持');await reject.click();await panel.getByText(/已驳回，未写入陈述/).waitFor();ok((await req('/interviews/IR-90')).data.statements.length===1,'reject writes no statements');
 await ready();mode('failure');await gen().click();await panel.getByText(/MODEL_HTTP_ERROR/).waitFor();ok((await req('/agents/drafts')).data.length===2,'real fake-model HTTP failure creates no draft');mode('ok');await ready();
 await gen().click();await ready();await confirm().waitFor();await req('/interviews/IR-90/turns',{question:'合成追加问答',answer:'来源版本改变'});await check().check();await confirm().click();await panel.getByText(/原文已变化，不能确认旧草稿/).waitFor();ok((await req('/interviews/IR-90')).data.statements.length===1,'real SOURCE_CHANGED visible without write');
 await ready();await gen().click();await ready();await confirm().waitFor();let drafts=(await req('/agents/drafts')).data;let latest=drafts.at(-1);await req('/agents/drafts/'+latest.draftId+'/review',{decision:'Rejected',note:'另一个审核者已处理'});await check().check();await confirm().click();await panel.getByText(/此草稿已处理/).waitFor();ok((await req('/interviews/IR-90')).data.statements.length===1,'real ALREADY_REVIEWED error no duplicate write');await ready();
 ok((await req('/agents/people_ops/interviews/IR-90:extract',{},'ExternalExpert')).status===403,'backend enforces forbidden extraction independent of UI');
 ok((await req('/agents/drafts/'+latest.draftId+'/review',{decision:'Confirmed'},'AgentService')).status===403,'backend forbids AgentService review');
 await p.route('**/agents/people_ops/**',async r=>{const result=await r.fetch({headers:{...r.request().headers(),'x-mcis-role':'ExternalExpert'}});await r.fulfill({response:result})});await gen().click();await panel.getByText(/后端拒绝当前权限/).waitFor();ok(true,'actual backend 403 rendered');await p.unroute('**/agents/people_ops/**');await ready();
 mode('delay');const n=posts;await gen().dblclick();await p.locator('.ic-person').nth(1).click();await p.waitForTimeout(4400);ok(posts===n+1,'double-click one POST');ok(!(await panel.innerText()).includes('值班人员称发现目标船'),'late extraction isolated after record switch');
 await p.locator('.ic-person').nth(0).click();await ready();await gen().click();await p.locator('.topbar select').selectOption('ExternalExpert');await p.waitForTimeout(4400);ok(!(await panel.innerText()).includes('值班人员称发现目标船'),'late extraction isolated after identity switch');await p.locator('.topbar select').selectOption('Investigator');await ready();
 await gen().click();await p.evaluate(()=>location.hash='#/interview?case=CASE-W202-OTHER');await p.waitForTimeout(4400);ok(!(await panel.innerText()).includes('值班人员称发现目标船'),'late extraction isolated after same-document case switch');
 mode('ok');await p.evaluate(()=>location.hash='#/interview?case=CASE-W202-QA');await ready();
 await p.route('**/agents/people_ops/**',async r=>{await r.fetch();await r.abort()});const before=(await req('/agents/drafts')).data.length;await gen().click();await panel.getByText(/结果未确认，操作已锁定/).waitFor();ok(await gen().isDisabled(),'lost committed response locks retry');await p.unroute('**/agents/people_ops/**');await panel.getByRole('button',{name:'读取服务器状态'}).click();await p.waitForTimeout(400);ok((await req('/agents/drafts')).data.length===before+1,'unknown result refetch never automatically resends');await panel.getByRole('checkbox',{name:/我已核对服务器/}).check();await panel.getByRole('button',{name:'核查后解除本页锁定'}).click();await ready();
 // Response-only adversarial text injection tests rendering, not backend validation.
 await p.route('**/agents/drafts',async r=>{const response=await r.fetch();const ds=await response.json();ds.forEach(d=>{d.payload.statements[0].summary='<img src=x onerror="window.ACCEPTANCE_XSS=1">'+'很长候选'.repeat(500)});await r.fulfill({json:ds})});await refresh();await p.setViewportSize({width:390,height:844});await p.waitForTimeout(300);ok(!await p.evaluate(()=>window.ACCEPTANCE_XSS),'HTML rendered as escaped text');ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'390px mobile no horizontal document overflow');await p.screenshot({path:path.join(artifacts,'mobile.png'),fullPage:true});await p.unroute('**/agents/drafts');

 await p.setViewportSize({width:1365,height:900});await refresh();
 await p.evaluate(async()=>{const a=await import('/src/api.ts');a.setIdentity('AgentService')});await ready();ok(await confirm().isDisabled(),'AgentService sees queue but cannot confirm');await p.locator('.topbar select').selectOption('Investigator');await ready();
 await p.route('**/agents/drafts',async r=>{const response=await r.fetch();const ds=await response.json();ds[0].caseId='CASE-W202-OTHER';await r.fulfill({json:ds})});await panel.getByRole('button',{name:'读取服务器状态'}).click();await panel.getByText(/草稿队列与当前案件不一致/).waitFor();ok(await gen().isDisabled()&&await panel.locator('.w20-draft').count()===0,'cross-case queue response rejected, not rendered');await p.unroute('**/agents/drafts');await refresh();
 await p.route('**/agents/drafts',async r=>{const response=await r.fetch();const ds=await response.json();for(const d of ds){d.payload.statements.push({...d.payload.statements[0],summary:'第二候选，仍需人工核对'});d.citations.push({...d.citations[0]})}await r.fulfill({json:ds})});await refresh();await check().first().check();ok(await confirm().isDisabled(),'two-item draft requires every semantic acknowledgement');await check().nth(1).check();ok(await confirm().isEnabled(),'two acknowledgements enable explicit write, no auto-write');await p.screenshot({path:path.join(artifacts,'desktop.png'),fullPage:true});await p.unroute('**/agents/drafts');await refresh();
 await p.route('**/agents/people_ops/**',async r=>{const response=await r.fetch();const d=await response.json();d.targetEntityId='IR-91';await r.fulfill({json:d})});await gen().click();await panel.getByText(/结果未确认，操作已锁定/).waitFor();ok(await gen().isDisabled(),'mismatched successful response cannot claim success or resend');await p.unroute('**/agents/people_ops/**');
 ok(errors.length===0,'no browser runtime errors');console.log('TOTAL '+passes+' PASS; REAL FASTAPI + LOOPBACK FAKE MODEL; NO REAL LLM TESTED');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
