// Receipt B: real Chromium (normal sandbox) -> real Vite dev (29cbfe2 web) -> real uvicorn (29cbfe2 service).
// No page.route, no fetch mocks. Late responses are produced by the backend's test-only ASGI delay (after the real handler ran).
const assert=require('node:assert/strict');const fs=require('node:fs');const http=require('node:http');const {execFileSync}=require('node:child_process');
const [pw,exe,readyPath,front,vp,shots,tag]=process.argv.slice(2);const ready=JSON.parse(fs.readFileSync(readyPath));const {chromium}=require(pw);
const [W,H]=vp.split('x').map(Number);const steps=[];let stage='launch';const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const delay=(paths,seconds,remaining)=>fs.writeFileSync(ready.delayFile,JSON.stringify({paths,seconds,remaining}));
const ctl=p=>new Promise((res,rej)=>http.get(ready.origin+p,r=>{let b='';r.on('data',d=>b+=d);r.on('end',()=>res(b));}).on('error',rej));
const db=()=>JSON.parse(execFileSync('python3',['-c',`import sqlite3,json;c=sqlite3.connect('file:${ready.db}?mode=ro',uri=True);print(json.dumps(dict(custody=c.execute("select case_id,evidence_id,kind from custody_events order by id").fetchall(),audit=c.execute("select count(*) from audit_events").fetchone()[0])))`]).toString());
(async()=>{
 const browser=await chromium.launch({executablePath:exe,headless:true,chromiumSandbox:true});
 const ctx=await browser.newContext({viewport:{width:W,height:H},serviceWorkers:'block'});
 await ctx.addInitScript(()=>{if(!sessionStorage.getItem('w17init')){localStorage.setItem('mcis.role','LeadInvestigator');localStorage.setItem('mcis.operator','synthetic-reader');sessionStorage.setItem('w17init','1');}});
 const page=await ctx.newPage();const reqs=[],resps=[],errors=[],external=[];
 page.on('request',r=>{const u=r.url();if(!u.startsWith(front))external.push(u);if(u.includes('/api/'))reqs.push({m:r.method(),p:u.replace(front,'')});});
 page.on('response',r=>{if(r.url().includes('/api/'))resps.push({p:r.url().replace(front,''),s:r.status()});});
 page.on('pageerror',e=>errors.push(e.message));
 const body=()=>page.locator('body').innerText();const btn=n=>page.getByRole('button',{name:n,exact:true});
 const nav=c=>page.evaluate(c=>{location.hash='/evidence?case='+c},c);
 const shot=async n=>{await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));await page.screenshot({path:`${shots}/${tag}-${n}.png`,fullPage:false});};
 const OPEN='＋ 登记已有文件副本 / 查看登记原件',READ='读取当前证据登记回执（只读）',CHAIN='保管链 · EV-001';
 await page.goto(front+'/#/evidence?case=SYN-A');
 {const ps=execFileSync('ps',['-eo','pid,args']).toString().split('\n').filter(l=>l.includes('/opt/google/chrome/'));const rend=ps.filter(l=>/--type=renderer/.test(l));let sec=null,nnp=null;if(rend[0]){const st=fs.readFileSync('/proc/'+rend[0].trim().split(' ')[0]+'/status','utf8');sec=(st.match(/Seccomp:\s*(\d+)/)||[])[1];nnp=(st.match(/NoNewPrivs:\s*(\d+)/)||[])[1];}
  steps.push({step:'sandbox',browser:browser.version(),noSandboxFlag:ps.some(l=>/--no-sandbox|--disable-setuid-sandbox/.test(l)),renderers:rend.length,seccomp:sec,noNewPrivs:nnp});assert.equal(steps[0].noSandboxFlag,false);}
 // 1 initial: list visible, nothing selected, no custody read
 stage='initial';await btn('SOURCE-SYN-A').waitFor();await page.getByText('请选择证据',{exact:true}).waitFor();
 assert.ok(!reqs.some(r=>r.p.endsWith('/EV-001/custody')));await shot('1-A-list-no-selection');steps.push({step:stage,pass:true});
 // 2 explicit selection drives custody read
 stage='explicit_select_A';{const w=page.waitForResponse(r=>r.url().endsWith('/api/v1/cases/SYN-A/evidence/EV-001/custody'));await btn('SOURCE-SYN-A').click();assert.equal((await w).status(),200);}await page.getByText(CHAIN,{exact:true}).waitFor();await shot('2-A-selected-custody');steps.push({step:stage,pass:true});
 // 3 case switch B->A->B with the first two list responses delayed by the backend
 stage='case_switch_late_lists';delay(['/api/v1/cases/SYN-B/evidence','/api/v1/cases/SYN-A/evidence'],4,2);
 const late1=page.waitForResponse(r=>r.url().endsWith('/api/v1/cases/SYN-B/evidence'),{timeout:20000});await nav('SYN-B');await sleep(300);
 const late2=page.waitForResponse(r=>r.url().endsWith('/api/v1/cases/SYN-A/evidence'),{timeout:20000});await nav('SYN-A');await sleep(300);
 assert.ok(!(await body()).includes('SOURCE-SYN-A'),'old A list must be cleared while A list is pending');
 await nav('SYN-B');await btn('SOURCE-SYN-B').waitFor();
 let t=await body();assert.ok(t.includes('请选择证据')&&!t.includes(CHAIN)&&!t.includes('SOURCE-SYN-A'));
 assert.ok(!reqs.some(r=>r.p==='/api/v1/cases/SYN-B/evidence/EV-001/custody'));
 const [l1,l2]=await Promise.all([late1,late2]);await sleep(600);t=await body();
 assert.ok(t.includes('SOURCE-SYN-B')&&t.includes('请选择证据')&&!t.includes('SOURCE-SYN-A')&&!t.includes(CHAIN));
 await shot('3-B-after-late-A-B-lists');steps.push({step:stage,pass:true,lateStatuses:[l1.status(),l2.status()]});
 // 4 explicit select B, then receipt read
 stage='receipt_B';{const w=page.waitForResponse(r=>r.url().endsWith('/api/v1/cases/SYN-B/evidence/EV-001/custody'));await btn('SOURCE-SYN-B').click();assert.equal((await w).status(),200);}await page.getByText(CHAIN,{exact:true}).waitFor();
 await btn(OPEN).click();assert.ok(!reqs.some(r=>r.p.endsWith('/intake')));{const w=page.waitForResponse(r=>r.url().endsWith('/SYN-B/evidence/EV-001/intake'));await btn(READ).click();assert.equal((await w).status(),200);}
 await page.locator('.w42-receipt').waitFor();let rc=await page.locator('.w42-receipt').innerText();
 assert.ok(rc.includes('SYN-B.txt')&&rc.includes(ready.registered['SYN-B'].sourceSha256)&&rc.includes(ready.registered['SYN-B'].requestDigest)&&!rc.includes('SYN-A.txt'));
 await page.locator('.w42-receipt').scrollIntoViewIfNeeded();await shot('4-B-receipt');steps.push({step:stage,pass:true});
 // 5 stale receipt: A read delayed, switch to B before it arrives
 stage='stale_receipt_A';await nav('SYN-A');await btn('SOURCE-SYN-A').click();await page.getByText(CHAIN,{exact:true}).waitFor();await btn(OPEN).click();
 delay(['/api/v1/cases/SYN-A/evidence/EV-001/intake'],3,1);const lateR=new Promise(res=>{const m=r=>r.url().endsWith('/SYN-A/evidence/EV-001/intake');page.on('requestfinished',async r=>{if(m(r)){const x=await r.response();res({outcome:'delivered',status:x&&x.status()});}});page.on('requestfailed',r=>{if(m(r))res({outcome:'aborted_by_page',failure:r.failure()&&r.failure().errorText});});});
 await btn(READ).click();await sleep(300);await nav('SYN-B');await btn('SOURCE-SYN-B').waitFor();
 const lr=await lateR;await sleep(3600);t=await body();
 assert.equal(await page.locator('.w42-receipt').count(),0);assert.ok(!t.includes('SYN-A.txt')&&t.includes('请选择证据'));
 await shot('5-B-after-late-A-receipt');steps.push({step:stage,pass:true,late:lr});
 // 6 Public identity: denied, no B metadata
 stage='public_denied';await page.locator('select[title="X-MCIS-Role"]').selectOption('Public');
 await page.waitForFunction(()=>!document.body.innerText.includes('SOURCE-SYN-B'));await sleep(800);t=await body();
 assert.ok(!t.includes('SOURCE-SYN-B'));await page.waitForFunction(()=>true);assert.ok(resps.some(r=>r.p==='/api/v1/cases/SYN-B/evidence'&&r.s===403),'expected a 403 list response under Public');
 await shot('6-public-denied');steps.push({step:stage,pass:true});
 // 7 policy revoked for LeadInvestigator on SYN-B after selection -> read shows alert, no receipt
 stage='revoked_policy';await page.locator('select[title="X-MCIS-Role"]').selectOption('LeadInvestigator');await btn('SOURCE-SYN-B').waitFor();
 await btn('SOURCE-SYN-B').click();await page.getByText(CHAIN,{exact:true}).waitFor();await btn(OPEN).click();
 await ctl('/__w17ctl/denyB');{const w=page.waitForResponse(r=>r.url().endsWith('/SYN-B/evidence/EV-001/intake'));await btn(READ).click();assert.equal((await w).status(),403);}await page.locator('[role="alert"]').first().waitFor();await sleep(300);
 assert.equal(await page.locator('.w42-receipt').count(),0);const lastIntake=resps.filter(r=>r.p.endsWith('/intake')).at(-1);assert.equal(lastIntake.s,403);
 await shot('7-revoked-alert');steps.push({step:stage,pass:true});
 // global
 stage='global';const writes=reqs.filter(r=>r.m!=='GET');const forbidden=reqs.filter(r=>/download|\/content|:commit|:preview/.test(r.p));
 assert.deepEqual(writes,[]);assert.deepEqual(forbidden,[]);assert.deepEqual(external,[]);
 const d=db();assert.deepEqual(d.custody.map(x=>x[2]),['Register','Register']);
 await browser.close();
 console.log(JSON.stringify({passed:true,viewport:vp,steps,writes:writes.length,external:external.length,pageErrors:errors,sqlite:d,apiRequests:reqs.length}));
})().catch(e=>{console.log(JSON.stringify({passed:false,stage,error:String(e&&e.stack||e).slice(0,1500),steps}));process.exit(1);});
