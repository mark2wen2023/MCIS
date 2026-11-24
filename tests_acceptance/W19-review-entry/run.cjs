// Actual KnowledgePage in sandboxed Chromium; API responses are explicit synthetic doubles.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict')
const root=path.resolve(__dirname,'../..')
const flag=n=>{const i=process.argv.indexOf(n);return i<0?undefined:process.argv[i+1]}
const deps=path.resolve(flag('--web-deps')||path.join(root,'web/node_modules'))
const esbuild=require(path.join(deps,'esbuild'))
const {chromium}=require(flag('--playwright')||'playwright')
const origin='http://127.0.0.1:18793'
const hash=x=>crypto.createHash('sha256').update(x).digest('hex')
async function main(){
 const pins=JSON.parse(fs.readFileSync(path.join(__dirname,'pins.json'),'utf8'))
 for(const [name,expected] of Object.entries(pins)){
  const raw=fs.readFileSync(path.join(root,name))
  assert.equal(crypto.createHash('sha1').update('blob '+raw.length+'\0').update(raw).digest('hex'),expected,'fixed source '+name)
 }
 const built=await esbuild.build({entryPoints:[path.join(__dirname,'entry.tsx')],bundle:true,platform:'browser',format:'iife',jsx:'automatic',write:false,nodePaths:[deps],loader:{'.css':'empty'},logLevel:'warning'})
 if(process.argv.includes('--check-build')){console.log(JSON.stringify({build:'PASS',browser:'NOT_RUN',pinnedFiles:Object.keys(pins).length}));return}
 let browser
 try{
  browser=await chromium.launch({headless:true,chromiumSandbox:true,...(flag('--chromium')?{executablePath:flag('--chromium')}:{})})
  const context=await browser.newContext({serviceWorkers:'block'})
  const page=await context.newPage();page.setDefaultTimeout(8000)
  let versions,selected=0,requests=[],forbidden=[],errors=[],raceMode=false,held=[]
  // Explicit transport double: ensure a stale synthetic response reaches parsing
  // even after the application aborts its effect; cancellation guard must reject it.
  await page.addInitScript(()=>{
   const original=window.fetch.bind(window)
   window.__parsedQueries=[]
   window.fetch=async(input,options)=>{
    const url=new URL(typeof input==='string'?input:input.url,location.href)
    if(url.origin!==location.origin||url.pathname!=='/api/v1/knowledge/cards')return original(input,options)
    const copy={...options};delete copy.signal
    const response=await original(input,copy),parse=response.json.bind(response)
    response.json=async()=>{const value=await parse();window.__parsedQueries.push(url.search);return value}
    return response
   }
  })
  page.on('pageerror',e=>errors.push(e.message))
  await context.route('**/*',async route=>{
   const r=route.request(),u=new URL(r.url());requests.push({url:r.url(),method:r.method()})
   if(r.method()!=='GET'||u.origin!==origin){forbidden.push(r.url());return route.abort()}
   if(u.pathname==='/')return route.fulfill({contentType:'text/html',body:'<!doctype html><html lang="zh"><head><meta charset="utf-8"><link rel="icon" href="data:,"></head><body><div id="root"></div><script src="/entry.js"></script></body></html>'})
   if(u.pathname==='/entry.js')return route.fulfill({contentType:'application/javascript',body:built.outputFiles[0].text})
   if(u.pathname==='/api/v1/knowledge/cards'){
    const candidate=u.searchParams.get('status')==='Candidate'
    assert(!candidate||versions,'fixture must be frozen before user selection')
    const status=u.searchParams.get('status'),query=u.searchParams.get('q')||''
    if(raceMode&&candidate&&query==='告警'){
     await new Promise(resolve=>held.push({resolve,url:r.url()}))
     return route.fulfill({contentType:'application/json',body:JSON.stringify({items:[versions[0]],total:1,limit:20,offset:0})})
    }
    const shown=candidate||raceMode&&status==='Published'&&query==='告警'
    const item=shown?{...versions[selected],status}:null
    return route.fulfill({contentType:'application/json',body:JSON.stringify({items:shown?[item]:[],total:shown?1:0,limit:20,offset:0})})
   }
   forbidden.push(r.url());return route.abort()
  })
  await page.goto(origin+'/#/knowledge')
  await page.getByRole('heading',{name:'案例、疑难与方法知识卡',exact:true}).waitFor()
  versions=await page.evaluate(()=>window.__reviewFixture)
  for(const v of versions){delete v.version;v.contentDigest=hash(JSON.stringify(v.content))}
  await page.getByLabel('资料状态').selectOption('Candidate')
  const card=page.locator('article.w19-card')
  const summary=card.locator('summary').filter({hasText:'进入待审核查'})
  await summary.waitFor();assert.equal(await card.count(),1)
  const details=summary.locator('..')
  assert.equal(await details.evaluate(e=>e.open),false)
  assert.equal(await card.locator('blockquote').isVisible(),false)
  const before=requests.length
  // Start keyboard traversal outside controls. Do not click/evaluate the summary.
  await page.locator('h1').evaluate(e=>{e.setAttribute('tabindex','-1');e.focus()})
  let reached=false
  for(let i=0;i<80;i++){
   await page.keyboard.press('Tab')
   if(await summary.evaluate(e=>document.activeElement===e)){reached=true;break}
  }
  assert(reached,'summary keyboard reachable')
  await page.keyboard.press('Enter')
  await page.waitForFunction(()=>Array.from(document.querySelectorAll('article.w19-card summary')).find(e=>e.textContent.includes('进入待审核查'))?.parentElement.open)
  assert.equal(await card.locator('blockquote').isVisible(),true)
  assert.equal(await card.locator('blockquote').textContent(),versions[0].content.source.excerpt)
  assert.equal(requests.length,before,'opening causes no requests')
  assert.equal(await card.getByRole('button').count(),0,'Investigator has no review actions')
  // Same card ID, second fixed source version via actual page reload control.
  selected=1
  const reads=requests.filter(r=>r.url.includes('/api/v1/knowledge/cards')).length
  await page.getByRole('button',{name:'重新读取',exact:true}).click()
  await page.waitForFunction(d=>document.querySelector('article.w19-card')?.textContent.includes(d),versions[1].contentDigest)
  assert.equal(await summary.locator('..').evaluate(e=>e.open),false)
  assert.equal(await card.locator('blockquote').isVisible(),false)
  assert.equal(await card.locator('blockquote').textContent(),versions[1].content.source.excerpt)
  assert(!(await card.textContent()).includes(versions[0].content.source.excerpt))
  assert.equal(requests.filter(r=>r.url.includes('/api/v1/knowledge/cards')).length,reads+1)
  // New search-reason scenarios use the actual page controls and applied response.
  raceMode=true
  await page.getByLabel('字面关键词',{exact:true}).fill('原因未核')
  await page.getByRole('button',{name:'检索',exact:true}).click()
  const reason=card.locator('details[aria-label="本次返回原因"]')
  await page.waitForFunction(()=>document.querySelector('article.w19-card details[aria-label="本次返回原因"]')?.textContent.includes('原因未核'))
  const oldReason=await reason.textContent(),beforeEdit=requests.length
  await page.getByLabel('字面关键词',{exact:true}).fill('告警')
  assert.equal(await reason.textContent(),oldReason,'unsubmitted edit keeps old applied reason')
  assert.equal(requests.length,beforeEdit,'editing does not fetch')
  await page.getByRole('button',{name:'检索',exact:true}).click()
  await page.getByText('读取知识卡…',{exact:true}).waitFor()
  assert.equal(await card.count(),0,'no old rows or reasons during new-query loading')
  // Search button is disabled while loading; status switch is an existing allowed control.
  await page.getByLabel('资料状态').selectOption('Published')
  await page.waitForFunction(()=>document.querySelector('article.w19-card details[aria-label="本次返回原因"]')?.textContent.includes('告警'))
  assert.equal(held.length,1,'exactly one old Candidate request is held')
  const currentReason=await reason.textContent(),currentCard=await card.textContent()
  assert(currentReason.includes('已发布')&&!currentReason.includes('原因未核'))
  held[0].resolve()
  await page.waitForFunction(()=>window.__parsedQueries.some(s=>{const q=new URLSearchParams(s);return q.get('status')==='Candidate'&&q.get('q')==='告警'}))
  // Let the async continuation and React render settle after the stale JSON was parsed.
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))
  assert.equal(await reason.textContent(),currentReason,'late parsed Candidate must not replace Published reason')
  assert.equal(await card.textContent(),currentCard,'late parsed old card must not replace current card')
  assert.deepEqual(forbidden,[]);assert.deepEqual(errors,[])
  assert(requests.every(r=>r.method==='GET'))
  console.log(JSON.stringify({result:'PASS',sandbox:true,page:'actual KnowledgePage',api:'synthetic intercepted GET only',checks:['initial collapsed','Tab reachable','Enter opens','exact preloaded excerpt','opening adds zero requests','no review actions','same-card second-version reload collapsed','old excerpt removed','only one deliberate reload GET','no writes or unexpected requests','unsubmitted edit keeps prior explanation','new query loading clears old result','late parsed response cannot replace current result'],abortSignalIgnoredByTestTransport:true,realBackend:false,model:false}))
  await context.close()
 }finally{if(browser)await browser.close()}
}
main().catch(e=>{console.error('FAILED_OR_BLOCKED: '+e.message);process.exitCode=1})
