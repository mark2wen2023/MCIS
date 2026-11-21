// Manual real Chromium acceptance. Optional existing Playwright only; never installs.
// Browser launch failure is NOT a pass. No simulation/fallback or sandbox-disable flag.
'use strict';
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {pathToFileURL}=require('node:url'),assert=require('node:assert/strict');
const PRODUCT='f536f7482f1e1bff5f448a699cf4b0af320f2af7';
const HTML_SHA='8ad4bf30eebbe7309155292682361c1b977baacb667dc3019bd99c22307c00e6';
function options(args){
 const o={screenshots:false};
 for(let i=0;i<args.length;i++){
  const k=args[i];if(k==='--screenshots'){if(o.screenshots)throw Error('duplicate flag');o.screenshots=true;continue;}
  if(!['--html','--output','--chromium'].includes(k)||o[k]!==undefined||!args[i+1]||args[i+1].startsWith('--'))throw Error('invalid arguments');
  o[k]=args[++i];
 }
 if(!o['--html']||!o['--output'])throw Error('usage: node check.cjs --html FIXED_HTML --output NEW_DIRECTORY [--chromium ABSOLUTE_EXECUTABLE] [--screenshots]');
 if(o['--chromium']&&!path.isAbsolute(o['--chromium']))throw Error('chromium path must be absolute');
 return o;
}
async function main(){
 const o=options(process.argv.slice(2)),input=path.resolve(o['--html']),out=path.resolve(o['--output']);
 if(!fs.lstatSync(input).isFile())throw Error('HTML must be a regular file, not a symlink');
 const raw=fs.readFileSync(input);if(crypto.createHash('sha256').update(raw).digest('hex')!==HTML_SHA)throw Error('fixed product HTML hash mismatch');
 fs.mkdirSync(out); // Refuse existing output, preserve earlier evidence.
 const snapshot=path.join(out,'fixed-preview.html');fs.writeFileSync(snapshot,raw,{flag:'wx'});
 const url=pathToFileURL(snapshot).href;
 const evidence={productCommit:PRODUCT,htmlSha256:HTML_SHA,status:'failed',stage:'dependency',
  browser:null,playwright:null,viewport:{width:1440,height:900},checks:[],requests:[],errors:[],screenshots:[],browserClosed:false};
 let browser,failed=null;
 try{
  const {chromium}=require('playwright');evidence.playwright=require('playwright/package.json').version;
  evidence.stage='launch';
  browser=await chromium.launch({...(o['--chromium']?{executablePath:o['--chromium']}:{}),headless:true,chromiumSandbox:true,timeout:30000});
  evidence.browser=browser.version();evidence.stage='navigation';
  const context=await browser.newContext({viewport:evidence.viewport,offline:true,serviceWorkers:'block'});
  context.on('request',r=>evidence.requests.push(r.url()));
  const page=await context.newPage();page.setDefaultTimeout(10000);
  page.on('pageerror',e=>evidence.errors.push(e.message));page.on('console',m=>{if(['error','warning'].includes(m.type()))evidence.errors.push(m.type()+': '+m.text());});
  await page.goto(url,{waitUntil:'load',timeout:30000});
  assert.equal(page.url(),url);assert.match(await page.title(),/合成共享时点证据/);assert(await page.locator('h1').isVisible());
  evidence.checks.push('fixed page identity and visible heading');evidence.stage='interaction';
  async function screenshot(name){if(o.screenshots){await page.screenshot({path:path.join(out,name+'.png'),fullPage:true});evidence.screenshots.push(name+'.png');}}
 async function at(t){await page.locator('#time').selectOption({label:'T+'+t+'s'});assert.match(await page.locator('#clock').innerText(),new RegExp('T\\+'+String(t).replace('.','\\.')+'秒'));}
 async function detail(){return JSON.parse(await page.locator('#detail').innerText());}
 await at(0);await page.getByRole('button',{name:'查看原始点 A-t0',exact:true}).click();let original=await detail();assert.equal(original.gitRef,'2048c60fd6650c6f2c99a76a16be463a3895655d');assert.equal(original.jsonPointer,'/points/0');assert.equal(original.rawRecord.pointId,'A-t0');assert.equal(original.rawRecord.time.correctionSeconds,0);evidence.checks.push('T0 raw point identity, fixed fixture ref and pointer');
 await at(20);await page.getByRole('button',{name:'查看原始点 B-t20',exact:true}).click();let d=await detail();assert.equal(d.rawRecord.time.sourceUtc,'2026-02-01T12:00:08.000Z');assert.equal(d.rawRecord.time.correctionSeconds,12);assert.equal(d.rawRecord.time.alignedUtc,'2026-02-01T12:00:20.000Z');assert.equal(d.rawRecord.position.kind,'interpolated');assert.equal(await page.locator('#plot circle').count(),2);evidence.checks.push('T20 B raw +12 and existing interpolated quality');await screenshot('t20');
 await at(100);await page.locator('#events').getByRole('button').click();d=await detail();assert.equal(d.time.correctionSeconds,7);assert.equal(d.time.sourceUtc,'2026-02-01T12:01:33.000Z');assert.equal(d.time.alignedUtc,'2026-02-01T12:01:40.000Z');assert.equal(d.associatedTrack.records[0].rawRecord.pointId,'A-t100');assert.equal(await page.locator('#plot circle').count(),2);assert.match(await page.locator('#excluded').innerText(),/SYN-DEVICE-02.*不参与同步/);assert(!((await page.locator('#events').innerText()).includes('SYN-DEVICE-02')));evidence.checks.push('T100 device +7 associated A-t100; unknown device listed separately');await screenshot('t100');
 await at(80);assert.equal(await page.locator('#plot circle').count(),1);assert.match(await page.locator('#vessels article').nth(0).innerText(),/禁止跨缺口/);assert.match(await page.locator('#vessels article').nth(1).innerText(),/B-t80/);assert.match(await page.locator('#detail').innerText(),/未沿用上一时点/);evidence.checks.push('T80 A removed, B input point retained, old detail cleared');await screenshot('t80');
 await at(124.25);assert.equal(await page.locator('#plot circle').count(),0);assert.match(await page.locator('#vessels article').nth(0).innerText(),/禁止跨缺口/);assert.match(await page.locator('#vessels article').nth(1).innerText(),/此时点无观测/);assert.match(await page.locator('#excluded').innerText(),/不参与同步/);assert.equal(await page.locator('#events button').count(),0);evidence.checks.push('T124.25 A gap; B has no exact input at this instant, honestly empty (not carried forward)');await screenshot('t124-25');
 await page.locator('#excluded button').click();d=await detail();assert.equal(d.time.alignedUtc,null);assert.equal(d.status,'time_unresolved_not_synchronized');evidence.checks.push('unknown device remains outside synchronized events');
 for(const t of [60,100,121,127.5]){await at(t);assert.match(await page.locator('#vessels article').first().innerText(),/艏向：未知.*COG：90/);}evidence.checks.push('four A boundary observations retain unknown HDG; no COG fallback');

  assert.deepEqual(evidence.errors,[]);assert.deepEqual(evidence.requests,[url]);
  evidence.checks.push('no external page requests observed; no console/page errors (offline context)');
  evidence.stage='close';await context.close();
 }catch(e){failed=e;evidence.failure=String(e.stack||e);}
 finally{
  if(browser){try{await browser.close();evidence.browserClosed=true;}catch(e){failed=failed||e;evidence.cleanupFailure=String(e);}}
  if(!failed){evidence.status='passed';evidence.stage='complete';}
  fs.writeFileSync(path.join(out,'result.json'),JSON.stringify(evidence,null,2)+'\n',{flag:'wx'});
 }
 if(failed)throw failed;
 console.log('PASS real Chromium acceptance: '+evidence.browser+'; result.json and optional screenshots saved');
}
main().catch(e=>{console.error(String(e.stack||e));process.exitCode=1;});
