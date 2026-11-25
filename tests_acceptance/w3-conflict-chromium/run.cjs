'use strict';
const assert=require('node:assert/strict');
const {createHash}=require('node:crypto'),fs=require('node:fs'),path=require('node:path');
const {spawn,spawnSync}=require('node:child_process'),{createInterface}=require('node:readline'),{once}=require('node:events');
const {createServer}=require('node:http');
const fixed='bd02094a7cbb95d9ebb24a33e51bab2e695cccd7';
const root=path.resolve(process.env.MCIS_SOURCE_ROOT||'.');
const required=['MCIS_SOURCE_ROOT','MCIS_NODE_MODULES'];
for(const k of required)assert(process.env[k],k+' required');
const manifest=JSON.parse(fs.readFileSync(path.join(__dirname,'pins.json'),'utf8'));
assert.equal(manifest.base,fixed);
const pins=Object.entries(manifest.gitBlobPins);assert.equal(pins.length,192);
for(const [p,want] of pins){
 const file=path.resolve(root,p);
 assert(file.startsWith(root+path.sep)&&fs.realpathSync(file)===file,p);
 const data=fs.readFileSync(file);assert.equal(createHash('sha1').update('blob '+data.length+'\0').update(data).digest('hex'),want,p);
}
const bundle=require(path.join(path.resolve(process.env.MCIS_NODE_MODULES),'esbuild')).buildSync({
 entryPoints:[path.join(__dirname,'page.tsx')],bundle:true,write:false,jsx:'automatic',platform:'browser',format:'iife',
 alias:{'w3-fixed':path.join(root,'web/src/issueWorkspace')},nodePaths:[path.resolve(process.env.MCIS_NODE_MODULES)]
}).outputFiles[0].contents;
console.error(JSON.stringify({stage:'bundle',base:fixed,pins:pins.length,bytes:bundle.length}));
if(process.argv.includes('--build-only'))process.exit(0);

