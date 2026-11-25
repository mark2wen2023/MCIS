// Real Chrome (normal sandbox) -> real Vite proxy -> real FastAPI. No route mocks, no --no-sandbox.
'use strict';
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');

const [pwPath, exe, front, packagePath, expectedPath, shotsDir, logPath] = process.argv.slice(2);
const expected=JSON.parse(fs.readFileSync(expectedPath,'utf8'));
const {chromium}=require(pwPath);
fs.mkdirSync(shotsDir,{recursive:true});
const httpLog=[];
const result={ok:false,blocker:null,browser:null,sandbox:null,preview:null,receipt:null,timeline:null,commitCount:0,shots:[]};

function shot(page,name){const p=path.join(shotsDir,name);return page.screenshot({path:p,fullPage:true}).then(()=>{result.shots.push(p);});}
function fail(msg){result.blocker=msg;throw new Error(msg);}

(async()=>{
  const browser=await chromium.launch({executablePath:exe,headless:true,chromiumSandbox:true});
  result.browser=browser.version();
  try{
    const ctx=await browser.newContext({viewport:{width:1440,height:900}});
    const page=await ctx.newPage();
    page.on('response',async (res)=>{
      const url=res.url();
      if(!url.includes('/api/'))return;
      const rec={utc:new Date().toISOString(),status:res.status(),method:res.request().method(),url,headers:{}};
      try{
        const ct=res.headers()['content-type']||'';
        if(ct.includes('json')) rec.body=await res.json();
      }catch(e){rec.bodyError=String(e.message||e);}
      httpLog.push(rec);
    });
    // sandbox check
    const {execSync}=require('node:child_process');
    const ps=execSync('ps -eo args=').toString();
    const chromeLines=ps.split('\n').filter(l=>/google-chrome|Chrome/.test(l));
    result.sandbox={noSandboxFlag:chromeLines.some(l=>/--no-sandbox|--disable-setuid-sandbox/.test(l)),chromeProcCount:chromeLines.length,browser:result.browser};
    assert.equal(result.sandbox.noSandboxFlag,false,'chrome launched with sandbox disabled');

    await page.goto(front+'/#/lobby',{waitUntil:'domcontentloaded'});
    await page.getByRole('heading',{name:'案件大厅'}).waitFor({timeout:30000});
    await page.locator('select.role-select').selectOption('LeadInvestigator');
    await page.getByRole('heading',{name:'案件大厅'}).waitFor();
    await shot(page,'01-lobby-lead.png');

    const openBtn=page.getByRole('button',{name:'选择基础资料包',exact:true});
    await openBtn.click();
    await page.getByLabel('基础资料 .mcase 文件',{exact:true}).setInputFiles(packagePath);
    await page.getByText(/字节/).first().waitFor();
    await shot(page,'02-file-selected.png');

    const previewResp=page.waitForResponse(r=>r.url().includes('/packages/intakes:preview')&&r.request().method()==='POST',{timeout:30000});
    await page.getByRole('button',{name:'上传并预览基础资料',exact:true}).click();
    const pvRes=await previewResp;
    if(!pvRes.ok()) fail(`首个阻塞：预检 HTTP ${pvRes.status()} ${await pvRes.text()}`);
    const preview=await pvRes.json();
    result.preview=preview;
    await page.getByText('服务端受限恢复范围预览',{exact:true}).waitFor({timeout:15000});
    await shot(page,'03-preview.png');
    if(preview.packageVersion!==expected.packageVersion) fail(`首个阻塞：预检 packageVersion=${preview.packageVersion}，期望 ${expected.packageVersion}`);
    if(preview.caseId!==expected.caseId) fail(`首个阻塞：预检 caseId=${preview.caseId}，期望 ${expected.caseId}`);
    if(preview.sourceSha256!==expected.sourceSha256) fail(`首个阻塞：预检 sourceSha256=${preview.sourceSha256}，期望 ${expected.sourceSha256}`);
    const ddAfter=async (label)=>page.getByText(label,{exact:true}).locator('xpath=following-sibling::dd[1]').innerText();
    const uiSha=await page.getByText('包 SHA-256',{exact:true}).locator('xpath=following-sibling::dd[1]').innerText();
    const uiVer=await ddAfter('案件包版本');
    const uiCase=await ddAfter('案号');
    result.previewUi={sha:uiSha,version:uiVer,caseId:uiCase};
    if(uiSha!==expected.sourceSha256||uiVer!==expected.packageVersion||uiCase!==expected.caseId)
      fail(`首个阻塞：预检页面展示不符 sha=${uiSha} ver=${uiVer} case=${uiCase}`);

    const commit=page.getByRole('button',{name:'确认首次导入',exact:true});
    if(await commit.isEnabled()) fail('首个阻塞：未勾选确认时导入按钮已可点');
    await page.getByRole('checkbox',{name:/我已核对案号/}).check();
    await shot(page,'04-confirmed.png');
    if(!(await commit.isEnabled())) fail('首个阻塞：勾选确认后导入按钮仍不可用');

    const commitWait=page.waitForResponse(r=>r.url().includes('/packages/intakes:commit')&&r.request().method()==='POST',{timeout:30000});
    await commit.click();
    const cmRes=await commitWait;
    if(!cmRes.ok()) fail(`首个阻塞：导入 HTTP ${cmRes.status()} ${await cmRes.text()}`);
    const receipt=await cmRes.json();
    result.receipt=receipt;
    await page.getByText('已核验服务端导入回执',{exact:true}).waitFor({timeout:15000});
    await shot(page,'05-receipt.png');
    if(receipt.packageVersion!==expected.packageVersion) fail(`首个阻塞：回执 packageVersion=${receipt.packageVersion}`);
    if(receipt.caseId!==expected.caseId) fail(`首个阻塞：回执 caseId=${receipt.caseId}`);
    if(receipt.sourceSha256!==expected.sourceSha256) fail(`首个阻塞：回执 sourceSha256=${receipt.sourceSha256}`);
    const recSha=await page.locator('div[role="status"] code').innerText();
    const recVerText=await page.locator('div[role="status"]').innerText();
    result.receiptUi={sha:recSha,text:recVerText};
    if(recSha!==expected.sourceSha256) fail(`首个阻塞：回执页 SHA 不符 ${recSha}`);
    if(!recVerText.includes(expected.packageVersion)||!recVerText.includes(expected.caseId))
      fail('首个阻塞：回执页未同时展示版本与案号');
    if(await commit.isEnabled()) fail('首个阻塞：导入后确认按钮仍可再次提交');

    const tlWait=page.waitForResponse(r=>r.url().includes('/timeline')&&r.request().method()==='GET',{timeout:30000});
    await page.getByRole('link',{name:'进入导入案件',exact:true}).click();
    const tlRes=await tlWait.catch(()=>null);
    // page may request timeline after evidence page loads
    await page.waitForURL(/case=CASE-INTAKE/,{timeout:15000});
    await page.getByText('事件时间线',{exact:false}).waitFor({timeout:20000});
    // wait until timeline GET has arrived
    let tlBody=null;
    if(tlRes&&tlRes.ok()) tlBody=await tlRes.json();
    else {
      const later=httpLog.find(h=>h.method==='GET'&&h.url.includes('/timeline')&&h.status===200);
      if(later) tlBody=later.body;
      else {
        // wait a bit more
        const r2=await page.waitForResponse(r=>r.url().includes('/cases/CASE-INTAKE/timeline')&&r.ok(),{timeout:20000});
        tlBody=await r2.json();
      }
    }
    result.timeline=tlBody;
    const titles=(tlBody?.events||[]).map(e=>e.title).sort();
    const want=expected.events.map(e=>e.title).sort();
    if(JSON.stringify(titles)!==JSON.stringify(want))
      fail(`首个阻塞：时间线事件不符 got=${JSON.stringify(titles)} want=${JSON.stringify(want)}`);
    // visual: labels or tooltips
    await page.waitForTimeout(800);
    await shot(page,'06-timeline.png');
    const panel=page.locator('text=事件时间线 · 冲突标注 · 两船距离').locator('xpath=ancestor::*[contains(@class,"panel") or self::section][1]');
    // hover chart points if possible
    const canvas=page.locator('canvas').first();
    if(await canvas.count()){
      const box=await canvas.boundingBox();
      if(box){
        // events at t=1 and t=2 of max~60; left padding ~78 of  chart width
        const plotLeft=box.x+78, plotW=box.width-78-44;
        const y=box.y+box.height/2;
        for(const t of [1,2]){
          await page.mouse.move(plotLeft+(t/60)*plotW, y);
          await page.waitForTimeout(200);
        }
        await shot(page,'07-timeline-hover.png');
      }
    }
    const commitPosts=httpLog.filter(h=>h.method==='POST'&&h.url.includes('/packages/intakes:commit'));
    result.commitCount=commitPosts.length;
    if(result.commitCount!==1) fail(`首个阻塞：导入次数为 ${result.commitCount}，期望仅一次`);
    result.ok=true;
  }finally{
    await browser.close().catch(()=>{});
    fs.writeFileSync(logPath,JSON.stringify({result,httpLog},null,2));
    console.log(JSON.stringify({ok:result.ok,blocker:result.blocker,browser:result.browser,sandbox:result.sandbox,commitCount:result.commitCount,preview:result.preview&&{caseId:result.preview.caseId,packageVersion:result.preview.packageVersion,sourceSha256:result.preview.sourceSha256},receipt:result.receipt&&{caseId:result.receipt.caseId,packageVersion:result.receipt.packageVersion,sourceSha256:result.receipt.sourceSha256},timelineTitles:(result.timeline&&result.timeline.events||[]).map(e=>e.title),shots:result.shots},null,2));
  }
})().then(()=>process.exit(result.ok?0:1),e=>{
  result.blocker=result.blocker||('首个阻塞：脚本异常 '+e.stack);
  try{fs.writeFileSync(logPath,JSON.stringify({result,httpLog,error:String(e.stack||e)},null,2));}catch{}
  console.error(result.blocker);
  process.exit(1);
});
