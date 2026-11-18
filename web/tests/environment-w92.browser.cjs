// UI fault/lifecycle tests use synthetic intercepted API responses, not backend acceptance.
const {chromium}=require(process.env.MCIS_PLAYWRIGHT_MODULE || 'playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.MCIS_BROWSER_BIN||undefined,args:['--no-sandbox']});
 const artifacts=process.env.MCIS_W92_ARTIFACTS||fs.mkdtempSync(path.join(os.tmpdir(),'mcis-w92-ui-'));
 fs.mkdirSync(artifacts,{recursive:true});let count=0;const ok=(v,m)=>{assert(v,m);console.log('PASS '+(++count)+' '+m)};
 try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}});page.setDefaultTimeout(10000);
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 const db={A:[],B:[]};let posts=0,mode='ok',getMode='ok';
 await page.route('**/api/v1/**',async route=>{
  const req=route.request(),url=new URL(req.url()),parts=url.pathname.split('/');const id=parts[4];
  if(parts[3]!=='cases')return route.fulfill({json:[]});
  if(parts.length===5)return route.fulfill({json:{caseId:id,title:'合成测试案件 '+id,isFictionalDemo:true}});
  if(parts[5]==='environment-observations'){
   if(req.method()==='GET'){
    const result=getMode==='mismatch'?[{...db.A[0],caseId:'OTHER'}]:db[id]||[];
    if(getMode==='delay'){await new Promise(r=>setTimeout(r,650))}
    if(getMode==='denied')return route.fulfill({status:403,json:{code:'FORBIDDEN'}});
    return route.fulfill({json:result});
   }
   posts++;const body=req.postDataJSON();
   if(mode==='denied')return route.fulfill({status:403,json:{code:'FORBIDDEN'}});
   if(db[id].some(x=>x.observationId===body.observationId))return route.fulfill({status:409,json:{code:'EXISTS'}});
   db[id].push(body);
   if(mode==='lost')return route.abort();
   if(mode==='delay')await new Promise(r=>setTimeout(r,650));
   return route.fulfill({status:201,json:body});
  }
  return route.fulfill({json:[]});
 });
 const panel=page.locator('.w92-page');
 const open=async()=>{await panel.getByRole('button',{name:'＋ 新增环境记录'}).click()};
 const fill=async(id)=>{await panel.getByLabel('整条记录的来源口径（必选）').selectOption('Direct');await panel.getByLabel('观测编号（必填，案件内唯一）').fill(id);await panel.getByLabel('资料来源（必填）').fill('Synthetic source p. 1');await panel.getByLabel('原文与说明（必填）').fill('东北风4级，能见度良好\n保留原文')};
 const save=()=>panel.getByRole('button',{name:'保存环境记录',exact:true});
 const ready=()=>panel.getByRole('button',{name:'＋ 新增环境记录'}).waitFor();
 const goto=async(id)=>{await page.evaluate(x=>location.hash='#/env?case='+x,id);await ready()};
 const refresh=async()=>{await panel.getByRole('button',{name:'刷新已保存记录（放弃未保存输入）'}).click();await ready()};
 await page.goto((process.env.MCIS_W92_WEB_URL||'http://127.0.0.1:5192')+'/#/env?case=A');await ready();
 ok((await panel.innerText()).includes('尚未供仿真使用'),'honest boundary visible');ok((await panel.innerText()).includes('本案尚无环境观测记录'),'empty unknown');
 await open();await fill('OBS-1');await panel.getByLabel('能见度（nm）（可选）').fill('0');await save().click();await panel.getByText('环境记录已保存',{exact:true}).waitFor();
 ok(posts===1&&db.A[0].visibilityNm===0,'save preserves known zero');ok(db.A[0].observedAtUtc===null&&db.A[0].locationDescription===null&&!('windSpeedMps' in db.A[0]),'unknown never invented');
 ok((await panel.locator('.w92-record').innerText()).includes('未知'),'list shows unknown');await page.reload();await ready();ok(await panel.locator('.w92-record').count()===1,'reopen reads saved list');
 await open();await fill('OBS-1');await save().click();await panel.getByText(/观测编号已存在/).waitFor();ok(db.A.length===1,'conflict no overwrite');await panel.getByRole('button',{name:'取消 / 关闭'}).click();
 await open();await fill('OBS-2');await panel.getByLabel('观测时刻（UTC，可选）').fill('2023-02-29T12:00:00Z');const before=posts;await save().click();await panel.getByRole('alert').waitFor();ok(posts===before,'invalid real date blocked before request');await panel.getByLabel('观测时刻（UTC，可选）').fill('2024-02-29T12:00:00Z');await panel.getByLabel('风的来向（° 真北）（可选）').fill('90');await panel.getByLabel('水流去向（° 真北）（可选）').fill('180');mode='delay';await save().dblclick();await panel.getByText('环境记录已保存',{exact:true}).waitFor();ok(posts===before+1,'double click writes once');ok((await panel.locator('.w92-record').last().innerText()).includes('从该方向吹来')&&(await panel.locator('.w92-record').last().innerText()).includes('向该方向流去'),'direction distinction visible');
 await refresh();await open();await fill('OBS-3');mode='lost';const lostBefore=posts;await save().click();await panel.getByText(/保存结果尚未确认/).waitFor();ok(await save().count()===0,'unknown result no save retry control');await panel.getByRole('button',{name:'核查保存结果（只读）'}).click();await panel.getByText('环境记录已保存',{exact:true}).waitFor();ok(posts===lostBefore+1&&db.A.length===3,'read-only verification finds committed record without resend');
 mode='ok';await refresh();await open();await fill('CANCELLED');await panel.getByRole('button',{name:'取消 / 关闭'}).click();await open();ok(await panel.getByLabel('观测编号（必填，案件内唯一）').inputValue()==='','cancel clears form');ok(!db.A.some(x=>x.observationId==='CANCELLED'),'cancel no write');
 await fill('DENIED');mode='denied';await save().click();await panel.getByText(/当前身份或案件权限不允许新增/).waitFor();ok(!db.A.some(x=>x.observationId==='DENIED'),'write 403 visible');await panel.getByRole('button',{name:'取消 / 关闭'}).click();
 mode='delay';await open();await fill('LATE-A');await save().click();await goto('B');await page.waitForTimeout(850);ok(await panel.locator('.w92-record').count()===0&&!(await panel.innerText()).includes('LATE-A'),'late write isolated from new case');await goto('A');ok((await panel.innerText()).includes('LATE-A'),'return loads actual saved original case');
 await open();await fill('LATE-ROLE');await save().click();await page.locator('.role-select').selectOption('Public');await page.waitForTimeout(850);ok(await panel.getByRole('button',{name:'＋ 新增环境记录'}).count()===0,'role switch removes write controls');ok(!(await panel.innerText()).includes('环境记录已保存'),'old-role success not applied');await page.locator('.role-select').selectOption('Investigator');await ready();
 getMode='mismatch';await refresh().catch(()=>{});await panel.getByText(/无法加载环境记录/).waitFor();ok(await panel.locator('.w92-record').count()===0,'cross-case response rejected');getMode='ok';await panel.getByRole('button',{name:'重试',exact:true}).click();await ready();
 getMode='denied';await refresh().catch(()=>{});await panel.getByText(/当前身份无权读取/).waitFor();ok(await panel.locator('.w92-record').count()===0,'read forbidden hides records');getMode='ok';await panel.getByRole('button',{name:'重试',exact:true}).click();await ready();
 await goto('B');await open();await fill('UNSAVED');await goto('A');await page.goBack();await ready();ok(!(await panel.innerText()).includes('UNSAVED'),'Back returns clean case session');await page.goForward();await ready();ok((await panel.innerText()).includes('合成测试案件 A'),'Forward binds original case');
 // Literal attacker-controlled text is displayed, never interpreted as markup.
 db.A[0].description='<img src=x onerror="window.W92_XSS=1">'+'长文字'.repeat(300);await refresh();
 for(const width of [1440,768,390]){
  await page.setViewportSize({width,height:1000});await open();await fill('LAYOUT');await page.waitForTimeout(150);
  ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'no document overflow '+width);
  ok(await panel.evaluate(el=>el.scrollWidth<=el.clientWidth),'no environment overflow '+width);
  await page.screenshot({path:path.join(artifacts,'environment-'+width+'.png'),fullPage:true});await panel.getByRole('button',{name:'取消 / 关闭'}).click();
 }
 ok(!await page.evaluate(()=>window.W92_XSS),'source HTML escaped');ok(errors.length===0,'no runtime errors');
 console.log(`TOTAL ${count} PASS. Mock API UI tests; backend not assessed. Screenshots: ${artifacts}`);
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
