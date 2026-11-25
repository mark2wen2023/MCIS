'use strict';
const assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const {createInterface}=require('node:readline');
const {join}=require('node:path');
const [web,chromiumPath,installedPlaywright,caseId,outDir]=process.argv.slice(2);
const api='/api/v1/cases/'+caseId, rounds=api+'/consultation/rounds';
const input=createInterface({input:process.stdin})[Symbol.asyncIterator]();
async function main(){
 const pw=await import(pathToFileURL(installedPlaywright).href);
 const browser=await (pw.chromium??pw.default.chromium).launch({executablePath:chromiumPath,
    headless:true,chromiumSandbox:true,args:['--no-proxy-server']});
 try{
  const context=await browser.newContext({serviceWorkers:'block'});
  const offOrigin=[], writes=[];
  const origin=new URL(web).origin, wsHost=new URL(web).host;
  await context.route('**/*',async route=>{
    if(new URL(route.request().url()).origin===origin)await route.continue();
    else{offOrigin.push(route.request().url());await route.abort();}
  });
  if(typeof context.routeWebSocket!=='function')throw Error('Existing Playwright must support routeWebSocket');
  await context.routeWebSocket('**/*',route=>{
    const u=new URL(route.url());
    if(u.protocol==='ws:'&&u.host===wsHost)route.connectToServer();
    else{offOrigin.push(u.href);void route.close();}
  });
  const page=await context.newPage();page.setDefaultTimeout(15000);
  async function snap(name){
    if(!outDir)return;
    await page.screenshot({path:join(outDir,name+'.png'),fullPage:true});
  }
  page.on('request',r=>{if(['POST','PUT','PATCH','DELETE'].includes(r.method()))writes.push([r.method(),new URL(r.url()).pathname,r.postDataJSON()]);});
  const role=page.locator('select.role-select');
  async function enter(){
    const url=web+'/#/recs?case='+caseId;
    // Same-hash goto after the FastAPI/SQLite restart does not reload; the panel can stay on a hung pre-restart fetch.
    if(page.url().includes('#/recs?case='+caseId)) await page.reload({waitUntil:'domcontentloaded'});
    else await page.goto(url,{waitUntil:'domcontentloaded'});
    await role.waitFor();
    // Re-selecting the already-active role fires identity listeners and invalidates the
    // in-flight policy/rounds load without remounting, leaving the panel stuck on “正在读取”.
    if(await role.inputValue()!=='LeadInvestigator') await role.selectOption('LeadInvestigator');
    try {
      await page.getByText('新建征求意见轮次',{exact:true}).waitFor();
    } catch (err) {
      if(outDir){
        const fs=require('node:fs');
        await snap('diag-enter-failed');
        fs.writeFileSync(join(outDir,'diag-enter-failed.txt'), await page.locator('body').innerText());
      }
      throw err;
    }
  }
  async function commit(button, path, type, status){
    const response=page.waitForResponse(r=>new URL(r.url()).pathname===path&&r.request().method()===type);
    await button.click();
    const r=await response;
    assert.equal(r.status(),status,await r.text());
    return r.json();
  }
  async function service(path){
    const r=await context.request.get(web+path,{maxRedirects:0,headers:{'X-MCIS-Role':'LeadInvestigator','X-MCIS-Operator':'SyntheticAuditReader'}});
    assert.equal(r.status(),200);
    return r.json();
  }
  await enter();
  for(const n of [1,2]){
    const declared=n===2, start=writes.length, version='SYN-DEADLINE-'+n;
    await page.getByLabel('草案版本',{exact:true}).fill(version);
    await page.getByLabel('相关方编号',{exact:true}).fill('SYN-A');
    await page.getByLabel('相关方名称',{exact:true}).fill('虚构相关方');
    if(declared){
      await page.getByLabel('登记已商定期限',{exact:true}).check();
      await page.getByLabel('已商定期限（天）',{exact:true}).fill('45');
    }
    await page.getByRole('button',{name:'核对新建轮次',exact:true}).click();
    const review=page.getByRole('region',{name:'轮次操作确认'});
    await review.getByText(declared?'申报已商定期限：服务登记时间起 45 天':'默认期限：服务登记时间起 30 天',{exact:false}).waitFor();
    if(declared)await review.getByText('系统不核验是否已经商定',{exact:false}).waitFor();
    await review.getByText('不会向相关方发送消息',{exact:false}).waitFor();
    await snap(declared?'03-declared-45-preview':'01-default-30-preview');
    assert.equal(writes.length,start,'preview must not write');
    const opened=await commit(review.getByRole('button',{name:'确认登记',exact:true}),rounds,'POST',201);
    assert.deepEqual([opened.caseId,opened.roundNo,opened.draftVersion,opened.isAgreedDeadline],[caseId,n,version,declared]);
    assert.equal(Date.parse(opened.deadlineUtc)-Date.parse(opened.openedUtc),(declared?45:30)*86400000);
    const request=writes.at(-1)[2];
    assert.equal(request.isAgreedDeadline,declared);
    if(declared)assert.equal(request.days,45);else assert.equal(Object.hasOwn(request,'days'),false);
    await page.getByLabel('回复正文',{exact:true}).fill('仅登记合成答复，不发送。');
    await commit(page.locator('.w7-editor').getByRole('button',{name:'登记回复',exact:true}),rounds+'/'+n+'/replies','POST',201);
    await page.getByRole('button',{name:'核对关闭本轮',exact:true}).click();
    assert.equal(writes.length,start+2,'close preview must not write');
    const closed=await commit(review.getByRole('button',{name:'确认登记',exact:true}),rounds+'/'+n+':close','POST',200);
    assert.equal(closed.isClosed,true);
    assert.equal(writes.length,start+3);
    const closedNote=page.getByText('本轮已关闭，不能新增回复；待处理意见仍可作采纳决定。',{exact:true});
    await closedNote.waitFor();
    await closedNote.scrollIntoViewIfNeeded();
    await snap(declared?'04-declared-45-closed':'02-default-30-closed');
  }
  console.log('W7_RESTART_SQLITE');
  const answer=await input.next();assert.equal(answer.value,'READY');
  await enter();
  const select=page.getByRole('combobox',{name:'选择轮次'});
  await select.waitFor();
  for(const n of [1,2]){
    await select.selectOption(String(n));
    assert.match(await select.locator('option:checked').innerText(),new RegExp('SYN-DEADLINE-'+n+'.*已关闭'));
    const closedNote=page.getByText('本轮已关闭，不能新增回复；待处理意见仍可作采纳决定。',{exact:true});
    await closedNote.waitFor();
    await select.scrollIntoViewIfNeeded();
    await closedNote.scrollIntoViewIfNeeded();
    await snap(n===1?'05-reopen-round1-default30':'06-reopen-round2-declared45');
  }
  const persisted=await service(rounds);
  assert.deepEqual(persisted.map(x=>[x.roundNo,x.isClosed,x.isAgreedDeadline]),[[1,true,false],[2,true,true]]);
  assert.deepEqual(persisted.map(x=>(Date.parse(x.deadlineUtc)-Date.parse(x.openedUtc))/86400000),[30,45]);
  const audit=await service(api+'/audit?category=Consultation');
  assert.deepEqual(audit.map(x=>x.action),['consultation.open','consultation.reply','consultation.close','consultation.open','consultation.reply','consultation.close']);
  const open=audit.filter(x=>x.action==='consultation.open').map(x=>x.after);
  assert.match(open[0],/默认 30 天/);assert.match(open[1],/标记商定 45 天/);
  assert.equal((await service(api+'/audit:verify')).valid,true);
  assert.deepEqual(writes.map(x=>x.slice(0,2)),[rounds,rounds+'/1/replies',rounds+'/1:close',rounds,rounds+'/2/replies',rounds+'/2:close'].map(p=>['POST',p]));
  assert.deepEqual(offOrigin,[]);
 }finally{await browser.close();}
 console.log('W7 sandboxed Chromium PASS: two registered/closed rounds, default30 vs declared45, reopened UI and real audit.');
}
main().then(()=>process.exit(0),err=>{console.error(err);process.exit(1);});
