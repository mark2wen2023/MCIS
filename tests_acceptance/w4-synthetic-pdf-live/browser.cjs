// Real Chromium + actual localhost HTTP only. No route interception, canvas or response mocks.
const assert=require('node:assert/strict');const {createHash}=require('node:crypto');let stage='dependency';
(async()=>{
 const {chromium}=require(process.argv[2]);const [executablePath,origin,caseId,runId,imagePath,imageSha]=process.argv.slice(3);
 let browser;
 try{
  stage='browser_launch';browser=await chromium.launch({executablePath,headless:true,chromiumSandbox:true});
  stage='browser_assertions';const context=await browser.newContext({serviceWorkers:'block'});const page=await context.newPage();
  const forbidden=[];page.on('request',r=>{if(!r.url().startsWith(origin+'/'))forbidden.push(r.url());});
  const writes=[];page.on('request',r=>{if(r.method()==='POST')writes.push(r.url());});
  await page.goto(origin+'/image-review-lab');await page.locator('#case').fill(caseId);await page.locator('#run').fill(runId);await page.locator('#load').click();
  await page.locator('[data-ocr-review]').waitFor();
  await page.evaluate(()=>{window.oldDownload=document.querySelector('#source button').onclick;window.oldSave=document.querySelector('[data-ocr-review]').onclick;});
  const pending=page.waitForResponse(r=>r.url().endsWith('/synthetic-pdf-page'));
  await page.locator('#show-pdf').click();const response=await pending;assert.equal(response.status(),200);
  const receipt=await response.json();assert.deepEqual(Object.keys(receipt).sort(),['caseId','description','pngBase64','revision','runId']);
  assert.equal(receipt.description.physicalPage,1);assert.equal(receipt.caseId,caseId);assert.equal(receipt.runId,runId);
  await page.waitForFunction(()=>document.querySelector('#page-image').width===256&&document.querySelector('#preview-status').textContent.includes('原PDF SHA256'));
  const pixel=await page.locator('#page-image').evaluate(c=>Array.from(c.getContext('2d').getImageData(128,128,1,1).data));
  assert.deepEqual(pixel,[255,0,0,255]);assert.equal(await page.locator('#lines').isVisible(),false);
  const baseline=writes.length;
  for(const [id,old] of [['case',caseId],['run',runId]]){
   await page.locator('#'+id).fill('OTHER');
   await page.evaluate(async()=>{await window.oldDownload();await window.oldSave();});
   await page.locator('#'+id).fill(old);
   await page.evaluate(async()=>{await window.oldDownload();await window.oldSave();});
   assert.equal(writes.length,baseline);
  }
  await page.locator('#load').click();await page.locator('[data-ocr-review]').waitFor();
  await page.evaluate(async()=>{await window.oldDownload();await window.oldSave();});assert.equal(writes.length,baseline);
  const imageReply=page.waitForResponse(r=>r.url()===origin+imagePath);
  await page.locator('#show-image').click();
  const ir=await imageReply;assert.equal(ir.status(),200);const imageBytes=await ir.body();assert.equal(createHash('sha256').update(imageBytes).digest('hex'),imageSha);assert.equal(ir.headers()['x-sha256'],imageSha);assert.notEqual(imageSha,receipt.description.pageSha256);
  await page.waitForFunction(()=>document.querySelector('#page-image').width===256&&document.querySelector('#preview-status').textContent.includes('页图已载入'));
  const restored=await page.locator('#page-image').evaluate(c=>Array.from(c.getContext('2d').getImageData(128,128,1,1).data));
  assert.deepEqual(restored,[0,0,255,255]);assert.equal(writes.length,baseline+1);
  assert.equal(writes.filter(x=>x.endsWith('/reviews')).length,0);assert.deepEqual(forbidden,[]);
  console.log(JSON.stringify({passed:true,sandbox:true,realCanvasPixel:pixel,derivedRequests:1,restoredPngRequests:1,ocrWrites:0}));
 }finally{if(browser)await browser.close();}
})().catch(e=>{console.log(JSON.stringify({passed:false,stage,errorType:e.name}));process.exitCode=stage==='browser_launch'?20:stage==='browser_assertions'?21:22;});
