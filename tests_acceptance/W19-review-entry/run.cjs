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
  let versions,selected=0,requests=[],forbidden=[],errors=[]
  page.on('pageerror',e=>errors.push(e.message))
  await context.route('**/*',async route=>{
   const r=route.request(),u=new URL(r.url());requests.push({url:r.url(),method:r.method()})
   if(r.method()!=='GET'||u.origin!==origin){forbidden.push(r.url());return route.abort()}
   if(u.pathname==='/')return route.fulfill({contentType:'text/html',body:'<!doctype html><html lang="zh"><head><meta charset="utf-8"><link rel="icon" href="data:,"></head><body><div id="root"></div><script src="/entry.js"></script></body></html>'})
   if(u.pathname==='/entry.js')return route.fulfill({contentType:'application/javascript',body:built.outputFiles[0].text})
   if(u.pathname==='/api/v1/knowledge/cards'){
    const candidate=u.searchParams.get('status')==='Candidate'
    assert(!candidate||versions,'fixture must be frozen before user selection')
    return route.fulfill({contentType:'application/json',body:JSON.stringify({items:candidate?[versions[selected]]:[],total:candidate?1:0,limit:20,offset:0})})
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
  const details=card.locator('details').first()
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
  await page.waitForFunction(()=>document.querySelector('article.w19-card details').open)
  assert.equal(await card.locator('blockquote').isVisible(),true)
  assert.equal(await card.locator('blockquote').textContent(),versions[0].content.source.excerpt)
  assert.equal(requests.length,before,'opening causes no requests')
  assert.equal(await card.getByRole('button').count(),0,'Investigator has no review actions')
  // Same card ID, second fixed source version via actual page reload control.
  selected=1
  const reads=requests.filter(r=>r.url.includes('/api/v1/knowledge/cards')).length
  await page.getByRole('button',{name:'重新读取',exact:true}).click()
  await page.waitForFunction(d=>document.querySelector('article.w19-card')?.textContent.includes(d),versions[1].contentDigest)
  assert.equal(await card.locator('details').first().evaluate(e=>e.open),false)
  assert.equal(await card.locator('blockquote').isVisible(),false)
  assert.equal(await card.locator('blockquote').textContent(),versions[1].content.source.excerpt)
  assert(!(await card.textContent()).includes(versions[0].content.source.excerpt))
  assert.equal(requests.filter(r=>r.url.includes('/api/v1/knowledge/cards')).length,reads+1)
  assert.deepEqual(forbidden,[]);assert.deepEqual(errors,[])
  assert(requests.every(r=>r.method==='GET'))
  console.log(JSON.stringify({result:'PASS',sandbox:true,page:'actual KnowledgePage',api:'synthetic intercepted GET only',checks:['initial collapsed','Tab reachable','Enter opens','exact preloaded excerpt','opening adds zero requests','no review actions','same-card second-version reload collapsed','old excerpt removed','only one deliberate reload GET','no writes or unexpected requests'],realBackend:false,model:false}))
  await context.close()
 }finally{if(browser)await browser.close()}
}
main().catch(e=>{console.error('FAILED_OR_BLOCKED: '+e.message);process.exitCode=1})
