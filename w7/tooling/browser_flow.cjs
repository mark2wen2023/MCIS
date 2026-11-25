// Real Chrome (normal sandbox) -> real Vite -> real FastAPI. Observe requests; do not mock routes.
'use strict';
const fs=require('node:fs');
const path=require('node:path');
const {execSync}=require('node:child_process');

const [pwPath,exe,front,shotsDir,logPath]=process.argv.slice(2);
const {chromium}=require(pwPath);
const CASE='SYN-W7-CREATE-BODY';
const BODY0='  第一段：整改建议，保留段落和空格。\n\n第二段：核验措施。  ';
const TITLE0='合成建议 0';
const TITLE1='合成建议 1';
const ADDRESSEE='合成对象';
const DUE='2099-06-30';

fs.mkdirSync(shotsDir,{recursive:true});
const httpLog=[], reqLog=[];
const result={ok:false,blocker:null,browser:null,sandbox:null,created:[],reload:[],emptyAfterReload:null,writes:[],external:[],shots:[]};

function fail(msg){result.blocker=msg;throw new Error(msg);}
async function shot(page,name){const p=path.join(shotsDir,name);await page.screenshot({path:p,fullPage:false});result.shots.push(p);}
function hostOf(url){try{return new URL(url).hostname;}catch{return '';}}
function isInternal(url){
  if(!url||url.startsWith('data:')||url.startsWith('blob:')||url.startsWith('about:')||url.startsWith('chrome')) return true;
  const h=hostOf(url);
  return h==='127.0.0.1'||h==='localhost';
}

async function openCreate(page){
  await page.getByRole('button',{name:'＋ 新建安全建议'}).click();
  await page.getByText('建议正文（可选）',{exact:true}).waitFor({timeout:10000});
}
async function fillCommon(page,title){
  await page.locator('input[placeholder="建议标题"]').fill(title);
  await page.locator('input[placeholder="建议对象"]').fill(ADDRESSEE);
  await page.locator('input[type="date"]').fill(DUE);
}
async function saveAndWait(page,title){
  const wait=page.waitForResponse(r=>{try{const u=new URL(r.url());return u.pathname.endsWith('/recommendations')&&r.request().method()==='POST';}catch{return false;}},{timeout:20000});
  await page.getByRole('button',{name:'保存',exact:true}).click();
  const res=await wait;
  if(!res.ok()) fail(`首个阻塞：保存建议 HTTP ${res.status()} ${await res.text()}`);
  const body=await res.json();
  await page.getByText('已新建安全建议（草拟）',{exact:false}).waitFor({timeout:10000}).catch(()=>{});
  await page.getByText(title,{exact:true}).first().waitFor({timeout:10000});
  return body;
}
async function readContent(page,expectBody,expectEmptyLabel){
  const btn=page.getByRole('button',{name:'读取正文与登记回复',exact:true});
  if(await btn.count()) await btn.click();
  else {
    const reopen=page.getByRole('button',{name:'重新读取完整内容',exact:true});
    if(await reopen.count()) await reopen.click();
    else fail('首个阻塞：找不到「读取正文与登记回复」');
  }
  await page.getByRole('heading',{name:'正文',exact:true}).waitFor({timeout:15000});
  const statusText=await page.getByText('服务端状态',{exact:true}).locator('xpath=following-sibling::dd[1]').innerText();
  if(!statusText.includes('草拟')) fail(`首个阻塞：完整内容核查状态不是草拟，而是「${statusText}」`);
  const box=page.locator('div.w74-text').first();
  const text=await box.innerText();
  if(expectEmptyLabel){
    if(!text.includes('未记录正文')) fail(`首个阻塞：空正文未显示兼容说明，实际「${text}」`);
  }else{
    if(text!==expectBody && text!==expectBody.trim()){
      // whitespace in HTML may collapse; compare exact first, then fail with both
      const raw=await box.evaluate(el=>el.innerText);
      if(raw!==expectBody) fail(`首个阻塞：正文与输入不符。页面=${JSON.stringify(raw)} 期望=${JSON.stringify(expectBody)}`);
    }
  }
  const issued=await page.getByText('已发布',{exact:false}).count();
  return {statusText,text,issuedVisibleHint:issued};
}
async function readAudit(page){
  await page.getByRole('button',{name:/读取审计摘要/}).click();
  await page.getByText(/返回 \d+ 条摘要/,{exact:false}).waitFor({timeout:15000});
  const items=await page.locator('div.w74-audit ol li').allInnerTexts();
  return items;
}

