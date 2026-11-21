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
   const c=await browser.newContext({viewport:{width,height:900},hasTouch:false,isMobile:false,offline:true,serviceWorkers:'block'});
   try{
    const requests=[],errors=[];c.on('request',r=>requests.push(r.url()));const p=await c.newPage();p.setDefaultTimeout(8000);p.on('pageerror',e=>errors.push(e.message));
    await p.goto(url);assert.match(await p.title(),/登记轨迹/);assert.equal(await p.locator('[data-current]').count(),0);
    // Real input devices only: evaluate below reads focus, never sets value/events.
    const tabTo=async selector=>{
     for(let i=0;i<100;i++){
      if(await p.locator(selector).evaluate(e=>e===document.activeElement))return;
      await p.keyboard.press('Tab');
     }
     throw Error('Keyboard focus not reachable: '+selector);
    };
    const slide=async i=>{
     await tabTo('#preview-slider');await p.keyboard.press('Home');
     for(let n=0;n<i;n++)await p.keyboard.press('ArrowRight');
     assert.equal(await p.locator('#preview-slider').inputValue(),String(i));
    };
    const count=async()=>Number((await p.locator('#preview-count').innerText()).split('：')[1]);
    const submit=async()=>{
     const n=await count();await tabTo('#registered-load');await p.keyboard.press('Enter');
     assert.equal(await count(),n+1);
    };
    const cleared=async()=>{
     assert.equal(await p.locator('[data-current]').count(),0);
     for(const id of ['record-id','raw-time','source-time','correction','aligned-time','pointer','ref','clock'])assert.equal(await p.locator('#'+id).innerText(),'—',id);
     assert.equal(await p.locator('#file').innerText(),'未选择证据');
     assert.equal(await p.locator('#quality').innerText(),'未选择');
     assert.equal(await p.locator('#source-a').isDisabled(),true);assert.equal(await p.locator('#source-b').isDisabled(),true);
    };
    await slide(0);await p.locator('#preview-slider').scrollIntoViewIfNeeded();
    const box=await p.locator('#preview-slider').boundingBox();assert(box&&box.width>20);
    await p.mouse.move(box.x+8,box.y+box.height/2);await p.mouse.down();
    await p.mouse.move(box.x+box.width-8,box.y+box.height/2,{steps:20});await p.mouse.up();
    assert.equal(await p.locator('#preview-slider').inputValue(),'3');assert.equal(await count(),0);await cleared();
    await slide(0);await p.keyboard.press('ArrowRight');await p.keyboard.press('ArrowLeft');
    assert.equal(await p.locator('#preview-slider').inputValue(),'0');assert.equal(await count(),0);
    await submit();await p.waitForFunction(()=>document.querySelectorAll('[data-current]').length===2);
    await tabTo('#source-b');await p.keyboard.press('Enter');
    assert.equal(await p.locator('#correction').innerText(),'12 s');assert.equal(await p.locator('#source-time').innerText(),'2026-02-01T12:00:08.000Z');
    assert.equal(await p.locator('#aligned-time').innerText(),'2026-02-01T12:00:20.000Z');assert.equal(await p.locator('#pointer').innerText(),'/points/2');
    assert.match(await p.locator('#quality').innerText(),/已存插值/);
    const before=await p.locator('#ref').innerText();assert.match(before,/登记摘要 .*原文字节 SHA-256/);
    await p.locator('[data-current]').nth(1).click();assert.equal(await p.locator('#ref').innerText(),before);assert.equal(await p.locator('#pointer').innerText(),'/points/2');assert.equal(await count(),1);
    await p.screenshot({path:path.join(output,`${width}-t20.png`),fullPage:true});
    await slide(1);await cleared();assert.equal(await count(),1);await submit();
    await p.waitForFunction(()=>document.querySelectorAll('[data-current]').length===1);
    await p.locator('#source-a').click();assert.equal(await p.locator('#pointer').innerText(),'/sampling/missingIntervals/0');assert.equal(await p.locator('#quality').innerText(),'声明缺轨');assert.equal(await p.locator('#source-time').innerText(),'—');
    await p.locator('#source-b').click();assert.equal(await p.locator('#pointer').innerText(),'/points/9');assert.equal(await p.locator('#aligned-time').innerText(),'2026-02-01T12:01:20.000Z');
    await slide(3);await cleared();assert.equal(await count(),2);await submit();
    await p.waitForFunction(()=>document.getElementById('state-note').textContent.includes('无精确行'));assert.equal(await p.locator('[data-current]').count(),0);
    assert.equal(await p.locator('#source-b').isDisabled(),true);assert.equal(await p.locator('#point-options button').nth(1).isDisabled(),true);
    await p.locator('#source-a').click();assert.equal(await p.locator('#pointer').innerText(),'/sampling/missingIntervals/1');assert.equal(await p.locator('#quality').innerText(),'声明缺轨');assert.equal(await p.locator('#aligned-time').innerText(),'2026-02-01T12:02:04.250Z');
    await p.screenshot({path:path.join(output,`${width}-gap.png`),fullPage:true});
    await slide(2);await cleared();await submit();await p.waitForFunction(()=>document.querySelectorAll('[data-current]').length===2);
    await p.locator('#point-options button').first().click();assert.equal(await p.locator('#pointer').innerText(),'/points/7');assert.match(await p.locator('#warning').innerText(),/艏向未知/);
    assert.equal(await count(),4);await p.locator('#preview-late').click();
    await p.waitForFunction(()=>document.getElementById('preview-event').textContent.includes('被忽略'));
    await cleared();assert.equal(await count(),5);assert.equal(await p.locator('#registered-case').innerText(),'未选案件');
    if(width===390){await p.locator('#nav-toggle').click();assert.equal(await p.locator('#nav-toggle').getAttribute('aria-expanded'),'true');}
    assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));assert.deepEqual(errors,[]);assert.deepEqual(requests,[url]);
    result.checks.push({width,height:900,hasTouch:false,isMobile:false,input:'mouse drag; Tab/Home/Arrow/Enter',lateScenario:'synthetic A to no case; not A/B or revocation',status:'passed',requests:requests.length});
   }finally{await c.close();}
  }
 }catch(e){error=e;result.failure=String(e.message);}
 finally{if(browser){try{await browser.close();result.closed=true;}catch(e){error=error||e;}}result.status=!error&&result.closed?'passed':'failed';fs.writeFileSync(path.join(output,'result.json'),JSON.stringify(result,null,2));}
 if(error)throw error;
}
main().catch(e=>{console.error(e.message);process.exitCode=1;});
