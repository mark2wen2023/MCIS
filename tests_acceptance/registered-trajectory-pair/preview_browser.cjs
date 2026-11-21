// Manual invocation only. Real Playwright, normal Chromium sandbox, no server/install.
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const SHA='9d4e3b8a990597e83769ea37292a500f10f4f3f693815d3a9c0e85a9d4b2b856';
async function main(){
 const [input,output,executable,...extra]=process.argv.slice(2);if(!input||!output||extra.length)throw Error('node preview_browser.cjs HTML NEW_RESULT_DIR [CHROMIUM_ABSOLUTE_PATH]');
 if(executable&&!path.isAbsolute(executable))throw Error('Absolute executable required');
 if(!fs.lstatSync(input).isFile())throw Error('Regular HTML required');const bytes=fs.readFileSync(input);
 assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),SHA);fs.mkdirSync(output);
 const dest=path.resolve(output,'preview.html');fs.writeFileSync(dest,bytes,{flag:'wx'});const url=pathToFileURL(dest).href;
 let browser,error;const result={htmlSha256:SHA,status:'failed',browser:null,checks:[],closed:false};
 try{
  const {chromium}=require('playwright');
  browser=await chromium.launch({headless:true,chromiumSandbox:true,timeout:30000,...(executable?{executablePath:executable}:{})});result.browser=browser.version();
  for(const width of [1440,390]){
   const c=await browser.newContext({viewport:{width,height:900},offline:true,serviceWorkers:'block'});
   try{
    const requests=[],errors=[];c.on('request',r=>requests.push(r.url()));const p=await c.newPage();p.setDefaultTimeout(8000);p.on('pageerror',e=>errors.push(e.message));
    await p.goto(url);assert.match(await p.title(),/登记轨迹/);assert.equal(await p.locator('[data-current]').count(),0);
    const slide=async i=>p.locator('#preview-slider').evaluate((e,v)=>{e.value=String(v);e.dispatchEvent(new Event('input',{bubbles:true}));},i);
    for(let i=0;i<12;i++)await slide(i%4);assert.equal(await p.locator('#preview-count').innerText(),'模拟查询次数：0');
    await slide(0);await p.locator('#registered-load').click();await p.waitForFunction(()=>document.querySelectorAll('[data-current]').length===2);
    assert.equal(await p.locator('#preview-count').innerText(),'模拟查询次数：1');
    const b=p.locator('#point-options button').nth(1);await b.focus();assert(await b.evaluate(e=>e===document.activeElement));await p.keyboard.press('Enter');
    assert.equal(await p.locator('#correction').innerText(),'12 s');assert.equal(await p.locator('#source-time').innerText(),'2026-02-01T12:00:08.000Z');assert.match(await p.locator('#quality').innerText(),/已存插值/);
    const before=await p.locator('#ref').innerText();await p.locator('[data-current]').nth(1).click();assert.equal(await p.locator('#ref').innerText(),before);
    await p.screenshot({path:path.join(output,`${width}-t20.png`),fullPage:true});
    await slide(1);assert.equal(await p.locator('#pointer').innerText(),'—');assert.equal(await p.locator('[data-current]').count(),0);await p.locator('#registered-load').click();await p.waitForFunction(()=>document.querySelectorAll('[data-current]').length===1);assert.match(await p.locator('#state-note').innerText(),/声明缺轨/);
    await slide(3);await p.locator('#registered-load').click();await p.waitForFunction(()=>document.getElementById('state-note').textContent.includes('无精确行'));assert.equal(await p.locator('[data-current]').count(),0);await p.screenshot({path:path.join(output,`${width}-gap.png`),fullPage:true});
    await slide(2);await p.locator('#registered-load').click();await p.waitForFunction(()=>document.querySelectorAll('[data-current]').length===2);await p.locator('#point-options button').first().click();assert.match(await p.locator('#warning').innerText(),/艏向未知/);
    await p.locator('#preview-late').click();await p.waitForFunction(()=>document.getElementById('preview-event').textContent.includes('被忽略'));assert.equal(await p.locator('[data-current]').count(),0);assert.equal(await p.locator('#registered-case').innerText(),'未选案件');assert.equal(await p.locator('#ref').innerText(),'—');
    if(width===390){await p.locator('#nav-toggle').click();assert.equal(await p.locator('#nav-toggle').getAttribute('aria-expanded'),'true');}
    assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));assert.deepEqual(errors,[]);assert.deepEqual(requests,[url]);
    result.checks.push({width,status:'passed',requests:requests.length});
   }finally{await c.close();}
  }
 }catch(e){error=e;result.failure=String(e.message);}
 finally{if(browser){try{await browser.close();result.closed=true;}catch(e){error=error||e;}}result.status=!error&&result.closed?'passed':'failed';fs.writeFileSync(path.join(output,'result.json'),JSON.stringify(result,null,2));}
 if(error)throw error;
}
main().catch(e=>{console.error(e.message);process.exitCode=1;});
