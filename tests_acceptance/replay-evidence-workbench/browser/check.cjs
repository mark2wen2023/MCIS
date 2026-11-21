// Manual real-browser acceptance for the NEW workbench, never the old preview.
// Requires an existing Playwright + normally sandboxed Chromium. No installation.
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {pathToFileURL}=require('node:url'),assert=require('node:assert/strict');
const PRODUCT='f25cf283a50b128e7aed8c247c857312249fd3e9';
const HTML_SHA='6a1665d539d868d91c629a61205145660bfee873bd1b423e814eaa07aea641b3';
function options(args){
 const o={};for(let i=0;i<args.length;i++){
  const k=args[i];if(!['--html','--output','--chromium'].includes(k)||o[k]!==undefined||!args[i+1]||args[i+1].startsWith('--'))throw Error('invalid arguments');o[k]=args[++i];
 }
 if(!o['--html']||!o['--output'])throw Error('usage: node check.cjs --html NEW_WORKBENCH_HTML --output NEW_DIRECTORY [--chromium ABSOLUTE_EXECUTABLE]');
 if(o['--chromium']&&!path.isAbsolute(o['--chromium']))throw Error('chromium executable must be absolute');return o;
}
async function main(){
 const o=options(process.argv.slice(2)),input=path.resolve(o['--html']),out=path.resolve(o['--output']);
 if(!fs.lstatSync(input).isFile())throw Error('regular HTML file required');
 const raw=fs.readFileSync(input);if(crypto.createHash('sha256').update(raw).digest('hex')!==HTML_SHA)throw Error('fixed NEW workbench HTML hash mismatch');
 fs.mkdirSync(out);const snapshot=path.join(out,'fixed-workbench.html');fs.writeFileSync(snapshot,raw,{flag:'wx'});const url=pathToFileURL(snapshot).href;
 const result={productCommit:PRODUCT,htmlSha256:HTML_SHA,status:'failed',stage:'dependency',browser:null,playwright:null,viewports:[],browserClosed:false};let browser,failed=null;
 try{
  const {chromium}=require('playwright');result.playwright=require('playwright/package.json').version;result.stage='launch';
  browser=await chromium.launch({headless:true,chromiumSandbox:true,timeout:30000,...(o['--chromium']?{executablePath:o['--chromium']}: {})});result.browser=browser.version();
  for(const viewport of [{width:1440,height:900},{width:390,height:844}]){
   const label=viewport.width===390?'narrow':'desktop';result.stage=label;
   const evidence={label,viewport,checks:[],requests:[],errors:[],screenshots:[],status:'running'};result.viewports.push(evidence);
   const context=await browser.newContext({viewport,offline:true,serviceWorkers:'block'});
   try{
    context.on('request',r=>evidence.requests.push(r.url()));const page=await context.newPage();page.setDefaultTimeout(10000);
    page.on('pageerror',e=>evidence.errors.push(e.message));page.on('console',m=>{if(['error','warning'].includes(m.type()))evidence.errors.push(m.type()+': '+m.text());});
    await page.goto(url,{waitUntil:'load',timeout:30000});assert.equal(page.url(),url);assert.equal(await page.title(),'粤海探析 · 复盘与取证');assert(await page.getByRole('heading',{name:'复盘与取证',exact:true}).isVisible());
    const text=async id=>(await page.locator('#'+id).innerText()).trim();
    const record=async()=>JSON.parse(await text('raw'));
    const markers=()=>page.locator('#map [data-current]');
    async function at(t){await page.locator('#time').selectOption({label:(await page.locator('#time option').allTextContents()).find(x=>x.endsWith('T+'+t+'s'))});assert((await text('clock')).includes('T+'+t+'s'));assert.equal(await text('record-id'),'—');assert(await page.locator('#raw-open').isDisabled());assert.equal(await page.locator('#raw-details').evaluate(n=>n.open),false);}
    async function shot(name){const file=label+'-'+name+'.png';await page.screenshot({path:path.join(out,file),fullPage:true});evidence.screenshots.push(file);}
    async function keyboardActivate(selector){const control=page.locator(selector);await control.focus();assert(await control.evaluate(n=>n===document.activeElement));await page.keyboard.press('Enter');}
    assert.equal(await text('record-id'),'A-t100');assert.equal(await markers().count(),2);evidence.checks.push('new workbench identity, meaningful initial A-t100, two markers');
    await page.keyboard.press('Tab');
    const initialFocus=label==='narrow'?'nav-toggle':'source-a';assert.equal(await page.evaluate(()=>document.activeElement.id),initialFocus);
    assert(await page.locator('#'+initialFocus).evaluate(n=>parseFloat(getComputedStyle(n).outlineWidth)>0));
    if(label==='narrow'){
     assert.equal(await page.locator('#navigation').isVisible(),false);await page.keyboard.press('Enter');assert(await page.locator('#navigation').isVisible());assert.equal(await page.locator('#nav-toggle').getAttribute('aria-expanded'),'true');await page.keyboard.press('Enter');assert.equal(await page.locator('#navigation').isVisible(),false);
    }else assert(await page.locator('#navigation').isVisible());
    evidence.checks.push('real Tab focus and visible focus outline; narrow navigation Enter toggles');
    await at(0);await keyboardActivate('#point-options button:first-child');const origin=await record();assert.equal(origin.rawRecord.pointId,'A-t0');assert.equal(origin.jsonPointer,'/points/0');assert.equal(origin.gitRef,'2048c60fd6650c6f2c99a76a16be463a3895655d');evidence.checks.push('original A-t0 record, fixed input revision and pointer');
    await at(20);await page.locator('#map [data-current="SYN-VESSEL-B"]').click();const mapRecord=await record();
    assert.equal(mapRecord.rawRecord.pointId,'B-t20');assert.equal(mapRecord.rawRecord.time.sourceUtc,'2026-02-01T12:00:08.000Z');assert.equal(mapRecord.rawRecord.time.correctionSeconds,12);assert.equal(mapRecord.rawRecord.time.alignedUtc,'2026-02-01T12:00:20.000Z');assert.equal(mapRecord.rawRecord.position.kind,'interpolated');assert.equal(await text('quality'),'输入已存插值');
    await at(20);await keyboardActivate('#point-options button:nth-child(2)');assert.deepEqual(await record(),mapRecord);await keyboardActivate('#raw-open');assert(await page.locator('#raw-details').evaluate(n=>n.open));assert.equal(await page.evaluate(()=>document.activeElement.id),'raw');
    evidence.checks.push('map click equals keyboard button; T20 original/interpolated/+12; expandable raw record focus');
    await at(80);assert.equal(await markers().count(),1);assert.equal(await markers().first().getAttribute('data-current'),'SYN-VESSEL-B');assert.match(await text('state-note'),/A：缺轨/);assert(await page.locator('#source-a').isDisabled());await keyboardActivate('#point-options button');assert.equal((await record()).rawRecord.pointId,'B-t80');await shot('t80');
    await at(124.25);assert.equal(await markers().count(),0);assert.equal(await page.locator('#point-options button').count(),0);assert.match(await text('state-note'),/B：此时点无精确观测/);assert(await page.locator('#source-a').isDisabled());assert(await page.locator('#source-b').isDisabled());await shot('t124-25');
    evidence.checks.push('T80 one B point; T124.25 zero; old detail invalidated, no carried-forward position');
    await keyboardActivate('#device-known');assert((await text('clock')).includes('T+100s'));assert.equal(await text('record-id'),'SYN-DEVICE-01');assert.equal(await text('correction'),'+7 s');assert.equal(await text('source-time'),'2026-02-01T12:01:33.000Z');assert.equal(await text('aligned-time'),'2026-02-01T12:01:40.000Z');await shot('device100');
    const currentClock=await text('clock');await keyboardActivate('#device-unknown');assert.equal(await text('clock'),currentClock);assert.equal(await text('record-id'),'SYN-DEVICE-02');assert.equal(await text('aligned-time'),'不参与同步');assert.equal(await text('correction'),'未知');assert.equal(await page.locator('#timeline [data-device="SYN-DEVICE-02"]').count(),0);assert.equal(await markers().count(),2);
    evidence.checks.push('device +7 and unknown device separate; unknown does not move clock or positions');
    for(const t of [60,100,121,127.5]){await at(t);await keyboardActivate('#point-options button:first-child');assert.equal((await record()).rawRecord.headingDeg.value,null);assert.match(await text('warning'),/不以航迹向代替艏向/);}
    const lines=await page.locator('#map [data-history="SYN-VESSEL-A"]').evaluateAll(ns=>ns.map(n=>[Number(n.dataset.from),Number(n.dataset.to)]));assert(lines.length);for(const [a,b] of lines)assert(![[60,100],[121,127.5]].some(([lo,hi])=>a<hi&&b>lo));
    evidence.checks.push('HDG unknown preserved at four boundaries; no history line bridges either gap');
    await at(100);await keyboardActivate('#point-options button:first-child');
    const positions=await page.locator('.chart-panel, .timeline-panel, .inspector').evaluateAll(ns=>ns.map(n=>{const b=n.getBoundingClientRect();return {top:b.top+scrollY,bottom:b.bottom+scrollY,left:b.left,right:b.right};}));
    if(label==='narrow'){assert(positions[0].bottom<=positions[1].top+1);assert(positions[1].bottom<=positions[2].top+1);}
    else assert(positions[2].left>=positions[0].right);
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));evidence.checks.push('viewport layout order and no whole-page horizontal overflow');await shot('layout100');
    assert.deepEqual(evidence.errors,[]);assert.deepEqual(evidence.requests,[url]);evidence.checks.push('no external page requests observed in offline context; no page/console errors');evidence.status='passed';
   }finally{await context.close();}
  }
 }catch(e){failed=e;result.failure=String(e.stack||e);}
 finally{
  if(browser){try{await browser.close();result.browserClosed=true;}catch(e){failed=failed||e;result.cleanupFailure=String(e);}}
  if(!failed){result.status='passed';result.stage='complete';}
  fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});
 }
 if(failed)throw failed;console.log('PASS real browser desktop+narrow: '+result.browser+'; result.json and screenshots saved');
}
main().catch(e=>{console.error(String(e.stack||e));process.exitCode=1;});
