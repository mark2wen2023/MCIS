// Real loopback application + isolated SQLite. Only lost response is intercepted after server commit.
const {chromium}=require(process.env.MCIS_PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.MCIS_BROWSER_BIN||undefined,args:['--no-sandbox']});
 let count=0;const ok=(condition,label)=>{assert(condition,label);console.log(`PASS ${++count} ${label}`)};
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});page.setDefaultTimeout(10000);
  const failures=[];page.on('pageerror',e=>failures.push(String(e)));
  const web=process.env.MCIS_W92_WEB_URL,panel=page.locator('.w92-page');
  const ready=()=>panel.getByRole('button',{name:'＋ 新增环境记录'}).waitFor();
  const open=()=>panel.getByRole('button',{name:'＋ 新增环境记录'}).click();
  const save=()=>panel.getByRole('button',{name:'保存环境记录',exact:true}).click();
  const fill=async id=>{await panel.getByLabel('观测编号（必填，案件内唯一）').fill(id);await panel.getByLabel('资料来源（必填）').fill('虚构资料第 2 页');await panel.getByLabel('原文与说明（必填）').fill('  虚构：东北风4级\n能见度良好，未知时刻/地点。  ')};
  const go=async cid=>{await page.goto(web+'/#/env?case='+cid);await ready()};
  await go('CASE-W92-A');ok((await panel.innerText()).includes('尚未供仿真使用'),'not simulation claim');
  ok(await panel.locator('.w92-record').count()===0,'new case empty');await open();await fill('OBS-REAL-HTTP');
  await panel.getByLabel('能见度（nm）（可选）').fill('0');await save();await panel.getByText('环境记录已保存',{exact:true}).waitFor();
  ok(await panel.locator('.w92-record').count()===1,'real HTTP create shows one');
  let docs=await page.evaluate(()=>fetch('/api/v1/cases/CASE-W92-A/environment-observations').then(r=>r.json()));
  ok(docs[0].observedAtUtc===null&&docs[0].locationDescription===null&&!('windSpeedMps' in docs[0]),'server unknown not fabricated');
  ok(docs[0].visibilityNm===0&&docs[0].description.startsWith('  ')&&docs[0].description.endsWith('  '),'zero and source whitespace roundtrip');
  await page.reload();await ready();ok((await panel.locator('.w92-record').innerText()).includes('0 nm'),'reopen known zero');
  ok((await panel.locator('.w92-record').innerText()).includes('未知'),'reopen unknown label');
  await open();await fill('OBS-REAL-HTTP');await save();await panel.getByText(/观测编号已存在/).waitFor();ok(await panel.locator('.w92-record').count()===1,'duplicate does not overwrite');
  await panel.getByRole('button',{name:'取消 / 关闭'}).click();await open();await fill('OBS-DIRECTION');
  await panel.getByLabel('风的来向（° 真北）（可选）').fill('90');await panel.getByLabel('水流去向（° 真北）（可选）').fill('270');await save();await panel.getByText('环境记录已保存',{exact:true}).waitFor();
  const last=await panel.locator('.w92-record').last().innerText();ok(last.includes('90 °（从该方向吹来）')&&last.includes('270 °（向该方向流去）'),'direction semantics visible and distinct');
  await go('CASE-W92-B');ok(await panel.locator('.w92-record').count()===0,'case B no leaked A records');await page.goBack();await ready();ok(await panel.locator('.w92-record').count()===2,'browser Back returns original saved case');
  await page.goForward();await ready();ok(await panel.locator('.w92-record').count()===0,'browser Forward restores B');
  await open();await fill('CANCEL');await panel.getByRole('button',{name:'取消 / 关闭'}).click();await open();ok(await panel.getByLabel('观测编号（必填，案件内唯一）').inputValue()==='','cancel clears draft');
  await fill('LOST-RESPONSE');let posts=0;
  await page.route('**/cases/CASE-W92-B/environment-observations',async route=>{if(route.request().method()==='POST'){posts++;await route.fetch();await route.abort()}else await route.continue()});
  await save();await panel.getByText(/保存结果尚未确认/).waitFor();ok(await panel.getByRole('button',{name:'保存环境记录',exact:true}).count()===0,'lost response prevents blind resend');
  await panel.getByRole('button',{name:'核查保存结果（只读）'}).click();await panel.getByText('环境记录已保存',{exact:true}).waitFor();ok(posts===1,'read-only recovery no second POST');
  await page.unroute('**/cases/CASE-W92-B/environment-observations');await page.locator('.role-select').selectOption('Public');await panel.getByText('当前身份仅可查看，不能新增环境记录。').waitFor();ok(await panel.getByRole('button',{name:'＋ 新增环境记录'}).count()===0,'Public cannot create');
  await page.locator('.role-select').selectOption('Investigator');await ready();
  await page.goto(web+'/#/env?case=CASE-W92-REDACTED');await panel.getByText('当前身份无权读取本案环境记录。').waitFor();ok(await panel.locator('.w92-record').count()===0,'Redacted policy fails closed');
  await go('CASE-W92-A');
  for(const width of [1440,768,390]){
   await page.setViewportSize({width,height:1000});await open();await fill('LAYOUT');
   ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`document fits ${width}`);
   ok(await panel.evaluate(el=>el.scrollWidth<=el.clientWidth),`environment fits ${width}`);
   await page.screenshot({path:path.join(process.env.MCIS_W92_RUN_DIR,`acceptance-${width}.png`),fullPage:true});
   await panel.getByRole('button',{name:'取消 / 关闭'}).click();
  }
  await page.setViewportSize({width:1440,height:1000});
  await page.getByRole('link',{name:/航迹设定/}).click();await page.getByRole('heading',{name:'已保存航迹检查'}).waitFor();
  ok(page.url().includes('case=CASE-W92-A'),'W10 navigation retains current case');
  await page.getByRole('link',{name:/询问笔录比对/}).click();await page.getByRole('heading',{name:'笔录抽取与草稿审核'}).waitFor();
  ok(page.url().includes('/interview?case=CASE-W92-A'),'W20 interview route retained');
  await page.getByRole('link',{name:/气象水文/}).click();await ready();
  ok(page.url().includes('/env?case=CASE-W92-A')&&await panel.locator('.w92-record').count()===2,'environment sidebar roundtrip retains case and records');
  ok(failures.length===0,'no runtime JS errors');console.log(`TOTAL ${count} passed; real backend, synthetic inputs.`);
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
