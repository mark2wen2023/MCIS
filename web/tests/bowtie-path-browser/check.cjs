'use strict'
const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict'),path=require('node:path');
async function run(){
 const [bundle,chrome]=process.argv.slice(2);assert(bundle&&chrome&&path.isAbsolute(chrome));
 const script=fs.readFileSync(bundle), url='https://w15-path.synthetic.invalid';
 const browser=await chromium.launch({headless:true,chromiumSandbox:true,executablePath:chrome});
 try{
  for(const viewport of [{width:1440,height:900},{width:390,height:844}]){
   const context=await browser.newContext({viewport,offline:true,serviceWorkers:'block'});
   const external=[],errors=[];
   try{
    await context.route('**/*',r=>{
     if(r.request().url()===url+'/')return r.fulfill({contentType:'text/html; charset=utf-8',body:'<!doctype html><html lang="zh"><meta charset="utf-8"><link rel="icon" href="data:,"><title>W15 synthetic</title><div id="root"></div><script src="/fixture.js"></script></html>'});
     if(r.request().url()===url+'/fixture.js')return r.fulfill({contentType:'application/javascript',body:script});
     external.push(r.request().url());return r.abort();
    });
    const p=await context.newPage();p.on('pageerror',e=>errors.push(String(e)));
    await p.goto(url+'/');const label=n=>p.getByLabel(n,{exact:true}), btn=n=>p.getByRole('button',{name:n,exact:true});
    await p.getByLabel(/危险源/).fill('Synthetic hazard');await label('顶事件 ID').fill('TOP');await label('顶事件描述').fill('Synthetic top');
    for(let i=1;i<=2;i++){
     await btn('添加节点').click();await label('节点 ID '+i).fill('THREAT-'+i);await label('节点名称 '+i).fill('Synthetic same label');
     await btn('添加连线').click();await label('起点 ID '+i).fill('THREAT-'+i);await label('终点 ID '+i).fill('TOP');
    }
    await p.getByRole('checkbox',{name:/SYN-E1 · Synthetic draft reference/}).check();
    const preview=btn('运行结构核查（不保存）');await preview.click();
    const first=btn('定位草稿端点（THREAT-1）'),second=btn('定位草稿端点（THREAT-2）'),source=btn('定位整份草稿参考资料');
    await first.waitFor();
    const focused=()=>p.evaluate(()=>document.activeElement?.id);
    const tabTo=async target=>{for(let i=0;i<80;i++){await p.keyboard.press('Tab');if(await target.evaluate(e=>document.activeElement===e))return}throw Error('Tab target not reached')};
    await preview.focus();await tabTo(first);await p.keyboard.press('Enter');assert.equal(await focused(),'w153-node-0');
    await tabTo(second);await p.keyboard.press('Enter');assert.equal(await focused(),'w153-node-1');
    await tabTo(source);await p.keyboard.press('Enter');assert.equal(await focused(),'w153-draft-sources');
    assert.equal(await p.evaluate(()=>window.fixtureRequestCount()),1);
    await label('节点名称 1').fill('Edited; existing result is stale');
    await first.waitFor({state:'detached'});assert.equal(await second.count(),0);assert.equal(await source.count(),0);
    assert.equal(await p.evaluate(()=>window.fixtureRequestCount()),1);assert.deepEqual(external,[]);assert.deepEqual(errors,[]);
    console.log('PASS width='+viewport.width+' real Tab/Enter endpoint+draft reference focus, stale buttons removed; synthetic responses only');
   }finally{await context.close()}
  }
 }finally{await browser.close()}
}
run().catch(e=>{console.error(String(e));process.exitCode=1});