const html='<!doctype html><html lang="zh-CN"><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>W3 synthetic protected trial</title><div id="root"></div><script src="/app.js"></script></html>';
function scopedMessage(msg,scope){
 const common=['action','caseId','contextId','profile','requestId'];
 const fields={read:['issueId'],list:[],sources:[],save:['issueId','operationId','expectedRevision','entry']};
 if(!msg||typeof msg!=='object'||Array.isArray(msg)||!Object.hasOwn(fields,msg.action)||Buffer.byteLength(JSON.stringify(msg))>65536||
   msg.caseId!==scope.caseId||msg.contextId!==scope.contextId||msg.profile!==scope.profile)return false;
 const allowed=[...common,...fields[msg.action]];
 if(msg.action==='save'&&Object.hasOwn(msg,'sourcePins'))allowed.push('sourcePins');
 return Object.keys(msg).sort().join('|')===allowed.sort().join('|');
}
async function run(){
 for(const k of ['MCIS_CHROMIUM','MCIS_PLAYWRIGHT','MCIS_HOST_PYTHON','MCIS_BROWSER_EVIDENCE_DIR'])assert(process.env[k],k+' required');
 const evidence=path.resolve(process.env.MCIS_BROWSER_EVIDENCE_DIR);fs.mkdirSync(evidence,{recursive:false,mode:0o700});
 const exe=path.resolve(process.env.MCIS_CHROMIUM);
 const version=spawnSync(exe,['--version'],{encoding:'utf8',timeout:10000});
 if(version.status!==0||!/Chrom(?:e|ium)/.test(version.stdout)){
  const blocked={stage:'browser-executable',pass:false,status:version.status,detail:version.stderr?.trim()||version.error?.message};
  fs.writeFileSync(path.join(evidence,'exit.json'),JSON.stringify(blocked,null,2)+'\n',{mode:0o600});
  throw Error(JSON.stringify(blocked));
 }
 const {chromium}=require(path.resolve(process.env.MCIS_PLAYWRIGHT));
 let browser,child,listener,rl;const turns=[];const report={base:fixed,version:version.stdout.trim(),chromiumSandbox:true,stages:[],pass:false};
 function step(x){report.stages.push(x);console.error(JSON.stringify({stage:x}));}
 try{
  step('launch');
  browser=await chromium.launch({executablePath:exe,headless:true,chromiumSandbox:true,timeout:20000});
  step('launch-complete');report.runtimeVersion=browser.version();
  const clean=Object.fromEntries(Object.entries(process.env).filter(([k])=>!k.startsWith('MCIS_')&&!k.startsWith('PYTHON')));
  child=spawn(path.resolve(process.env.MCIS_HOST_PYTHON),['-B','-s',path.join(root,'tests_acceptance/w3-stale-draft-recovery/host.py')],{
   cwd:root,env:{...clean,MCIS_HOST_SERVICE:path.join(root,'service'),PYTHONDONTWRITEBYTECODE:'1'},stdio:['pipe','pipe','pipe']});
  let errors='';child.stderr.on('data',b=>errors+=b.toString());child.on('error',()=>{});
  rl=createInterface({input:child.stdout});
  const input=rl[Symbol.asyncIterator]();let busy=false;
  async function next(){
   let timer;
   try{return await Promise.race([input.next().then(x=>{assert(!x.done,'test host stopped');return JSON.parse(x.value)}),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('test host read timeout')),8000)})]);}
   finally{clearTimeout(timer)}
  }
  async function exchange(m){
   assert(!busy,'one host operation at a time');busy=true;
   try{child.stdin.write(JSON.stringify(m)+'\n');return await next()}finally{busy=false}
  }
  const origin=await new Promise((resolve,reject)=>{
   listener=createServer((req,res)=>{
    const own='127.0.0.1:'+listener.address().port;
    if(req.method!=='GET'||req.headers.host!==own||!['/','/app.js'].includes(req.url)){res.writeHead(404).end();return}
    res.writeHead(200,{'content-type':req.url==='/'?'text/html; charset=utf-8':'text/javascript; charset=utf-8',
     'cache-control':'no-store','content-security-policy':"default-src 'none'; script-src 'self'; connect-src 'none'; frame-ancestors 'none'; base-uri 'none'"});
    res.end(req.url==='/'?html:bundle);
   });
   listener.once('error',reject);listener.listen(0,'127.0.0.1',()=>resolve('http://127.0.0.1:'+listener.address().port));
  });
  let info=await next();const ids=info.ids;assert.equal(ids.length,2);
  let page,context;const unexpected=[];
  async function open(id,width=1440){
   if(context)await context.close();
   context=await browser.newContext({viewport:{width,height:950},serviceWorkers:'block'});
   await context.route('**/*',r=>{
    const url=r.request().url();if([origin+'/',origin+'/app.js'].includes(url))return r.continue();
    unexpected.push(url);return r.abort();
   });
   page=await context.newPage();page.on('pageerror',e=>unexpected.push(e.message));
   const target=page;
   const scoped=info.scope;
   await page.exposeBinding('w3Send',async({page:p,frame},message)=>{
    assert(p===target&&frame===target.mainFrame()&&frame.url()===origin+'/'&&scopedMessage(message,scoped),'invalid protected callback');
    const reply=await exchange(message);
    turns.push({action:message.action,caseId:message.caseId,issueId:message.issueId,expectedRevision:message.expectedRevision,
     against:message.entry?.againstJudgment,sourceIds:message.entry?.sourceIds,code:reply.code,status:reply.status,ok:reply.ok});
    return reply;
   });
   await page.addInitScript(x=>{window.w3Scope=x},{scope:scoped,id});
   await page.goto(origin+'/',{waitUntil:'load'});
   await page.getByRole('heading',{name:'问题研判记录 · 未审核'}).waitFor();
  }
  const button=n=>page.getByRole('button',{name:n,exact:true});
  const textarea=()=>page.getByRole('textbox',{name:'意见与理由'});
  const wait=async pred=>{const until=Date.now()+5000;while(Date.now()<until){if(await pred())return;await new Promise(r=>setTimeout(r,40))}throw Error('state wait timeout')};
  const status=async text=>{await page.getByRole('status').filter({hasText:text}).waitFor()};
  const contains=async text=>{await wait(async()=> (await page.locator('body').innerText()).includes(text))};
  const click=async n=>button(n).click({timeout:5000});
  const read=async()=>{await click('重新读取历史');await status('已重新读取未审核历史')};
  const source=async()=>{await click('读取当前来源');await page.getByRole('checkbox',{name:'引用 EV-001'}).waitFor();};
  const select=async()=>page.getByRole('combobox',{name:'记录类型'}).selectOption('verification');
  const save=()=>click('追加记录，不覆盖历史');
  const capture=async name=>page.screenshot({path:path.join(evidence,name+'.png'),timeout:6000,fullPage:true});
  step('card-a-conflict');
  await open(ids[0]);await read();await source();await page.getByRole('checkbox',{name:'引用 EV-001'}).check();
  await select();await textarea().fill('合成保留稿甲：仍针对原判断');
  assert.equal((await exchange({testControl:'advance-same-judgment'})).revision,2);
  await save();await status('本次追加冲突');assert.equal(turns.at(-1).status,409);assert.equal(turns.at(-1).code,'ISSUE_HOST_REJECTED');
  assert.equal(await textarea().inputValue(),'合成保留稿甲：仍针对原判断');assert(await textarea().isDisabled());
  assert.equal(await button('按原操作重试').count(),0);await capture('01-definite-conflict');
  await click('重读历史以恢复草稿');await status('草稿可继续编辑');
  assert(await button('追加记录，不覆盖历史').isDisabled());
  await source();assert(await button('追加记录，不覆盖历史').isDisabled());
  await page.getByRole('checkbox',{name:'引用 EV-001'}).check();await save();await status('试验服务已返回工作记录');
  assert.equal(turns.at(-1).expectedRevision,2);assert.equal(turns.at(-1).against,1);assert.deepEqual(turns.at(-1).sourceIds,['EV-001']);
  step('card-b-no-rebind');
  await open(ids[1]);await read();await select();await textarea().fill('合成保留稿乙：不重新绑定');
  assert.equal((await exchange({testControl:'advance-new-judgment'})).revision,2);
  await save();await status('本次追加冲突');assert.equal(turns.at(-1).status,409);
  await click('重读历史以恢复草稿');await contains('原草稿针对判断 #1；当前判断 #2');
  assert(await textarea().isDisabled());assert(await button('追加记录，不覆盖历史').isDisabled());await capture('02-no-rebind');
  await click('放弃未提交文字');await read();assert(!(await page.locator('body').innerText()).includes('合成保留稿乙'));
  step('store-reopen');
  await context.close();context=undefined;
  info=await exchange({testControl:'reopen'});
  await open(ids[0],390);await read();await contains('版本：3');await contains('合成保留稿甲');await contains('EV-001 · 当前');await capture('03-card-a-reopened');
  await open(ids[1],390);await read();await contains('版本：2');await contains('并行添加新的判断');
  const body=await page.locator('body').innerText();assert(!body.includes('合成保留稿甲')&&!body.includes('合成保留稿乙'));
  assert.deepEqual(await page.evaluate(()=>[localStorage.length,sessionStorage.length]),[0,0]);
  await capture('04-card-b-reopened');assert.deepEqual(unexpected,[]);assert.equal(errors,'');
  await context.close();report.pass=true;step('complete');
 }finally{
  report.receipts=turns;
  const errors=[];
  for(const [phase,clean] of [
   ['browser',async()=>{if(browser)await browser.close()}],
   ['listener',async()=>{if(listener?.listening)await new Promise(resolve=>listener.close(resolve))}],
   ['host',async()=>{if(!child||child.exitCode!==null||!child.pid)return;const exited=once(child,'exit');child.stdin.end();
    const force=setTimeout(()=>child.kill('SIGTERM'),4000);try{const [code]=await exited;assert.equal(code,0)}finally{clearTimeout(force)}rl?.close()}]
  ])try{await clean()}catch(e){errors.push([phase,e.message])}
  report.cleanupErrors=errors;if(errors.length)report.pass=false;
  fs.writeFileSync(path.join(evidence,'exit.json'),JSON.stringify(report,null,2)+'\n',{mode:0o600});
  assert.deepEqual(errors,[]);
 }
}
run().catch(e=>{console.error(e.message);process.exitCode=1});
