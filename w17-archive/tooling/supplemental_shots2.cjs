'use strict';
const path=require('node:path');
const [pwPath,exe,front,packagePath,shotsDir]=process.argv.slice(2);
const {chromium}=require(pwPath);
(async()=>{
  const browser=await chromium.launch({executablePath:exe,headless:true,chromiumSandbox:true});
  const page=await (await browser.newContext({viewport:{width:1440,height:900}})).newPage();
  const shot=async(name)=>{const p=path.join(shotsDir,name);await page.screenshot({path:p});console.log('wrote',p);};

  await page.goto(front+'/#/lobby',{waitUntil:'domcontentloaded'});
  await page.getByRole('heading',{name:'案件大厅'}).waitFor({timeout:20000});
  await page.locator('select.role-select').selectOption('LeadInvestigator');
  await page.getByRole('button',{name:'选择基础资料包',exact:true}).click();
  await page.getByLabel('基础资料 .mcase 文件',{exact:true}).setInputFiles(packagePath);
  await page.getByRole('button',{name:'上传并预览基础资料',exact:true}).click();
  await page.getByText('服务端受限恢复范围预览',{exact:true}).waitFor({timeout:15000});
  const ver=page.getByText('案件包版本',{exact:true});
  await ver.scrollIntoViewIfNeeded();
  await shot('11-preview-version-scrolled.png');
  await page.getByText('案件包版本',{exact:true}).locator('xpath=ancestor::div[contains(@class,"w85-summary")][1]').screenshot({path:path.join(shotsDir,'11-preview-summary.png')});
  console.log('preview version dd', await page.getByText('案件包版本',{exact:true}).locator('xpath=following-sibling::dd[1]').innerText());
  // ensure we did not click commit
  const commit=page.getByRole('button',{name:'确认首次导入',exact:true});
  console.log('commit enabled after preview-only?', await commit.isEnabled());

  await page.goto(front+'/#/evidence?case=CASE-INTAKE',{waitUntil:'domcontentloaded'});
  await page.getByText('事件时间线',{exact:false}).waitFor({timeout:20000});
  await page.waitForTimeout(1000);
  await page.locator('canvas').first().scrollIntoViewIfNeeded();
  const canvas=page.locator('canvas').first();
  const cb=await canvas.boundingBox();
  console.log('canvas',cb);
  // hover a grid of points near left of plot (t=1,2 of 60)
  const plotLeft=cb.x+78, plotW=Math.max(50,cb.width-78-44);
  const xs=[plotLeft+(1/60)*plotW, plotLeft+(2/60)*plotW];
  const ys=[cb.y+cb.height*0.45, cb.y+cb.height*0.55, cb.y+cb.height*0.62, cb.y+cb.height*0.70];
  let n=0;
  for(const x of xs){
    for(const y of ys){
      n++;
      await page.mouse.move(x,y);
      await page.waitForTimeout(250);
      const tip=await page.evaluate(()=>{
        const els=[...document.querySelectorAll('div')].filter(e=>{
          const s=getComputedStyle(e);
          return e.textContent && e.textContent.includes('Synthetic') && s.position==='absolute' && e.offsetParent;
        });
        return els.map(e=>e.textContent.slice(0,80));
      });
      console.log('pos',x.toFixed(1),y.toFixed(1),'tips',tip);
      if(tip.length){
        await shot(`12-tooltip-${n}.png`);
      }
    }
  }
  await shot('12-timeline-after-hover.png');
  await browser.close();
})().catch(e=>{console.error(e);process.exit(1);});
