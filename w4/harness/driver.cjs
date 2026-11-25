// W4 extended real-Chromium driver. Normal sandbox (chromiumSandbox:true). No page.route, no response/canvas mocks.
// Delays are injected server-side (harness ASGI wrapper) after the real handler ran.
const assert=require('node:assert/strict');const fs=require('node:fs');const {execFileSync}=require('node:child_process');
const [pwPath,exe,cfgPath]=process.argv.slice(2);const cfg=JSON.parse(fs.readFileSync(cfgPath));const {chromium}=require(pwPath);
const [W,H]=cfg.viewport.split('x').map(Number);const tag=cfg.tag;const steps=[];let stage='launch';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const access=()=>JSON.parse(execFileSync('python3',['-c',`import sqlite3,json,sys;c=sqlite3.connect('file:${cfg.db}?mode=ro',uri=True);r=c.execute("select evidence_id,count(*) from custody_events where kind='Access' group by evidence_id").fetchall();print(json.dumps(dict(r)))`]).toString());
const acc=()=>{const a=access();return {pdf:a[cfg.pdfEvidenceId]||0,image:a[cfg.imageEvidenceId]||0};};
const delay=(suffix,seconds)=>fs.writeFileSync(cfg.delayFile,JSON.stringify({suffix,seconds,remaining:1}));
(async()=>{
 const browser=await chromium.launch({executablePath:exe,headless:true,chromiumSandbox:true});
 const ps=execFileSync('ps',['-eo','pid,args']).toString().split('\n').filter(l=>l.includes('/opt/google/chrome/')&&!l.includes('driver.cjs'));
 const noSandboxFlag=ps.some(l=>/--no-sandbox|--disable-setuid-sandbox/.test(l));const sandboxProcs=ps.filter(l=>/--type=renderer/.test(l)).length;
 steps.push({step:'launch',version:browser.version(),noSandboxFlagSeen:noSandboxFlag,rendererProcs:sandboxProcs,chromeProcs:ps.length});assert.equal(noSandboxFlag,false);
 const context=await browser.newContext({viewport:{width:W,height:H},serviceWorkers:'block'});const page=await context.newPage();
 const forbidden=[],consoleErr=[],net=[];page.on('request',r=>{if(!r.url().startsWith(cfg.origin+'/'))forbidden.push(r.url());if(r.method()==='POST')net.push(r.url().replace(cfg.origin,''));});
 page.on('response',r=>{if(r.status()>=400)consoleErr.push('HTTP '+r.status()+' '+r.url().replace(cfg.origin,''));});page.on('console',m=>{if(m.type()==='error')consoleErr.push(m.text());});page.on('pageerror',e=>consoleErr.push('pageerror:'+e.message));
 const canvas=()=>page.locator('#page-image').evaluate(c=>{const r={w:c.width,h:c.height,status:document.querySelector('#preview-status').textContent,lineHidden:document.querySelector('#lines').hidden};if(c.width>=129&&c.height>=129){r.center=Array.from(c.getContext('2d').getImageData(128,128,1,1).data);r.corner=Array.from(c.getContext('2d').getImageData(5,5,1,1).data);}return r;});
 const shot=async name=>{await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));await page.locator('#page-image').scrollIntoViewIfNeeded().catch(()=>{});
  await page.screenshot({path:`${cfg.shots}/${tag}-${name}-page.png`,fullPage:false});const c=await canvas();if(c.w>0)await page.locator('#page-image').screenshot({path:`${cfg.shots}/${tag}-${name}-canvas.png`});return c;};
 const load=async(caseId,run)=>{await page.locator('#case').fill(caseId);await page.locator('#run').fill(run);await page.locator('#load').click();await page.locator('[data-ocr-review]').waitFor();};
 const red=async()=>{await page.waitForFunction(()=>document.querySelector('#page-image').width===256&&document.querySelector('#preview-status').textContent.includes('原PDF SHA256'));};
 const blue=async()=>{await page.waitForFunction(()=>document.querySelector('#page-image').width===256&&document.querySelector('#preview-status').textContent.includes('页图已载入'));};
 const RED=[255,0,0,255],BLUE=[0,0,255,255];
 await page.goto(cfg.origin+'/image-review-lab');
 {const ps2=execFileSync('ps',['-eo','pid,args']).toString().split('\n').filter(l=>l.includes('/opt/google/chrome/'));const rend=ps2.filter(l=>/--type=renderer/.test(l));let seccomp=null,nnp=null;if(rend[0]){const st=fs.readFileSync('/proc/'+rend[0].trim().split(' ')[0]+'/status','utf8');seccomp=(st.match(/Seccomp:\s*(\d+)/)||[])[1];nnp=(st.match(/NoNewPrivs:\s*(\d+)/)||[])[1];}
  steps.push({step:'sandbox_probe',chromeProcs:ps2.length,renderers:rend.length,noSandboxFlagSeen:ps2.some(l=>/--no-sandbox|--disable-setuid-sandbox/.test(l)),rendererSeccomp:seccomp,rendererNoNewPrivs:nnp,zygote:ps2.some(l=>/--type=zygote/.test(l))});assert.ok(!steps.at(-1).noSandboxFlagSeen);}
 // 1 red page 1
 stage='red_page1';await load(cfg.caseId,cfg.runA);let a0=acc();
 let resp=page.waitForResponse(r=>r.url().endsWith('/synthetic-pdf-page'));await page.locator('#show-pdf').click();let rr=await resp;assert.equal(rr.status(),200);await red();
 let c=await shot('1-red-page1');assert.deepEqual(c.center,RED);let a1=acc();assert.deepEqual([a1.pdf-a0.pdf,a1.image-a0.image],[1,0]);
 steps.push({step:stage,pass:true,canvas:c,accessDelta:{pdf:a1.pdf-a0.pdf,image:a1.image-a0.image}});
 // 2 explicit re-read -> blue page 2
 stage='blue_reread';await page.locator('#load').click();await page.locator('[data-ocr-review]').waitFor();resp=page.waitForResponse(r=>r.url()===cfg.origin+cfg.imagePath);await page.locator('#show-image').click();rr=await resp;assert.equal(rr.status(),200);await blue();
 c=await shot('2-blue-reread');assert.deepEqual(c.center,BLUE);let a2=acc();assert.deepEqual([a2.pdf-a1.pdf,a2.image-a1.image],[0,1]);
 steps.push({step:stage,pass:true,canvas:c,accessDelta:{pdf:a2.pdf-a1.pdf,image:a2.image-a1.image}});
 // 3 A->B->A across real review runs with delayed old PDF response
 stage='ABA_run_delayed_old_pdf';
 if(cfg.runB){
  delay('/synthetic-pdf-page',3);let b0=acc();resp=page.waitForResponse(r=>r.url().endsWith('/synthetic-pdf-page'),{timeout:15000});
  await page.locator('#show-pdf').click();await sleep(300);
  await page.locator('#run').fill(cfg.runB); // switch to round B while old A response in flight
  rr=await resp;await sleep(800);let mid=await shot('3a-after-stale-arrival-on-B');
  assert.ok(!mid.status.includes('原PDF SHA256'));assert.notDeepEqual(mid.center,RED);
  await load(cfg.caseId,cfg.runB);resp=page.waitForResponse(r=>r.url()===cfg.origin+cfg.imagePath);await page.locator('#show-image').click();await resp;await blue();
  let cb=await shot('3b-runB-blue');assert.deepEqual(cb.center,BLUE);
  await load(cfg.caseId,cfg.runA);resp=page.waitForResponse(r=>r.url().endsWith('/synthetic-pdf-page'));await page.locator('#show-pdf').click();await resp;await red();await sleep(1000);
  let ca=await shot('3c-back-to-A-red');assert.deepEqual(ca.center,RED);let b1=acc();
  steps.push({step:stage,pass:true,staleStatus:rr.status(),afterStale:mid,runB:cb,backToA:ca,accessDelta:{pdf:b1.pdf-b0.pdf,image:b1.image-b0.image},note:'server audits the delayed (discarded) read too: expect pdf+2,image+1'});
 } else steps.push({step:stage,pass:null,note:'run B not creatable'});
 // 4 case switch while delayed PDF in flight
 stage='case_switch_delayed_old_pdf';delay('/synthetic-pdf-page',3);let d0=acc();
 resp=page.waitForResponse(r=>r.url().endsWith('/synthetic-pdf-page'),{timeout:15000});await page.locator('#show-pdf').click();await sleep(300);
 await page.locator('#case').fill('OTHER-CASE');await page.locator('#case').fill(cfg.caseId); // A->B->A on the case field
 rr=await resp;await sleep(800);let m4=await shot('4-case-ABA-after-stale');assert.ok(!m4.status.includes('原PDF SHA256'));assert.notDeepEqual(m4.center,RED);
 await load(cfg.caseId,cfg.runA);resp=page.waitForResponse(r=>r.url()===cfg.origin+cfg.imagePath);await page.locator('#show-image').click();await resp;await blue();await sleep(1000);
 let m4b=await shot('4b-case-ABA-blue');assert.deepEqual(m4b.center,BLUE);let d1=acc();
 steps.push({step:stage,pass:true,staleStatus:rr.status(),afterStale:m4,final:m4b,accessDelta:{pdf:d1.pdf-d0.pdf,image:d1.image-d0.image}});
 // 5 delayed old BLUE (registered PNG) then switch run A->B->A, then red must not be overwritten
 stage='run_switch_delayed_old_png';await load(cfg.caseId,cfg.runA);delay(':download',3);let e0=acc();
 resp=page.waitForResponse(r=>r.url()===cfg.origin+cfg.imagePath,{timeout:15000});await page.locator('#show-image').click();await sleep(300);
 await page.locator('#run').fill(cfg.runB||'OTHER');await page.locator('#run').fill(cfg.runA);
 rr=await resp;await sleep(800);let m5=await shot('5a-after-stale-png');assert.ok(!m5.status.includes('页图已载入'));assert.notDeepEqual(m5.center,BLUE);
 await load(cfg.caseId,cfg.runA);resp=page.waitForResponse(r=>r.url().endsWith('/synthetic-pdf-page'));await page.locator('#show-pdf').click();await resp;await red();await sleep(1000);
 let m5b=await shot('5b-red-after-stale-png');assert.deepEqual(m5b.center,RED);let e1=acc();
 steps.push({step:stage,pass:true,staleStatus:rr.status(),afterStale:m5,final:m5b,accessDelta:{pdf:e1.pdf-e0.pdf,image:e1.image-e0.image}});
 // 6 clear button during delayed PDF
 stage='clear_during_delayed_pdf';delay('/synthetic-pdf-page',3);
 resp=page.waitForResponse(r=>r.url().endsWith('/synthetic-pdf-page'),{timeout:15000});await page.locator('#show-pdf').click();await sleep(300);await page.locator('#clear-image').click();
 rr=await resp;await sleep(800);let m6=await shot('6-clear-after-stale');assert.ok(!m6.status.includes('原PDF SHA256'));assert.notDeepEqual(m6.center,RED);
 steps.push({step:stage,pass:true,staleStatus:rr.status(),afterStale:m6});
 assert.deepEqual(forbidden,[]);const ocrWrites=net.filter(x=>x.endsWith('/reviews')).length;assert.equal(ocrWrites,0);
 await browser.close();
 console.log(JSON.stringify({passed:true,viewport:cfg.viewport,steps,forbidden,ocrWrites,consoleErrors:consoleErr,posts:net}));
})().catch(e=>{console.log(JSON.stringify({passed:false,stage,error:String(e&&e.stack||e).slice(0,1500),steps}));process.exitCode=1;process.exit(1);});
