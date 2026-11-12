// Independent W19.1 acceptance: synthetic input only, real localhost service.
const {chromium}=require(process.env.W191_PLAYWRIGHT);
const assert=require('node:assert/strict');
const fs=require('node:fs');
const delay=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
 const b=await chromium.launch({headless:true,executablePath:process.env.W191_CHROMIUM,args:['--no-sandbox']});
 try {
 const p=await b.newPage({viewport:{width:1440,height:1000}}), errors=[];p.on('pageerror',e=>errors.push(String(e)));
  p.setDefaultTimeout(10000);const ui=p.locator('.w19'), empty=()=>ui.getByText('没有符合条件的知识卡。库为空时不伪造样本或模型推荐。'), role=async r=>{await p.locator('.topbar select').selectOption(r);await ui.getByRole('button',{name:'重新读取',exact:true}).waitFor();};
 await p.goto(`http://127.0.0.1:${process.env.W191_WEB_PORT}/#/knowledge`);await empty().waitFor();
 const createForm=async(kind,title)=>{await ui.locator('.w19-create summary').click();await ui.getByRole('button',{name:'在表单中填入合成示例（不保存）'}).click();await ui.locator('.w19-create select').first().selectOption(kind);await ui.locator('.w19-create textarea').nth(0).fill(title);await ui.locator('.w19-create textarea').nth(2).fill('<img src=x onerror="window.w191xss=1"> Synthetic only');};
 for(const kind of ['Case','Challenge','Method']){
  await role('Investigator');await createForm(kind,`验收 ${kind} <script>literal</script>`);await ui.getByRole('button',{name:'保存为内部待审候选'}).click();await ui.getByRole('heading',{name:`验收 ${kind} <script>literal</script>`}).waitFor();assert.equal(await ui.getByRole('button',{name:'批准发布到公开资料库'}).count(),0);
  await role('Public');assert.equal(await ui.locator('.w19-create').count(),0);assert.equal(await ui.getByRole('heading',{name:`验收 ${kind} <script>literal</script>`}).count(),0);
  await role('LeadInvestigator');await ui.getByLabel('资料状态').selectOption('Candidate');await ui.getByRole('heading',{name:`验收 ${kind} <script>literal</script>`}).waitFor();
  const publish=ui.getByRole('button',{name:'批准发布到公开资料库'});await ui.getByLabel('审核理由').fill('Synthetic authorization acceptance');assert(await publish.isDisabled());
  const checks=ui.locator('.w19-review input');await checks.nth(0).check();await checks.nth(1).check();assert(await publish.isDisabled());await checks.nth(2).check();await publish.click();await empty().waitFor();
  await role('Public');await ui.getByRole('heading',{name:`验收 ${kind} <script>literal</script>`}).waitFor();assert.equal(await ui.locator('.w19-audit,.w19-review').count(),0);
 }
 console.log('PASS B01 three-kind UI create, unpublished isolation, explicit three-checkbox publication, external read-only');
 for(const detail of await ui.locator('.w19-card summary').all())await detail.click();assert.equal(await ui.locator('.w19-card img,.w19-card script').count(),0);assert.equal(await p.evaluate(()=>window.w191xss),undefined);
 assert(!(await ui.innerText()).includes('Synthetic authorization acceptance'));
 await ui.getByLabel('字面关键词').fill('<script>literal</script>');await ui.getByLabel('字面关键词').press('Enter');await ui.getByRole('heading',{name:/已人工批准发布.*3 条/}).waitFor();
 await p.setViewportSize({width:390,height:844});assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await p.screenshot({path:process.env.W191_TMP+'/mobile.png',fullPage:true});
 console.log('PASS B02 HTML literal escaping, external review-note stripping, keyboard submit, 390px no overflow');
 await role('LeadInvestigator');await ui.locator('.w19-card').first().waitFor();const first=ui.locator('.w19-card').first();const removed=await first.locator('h3').innerText();await first.getByLabel('审核理由').fill('Synthetic withdrawal acceptance');await first.getByRole('button',{name:'撤回并移出公开检索'}).click();await ui.getByRole('heading',{name:/已人工批准发布.*2 条/}).waitFor();await role('Public');await ui.getByRole('heading',{name:/已人工批准发布.*2 条/}).waitFor();assert.equal(await ui.getByRole('heading',{name:removed}).count(),0);
 console.log('PASS B03 withdrawal removes external list');
 await role('Investigator');await createForm('Method','迟到提交合成样本');let release, reached;const hit=new Promise(r=>reached=r), gate=new Promise(r=>release=r);let posts=0;
 await p.route('**/api/v1/knowledge/cards',async route=>{if(route.request().method()!=='POST')return route.continue();posts++;const response=await route.fetch();reached();await gate;await route.fulfill({response});});
 await ui.getByRole('button',{name:'保存为内部待审候选'}).evaluate(el=>{el.click();el.click();});await hit;assert.equal(posts,1);assert(await ui.getByRole('button',{name:'保存为内部待审候选'}).isDisabled());await role('Public');release();await delay(300);assert.equal(await ui.getByText(/迟到提交合成样本/).count(),0);assert.equal(await ui.locator('.w19-create').count(),0);await p.unroute('**/api/v1/knowledge/cards');
 console.log('PASS B04 real committed delayed POST, double-click single send, identity change no internal result leak');
 await role('Investigator');await createForm('Challenge','断连未知合成样本');let dropped=0;
 await p.route('**/api/v1/knowledge/cards',async route=>{if(route.request().method()!=='POST')return route.continue();await route.fetch();dropped++;await route.abort('failed');});
 await ui.getByRole('button',{name:'保存为内部待审候选'}).click();await ui.getByText('结果未确认，禁止自动重发。重新读取相应队列并核查审计后才解除锁定；整页刷新不代表原请求撤销。').waitFor();assert(await ui.getByRole('button',{name:'保存为内部待审候选'}).isDisabled());assert.equal(dropped,1);await p.unroute('**/api/v1/knowledge/cards');
 await ui.getByLabel('资料状态').selectOption('Candidate');await ui.getByRole('heading',{name:'断连未知合成样本'}).waitFor();await ui.locator('.w19-audit summary').click();await ui.getByRole('button',{name:'读取最近50条审计'}).click();await ui.getByText('已读取最近50条审计；这是操作记录，不证明来源真实性。').waitFor();await ui.getByLabel('我已核查服务器队列和审计，确认不会重复写入').check();await ui.getByRole('button',{name:'核查后解除锁定'}).click();assert(await ui.getByRole('button',{name:'保存为内部待审候选'}).isEnabled());
 console.log('PASS B05 server commit plus lost response is unknown, no retry, queue+audit reread and explicit unlock');
 const defects=[];
 await role('Public');await role('Investigator');await createForm('Case','422错误合成样本');await ui.locator('.w19-create input').first().fill('duplicate,duplicate');
 const rejected=p.waitForResponse(r=>r.url().endsWith('/api/v1/knowledge/cards')&&r.request().method()==='POST');await ui.getByRole('button',{name:'保存为内部待审候选'}).click();assert.equal((await rejected).status(),422);await delay(500);
 if(await ui.getByRole('alert').count()===0){defects.push('B07: real HTTP 422 duplicate tags response is cleared by automatic list refresh, no persistent error shown');console.log('FAIL '+defects.at(-1));}else console.log('PASS B07 rejected write remains visible');
 await role('Public');await role('Investigator');await createForm('Case','导航返回迟到合成样本');let navRelease,navReached;const navHit=new Promise(r=>navReached=r),navGate=new Promise(r=>navRelease=r);
 await p.route('**/api/v1/knowledge/cards',async route=>{if(route.request().method()!=='POST')return route.continue();const response=await route.fetch();navReached();await navGate;await route.fulfill({response});});
 await ui.getByRole('button',{name:'保存为内部待审候选'}).click();await navHit;
 await p.evaluate(()=>{location.hash='#/cases';window.dispatchEvent(new HashChangeEvent('hashchange'));location.hash='#/knowledge';window.dispatchEvent(new HashChangeEvent('hashchange'));});
 navRelease();await delay(600);await p.unroute('**/api/v1/knowledge/cards');
 const oldNotice=await ui.getByText(/以服务返回状态为准/).count();
 if(oldNotice){defects.push('B08: leave and return in same browser task lets prior committed POST update returned workspace notice/filter');console.log('FAIL '+defects.at(-1));}else console.log('PASS B08 same-task navigation return drops prior response');
 if(defects.length)process.exitCode=1;
 await p.screenshot({path:process.env.W191_TMP+'/unknown-reconciled.png',fullPage:true});assert.deepEqual(errors,[]);console.log('PASS B06 no uncaught browser errors; screenshots temporary');
 }finally{await b.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
