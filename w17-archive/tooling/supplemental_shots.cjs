// Read-only supplemental shots on the already-imported target. No second commit.
'use strict';
const fs=require('node:fs');
const path=require('node:path');
const [pwPath,exe,front,sha,shotsDir]=process.argv.slice(2);
const {chromium}=require(pwPath);
(async()=>{
  const browser=await chromium.launch({executablePath:exe,headless:true,chromiumSandbox:true});
  const page=await (await browser.newContext({viewport:{width:1440,height:900}})).newPage();
  async function shot(name){const p=path.join(shotsDir,name);await page.screenshot({path:p,fullPage:false});console.log('wrote',p);}
  await page.goto(front+'/#/lobby',{waitUntil:'domcontentloaded'});
  await page.getByRole('heading',{name:'案件大厅'}).waitFor({timeout:20000});
  await page.locator('select.role-select').selectOption('LeadInvestigator');
  await page.getByRole('button',{name:'选择基础资料包',exact:true}).click();
  await page.getByLabel('按包 SHA-256 查询导入回执').fill(sha);
  await page.getByRole('button',{name:'只读查询回执',exact:true}).click();
  await page.getByText('已核验服务端导入回执',{exact:true}).waitFor();
  const ver=page.getByText(/案件包版本：1\.4\.0/);
  await ver.scrollIntoViewIfNeeded();
  await shot('08-receipt-version-scrolled.png');
  const verText=await ver.innerText();
  const box=page.getByText('已核验服务端导入回执',{exact:true}).locator('xpath=ancestor::div[@role="status"][1]');
  await box.screenshot({path:path.join(shotsDir,'08-receipt-block.png')});
  console.log('receipt version text',verText);

  await page.goto(front+'/#/evidence?case=CASE-INTAKE',{waitUntil:'domcontentloaded'});
  await page.getByText('事件时间线',{exact:false}).waitFor({timeout:20000});
  await page.waitForTimeout(800);
  const lane=page.getByText('双方 / 环境',{exact:true});
  await lane.scrollIntoViewIfNeeded();
  const lb=await lane.boundingBox();
  // two dots just to the right of the lane label
  for (const [i,dx] of [[1,22],[2,40]]){
    await page.mouse.move(lb.x+lb.width+dx, lb.y+lb.height/2);
    await page.waitForTimeout(400);
    await shot(`09-tooltip-synthetic-${i}.png`);
    const tip=await page.locator('.echarts-tooltip, div[style*="background"]').allTextContents().catch(()=>[]);
    console.log('hover',i,'tooltip candidates',tip.slice(0,5));
  }
  // also try echarts convertToPixel
  const pixels=await page.evaluate(()=>{
    const nodes=[...document.querySelectorAll('[_echarts_instance_], canvas')];
    const el=document.querySelector('[_echarts_instance_]')||document.querySelector('canvas')?.parentElement;
    const inst=el && window.echarts && window.echarts.getInstanceByDom(el);
    if(!inst) return {found:false, inst:!!el};
    return {found:true, p1:inst.convertToPixel({xAxisIndex:0,yAxisIndex:0},[1,0]), p2:inst.convertToPixel({xAxisIndex:0,yAxisIndex:0},[2,0])};
  });
  console.log('pixels',pixels);
  if(pixels && pixels.found){
    const cb=await page.locator('canvas').first().boundingBox();
    // convertToPixel is relative to chart box
    for(const [i,p] of [['1',pixels.p1],['2',pixels.p2]]){
      await page.mouse.move(cb.x+p[0], cb.y+p[1]);
      await page.waitForTimeout(400);
      await shot(`10-echarts-tooltip-${i}.png`);
    }
  }
  await browser.close();
})().catch(e=>{console.error(e);process.exit(1);});
