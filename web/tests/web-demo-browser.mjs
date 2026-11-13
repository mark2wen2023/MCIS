/** Opt-in same-machine real-browser acceptance. Never accepts an external URL. */
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { createRequire } from 'node:module';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { mkdir, mkdtemp } from 'node:fs/promises';
import assert from 'node:assert/strict';

const root=resolve(dirname(fileURLToPath(import.meta.url)),'../..');
const python=process.env.MCIS_DEMO_PYTHON;
const core=process.env.MCIS_PREFLIGHT_REAL_CORE;
if(!python || !core)throw Error('Set MCIS_DEMO_PYTHON and MCIS_PREFLIGHT_REAL_CORE to trusted local executables; no mock fallback.');
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.MCIS_PLAYWRIGHT_MODULE || 'playwright');
const artifactRoot=resolve(process.env.MCIS_BROWSER_ARTIFACTS || '/tmp/mcis-browser-acceptance');
await mkdir(artifactRoot,{recursive:true});
const artifacts=await mkdtemp(resolve(artifactRoot,'run-'));
let browser,child;
try {
 // Launch the browser first: an unavailable sandbox must not start a demo server.
 browser=await chromium.launch({headless:true,chromiumSandbox:true,
   ...(process.env.MCIS_CHROMIUM_EXECUTABLE?{executablePath:process.env.MCIS_CHROMIUM_EXECUTABLE}:{})});
 const context=await browser.newContext({viewport:{width:1280,height:900},serviceWorkers:'block'});
 const page=await context.newPage();
 child=spawn(python,['-m','mcis_service.identity.web_demo','--core-command',core],{
   cwd:root,env:{...process.env,PYTHONPATH:resolve(root,'service')},stdio:['ignore','pipe','pipe']});
 // Deliberately do not print stderr or page bodies containing the temporary CSRF nonce.
 const origin=await new Promise((ok,fail)=>{
   const timer=setTimeout(()=>fail(Error('Local demo startup timeout')),10000);let buffer='';
   child.once('error',()=>{clearTimeout(timer);fail(Error('Local demo process unavailable'));});
   child.once('exit',()=>{clearTimeout(timer);fail(Error('Local demo exited before startup'));});
   child.stdout.on('data',data=>{
     buffer+=data.toString();if(buffer.length>4096){clearTimeout(timer);fail(Error('Invalid demo startup output'));return;}
     const first=buffer.split('\n')[0];if(!buffer.includes('\n'))return;
     clearTimeout(timer);
     if(!/^http:\/\/127\.0\.0\.1:[1-9][0-9]{0,4}$/.test(first)||Number(new URL(first).port)>65535)fail(Error('Non-loopback demo origin rejected'));
     else ok(first);
   });
   child.stderr.resume();
 });
 const observed=[],violations=[];
 await context.route('**/*',async route=>{
   const request=route.request(),url=new URL(request.url());
   if(url.origin!==origin || !['/','/demo.js','/demo.css','/run'].includes(url.pathname)||url.search){
     violations.push('Unexpected browser request');await route.abort();return;
   }
   const headers=await request.allHeaders();
   if(headers.authorization || headers.cookie)violations.push('Unexpected credential header');
   observed.push({path:url.pathname,method:request.method()});await route.continue();
 });
 const response=await page.goto(origin,{waitUntil:'networkidle'});
 assert.equal(response.status(),200);
 assert.match(response.headers()['content-security-policy'],/script-src 'self'/);
 assert.equal(await page.title(),'MCIS · 隔离调查演示');
 await page.screenshot({path:resolve(artifacts,'before.png'),fullPage:true});
 for(const choice of ['both','1','2']) {
   await page.locator(`input[value="${choice}"]`).check();
   await page.locator('#run').click();
   await page.locator('#result').waitFor({state:'visible',timeout:30000});
   const metric=await page.locator('#metric').innerText();
   assert.equal(metric,choice==='both'?'差异 5°':'未列出冲突候选');
   assert.match(await page.locator('#summary').innerText(),/未审核.*临时数据已清理/);
   assert.match(await page.locator('#summary').innerText(),new RegExp(`已处理 ${choice==='both'?2:1} 份虚构来源`));
   assert.match(await page.locator('#status').innerText(),/不保留正式案件/);
   if(choice==='both')await page.screenshot({path:resolve(artifacts,'result.png'),fullPage:true});
 }
 // page.evaluate itself bypasses CSP; a DOM-inserted inline script must not execute.
 assert.equal(await page.evaluate(()=>{
   delete window.__mcisInlineProbe;
   const script=document.createElement('script');script.textContent='window.__mcisInlineProbe=true';
   document.head.append(script);script.remove();return window.__mcisInlineProbe===true;
 }),false);
 assert.deepEqual(await page.evaluate(()=>({local:localStorage.length,session:sessionStorage.length})),{local:0,session:0});
 assert.deepEqual(await context.cookies(),[]);
 assert.deepEqual(violations,[]);
 assert.equal(observed.filter(r=>r.path==='/run'&&r.method==='POST').length,3);
 console.log('PASS: real Chromium clicks + local W2 (both/1/2), inline CSP, empty storage, bounded requests. Fictional ephemeral demo only; not production UI/login.');
} catch(error) {
 process.exitCode=1;
 console.error(browser?'FAIL: browser acceptance did not complete; no pass claimed.':'BLOCKED: sandboxed Chromium unavailable; no browser acceptance claimed.');
} finally {
 if(browser)await browser.close().catch(()=>{});
 if(child && child.exitCode===null){
   const exited=once(child,'exit');child.kill('SIGTERM');
   let timer;await Promise.race([exited,new Promise(done=>{timer=setTimeout(()=>{child.kill('SIGKILL');done();},30000);})]);clearTimeout(timer);
 }
}