(async()=>{
  const browser=await chromium.launch({executablePath:exe,headless:true,chromiumSandbox:true});
  result.browser=browser.version();
  try{
    const ps=execSync('ps -eo args=').toString();
    const chromeLines=ps.split('\n').filter(l=>/google-chrome|Chrome/.test(l));
    result.sandbox={noSandboxFlag:chromeLines.some(l=>/--no-sandbox|--disable-setuid-sandbox/.test(l)),chromeProcCount:chromeLines.length,browser:result.browser};
    if(result.sandbox.noSandboxFlag) fail('首个阻塞：Chrome 带有 --no-sandbox');

    const ctx=await browser.newContext({viewport:{width:1440,height:900}});
    const page=await ctx.newPage();
    page.on('request',req=>{
      const rec={utc:new Date().toISOString(),method:req.method(),url:req.url(),resource:req.resourceType()};
      reqLog.push(rec);
      if(!isInternal(req.url())) result.external.push(rec);
    });
    page.on('response',async res=>{
      const url=res.url();
      if(!url.includes('/api/')) return;
      const rec={utc:new Date().toISOString(),status:res.status(),method:res.request().method(),url};
      try{
        const ct=res.headers()['content-type']||'';
        if(ct.includes('json')) rec.body=await res.json();
      }catch(e){rec.bodyError=String(e.message||e);}
      httpLog.push(rec);
    });

    await page.goto(front+'/#/recs?case='+CASE,{waitUntil:'domcontentloaded'});
    await page.locator('select.role-select').selectOption('LeadInvestigator');
    await page.getByText('安全建议跟踪',{exact:false}).waitFor({timeout:30000});
    await page.getByText(CASE,{exact:false}).first().waitFor({timeout:10000}).catch(()=>{});
    await shot(page,'01-recs-empty.png');

    if(result.external.length) fail('首个阻塞：出现非本机请求 '+JSON.stringify(result.external[0]));

    // --- rec 0: two Chinese paragraphs ---
    await openCreate(page);
    await fillCommon(page,TITLE0);
    await page.locator('textarea').fill(BODY0);
    const typed=await page.locator('textarea').inputValue();
    if(typed!==BODY0) fail('首个阻塞：文本框未保留两段中文与空白，实际='+JSON.stringify(typed));
    await shot(page,'02-create-form-filled.png');
    const created0=await saveAndWait(page,TITLE0);
    if(created0.status!=='Draft') fail('首个阻塞：创建响应 status='+created0.status);
    if(created0.body!==BODY0) fail('首个阻塞：创建响应正文不符 '+JSON.stringify(created0.body));
    result.created.push(created0);
    await page.getByText('草拟',{exact:true}).first().waitFor();
    await shot(page,'03-saved-draft-card.png');
    const read0=await readContent(page,BODY0,false);
    result.created[0].ui=read0;
    await shot(page,'04-read-body.png');
    const audit0=await readAudit(page);
    result.created[0].auditUi=audit0;
    await shot(page,'05-audit-create-only.png');
    if(!audit0.some(t=>/safetyrec\.create|新建安全建议/.test(t))) fail('首个阻塞：审计摘要未见 safetyrec.create / 新建安全建议');
    if(audit0.some(t=>/safetyrec\.(transition|progress|update)|已发布|签发|发送/.test(t))) fail('首个阻塞：审计出现签发/状态变更：'+JSON.stringify(audit0));

    // --- reload, confirm body + draft ---
    await page.reload({waitUntil:'domcontentloaded'});
    await page.locator('select.role-select').selectOption('LeadInvestigator');
    await page.getByText(TITLE0,{exact:true}).first().waitFor({timeout:20000});
    await page.getByText(TITLE0,{exact:true}).first().click();
    await page.getByText('草拟',{exact:true}).first().waitFor();
    const read0b=await readContent(page,BODY0,false);
    result.reload.push({id:created0.id,ui:read0b});
    await shot(page,'06-after-reload-body.png');

    // --- rec 1: empty body ---
    await openCreate(page);
    await fillCommon(page,TITLE1);
    const emptyVal=await page.locator('textarea').inputValue();
    if(emptyVal!=='') fail('首个阻塞：空正文文本框初值不是空字符串');
    await shot(page,'07-empty-body-form.png');
    const created1=await saveAndWait(page,TITLE1);
    if(created1.status!=='Draft') fail('首个阻塞：空正文创建 status='+created1.status);
    if(created1.body!=='') fail('首个阻塞：空正文创建响应 body='+JSON.stringify(created1.body));
    result.created.push(created1);
    await page.getByText(TITLE1,{exact:true}).first().click();
    const read1=await readContent(page,'',true);
    result.created[1].ui=read1;
    await shot(page,'08-empty-body-read.png');

    await page.reload({waitUntil:'domcontentloaded'});
    await page.locator('select.role-select').selectOption('LeadInvestigator');
    await page.getByText(TITLE1,{exact:true}).first().waitFor({timeout:20000});
    await page.getByText(TITLE1,{exact:true}).first().click();
    await page.getByText('草拟',{exact:true}).first().waitFor();
    const read1b=await readContent(page,'',true);
    result.emptyAfterReload=read1b;
    await shot(page,'09-empty-after-reload.png');
    // also reconfirm first rec still there
    await page.getByText(TITLE0,{exact:true}).first().click();
    const read0c=await readContent(page,BODY0,false);
    result.reload.push({id:created0.id,secondLook:read0c});
    await shot(page,'10-first-rec-still-present.png');

    const posts=httpLog.filter(h=>h.method==='POST'||h.method==='PUT'||h.method==='PATCH'||h.method==='DELETE');
    result.writes=posts.map(h=>({method:h.method,status:h.status,url:h.url,id:h.body&&h.body.id,statusField:h.body&&h.body.status,body:h.body&&h.body.body,replayed:h.body&&h.body.replayed}));
    const recCreates=posts.filter(h=>/\/recommendations$/.test(new URL(h.url).pathname));
    const otherWrites=posts.filter(h=>!/\/recommendations$/.test(new URL(h.url).pathname));
    if(recCreates.length!==2) fail(`首个阻塞：新建写入次数为 ${recCreates.length}，期望 2`);
    if(otherWrites.length) fail('首个阻塞：出现非新建写入 '+JSON.stringify(otherWrites));
    if(posts.some(h=>/transition|responses|issue|send|dispatch|mail/.test(h.url))) fail('首个阻塞：出现签发/发送/状态转换请求');
    if(result.external.length) fail('首个阻塞：出现非本机请求');
    if(result.created.length!==2) fail('首个阻塞：未得到两条创建回执');
    if(!(result.created[0].status==='Draft'&&result.created[1].status==='Draft')) fail('首个阻塞：响应不是 Draft');
    result.ok=true;
  }finally{
    await browser.close().catch(()=>{});
    fs.writeFileSync(logPath,JSON.stringify({result,httpLog,reqLog},null,2));
    const summary={ok:result.ok,blocker:result.blocker,browser:result.browser,sandbox:result.sandbox,
      created:result.created.map(c=>({id:c.id,status:c.status,body:c.body,title:c.title})),
      writes:result.writes,external:result.external,shots:result.shots};
    console.log(JSON.stringify(summary,null,2));
  }
})().then(()=>process.exit(result.ok?0:1),e=>{
  result.blocker=result.blocker||('首个阻塞：脚本异常 '+e.stack);
  try{fs.writeFileSync(logPath,JSON.stringify({result,httpLog,reqLog,error:String(e.stack||e)},null,2));}catch{}
  console.error(result.blocker);
  process.exit(1);
});
