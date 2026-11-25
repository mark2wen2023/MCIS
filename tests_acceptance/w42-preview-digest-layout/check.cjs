'use strict';
const assert = require('node:assert/strict');
const {createHash} = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const BASE_BLOB = 'ae05f95847e710b0be98ee19963f833c20506138';
const anchor = '.page-scroll{max-height:55vh';
const fix = '.image-pane #preview-status{overflow-wrap:anywhere}';
const digest = 'ddd0'.repeat(16);
const sourceDigest = 'a5e1'.repeat(16);
const status = 'PDF派生页 · 物理页 1 · 原PDF SHA256 '+sourceDigest+' · 派生PNG SHA256 '+digest+'；不是登记原图、OCR结果或事实核验。';

const valid = ['--baseline', '--candidate', '--playwright', '--chromium', '--out'];
const args = process.argv.slice(2);
const opts = {};
while (args.length) {
  const [key,value] = args.splice(0,2);
  assert(valid.includes(key)&&!Object.hasOwn(opts,key)&&value&&!value.startsWith('--'),'invalid flags');
  opts[key] = path.resolve(value);
}
for (const key of ['--baseline','--candidate']) assert(opts[key],'missing '+key);
const previous = fs.readFileSync(opts['--baseline']);
const before = previous.toString('utf8');
assert.equal(createHash('sha1').update('blob '+previous.length+'\0').update(previous).digest('hex'),BASE_BLOB,'baseline bytes differ');
assert.equal(before.split(anchor).length,2);
const after = fs.readFileSync(opts['--candidate'],'utf8');
assert.equal(after,before.replace(anchor,fix+anchor),'expected exactly one scoped CSS rule and no DOM/script changes');
console.log('PASS fixed baseline and exact CSS-only change');
if (!opts['--playwright']) {
  assert(!opts['--chromium']&&!opts['--out'],'--chromium and --out require --playwright');
  console.log('BROWSER NOT RUN: static gate only');
  process.exit(0);
}

function inert(html) {
  // Keep the complete host markup and CSS. Prevent application actions,
  // API calls and access audits in this synthetic layout-only test.
  const result = html.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'');
  assert(!/<script\b/i.test(result));
  return result;
}

async function measure(page) {
  return page.locator('#preview-status').evaluate((p,needle)=>{
    const rect = value=>({left:value.left,right:value.right,top:value.top,bottom:value.bottom});
    const r = document.createRange(), node = p.firstChild;
    const start = node.textContent.indexOf(needle);
    r.setStart(node,start);
    r.setEnd(node,start+needle.length);
    return {
      status:p.textContent, statusBox:rect(p.getBoundingClientRect()),
      fragments:Array.from(r.getClientRects(),rect),
      viewportWidth:document.documentElement.clientWidth, documentWidth:document.documentElement.scrollWidth,
      accessibleRole:p.getAttribute('role'),
      canvasLabels:[...document.querySelectorAll('.image-pane canvas')].map(c=>c.getAttribute('aria-label')),
    };
  },digest);
}

async function main() {
  const {chromium}=require(opts['--playwright']);
  const browser=await chromium.launch({
    headless:true,chromiumSandbox:true,timeout:15000,
    ...(opts['--chromium']?{executablePath:opts['--chromium']}:{})
  });
  const report=[];
  try {
    if (opts['--out']) fs.mkdirSync(opts['--out']);
    for (const width of [390,1440]) {
      const context=await browser.newContext({offline:true,serviceWorkers:'block',viewport:{width,height:900}});
      try {
        for (const [mode,html] of [['baseline',before],['candidate',after]]) {
          const page=await context.newPage(), errors=[], requests=[];
          page.on('pageerror',error=>errors.push(error.message));
          page.on('console',msg=>{if(msg.type()==='error') errors.push(msg.text());});
          page.on('request',request=>requests.push(request.url()));
          await page.setContent(inert(html),{waitUntil:'load'});
          assert.equal(await page.title(),'图片文字核对候选');
          await page.locator('#preview-status').evaluate((p,next)=>{p.textContent=next;},status);
          const m=await measure(page);
          assert.equal(m.status,status);
          assert.equal(m.accessibleRole,'status');
          assert.deepEqual(m.canvasLabels,['选中行邻近原图','整页原图及所选OCR框']);
          assert.equal(m.viewportWidth,width);
          assert(m.fragments.length>0);
          const contained=m.fragments.every(r=>r.left>=m.statusBox.left-1&&r.right<=m.statusBox.right+1);
          const lineCount=new Set(m.fragments.map(r=>Math.round(r.top))).size;
          if (mode==='baseline'&&width===390) assert(!contained,'negative control did not reproduce baseline overflow');
          if (mode==='candidate') {
            assert(contained,'digest overflows its status element');
            assert.equal(m.documentWidth,m.viewportWidth,'page has horizontal overflow');
            if (width===390) assert(lineCount>=2,'narrow digest not wrapped');
            else assert.equal(lineCount,1,'desktop digest unexpectedly wraps');
          }
          assert.deepEqual(errors,[]);
          assert.deepEqual(requests,[]);
          if(opts['--out']) await page.screenshot({path:path.join(opts['--out'],mode+'-'+width+'.png')});
          report.push({mode,width,contained,lineCount,pageScrollWidth:m.documentWidth});
          await page.close();
        }
      } finally { await context.close(); }
    }
    console.log(JSON.stringify({browser:browser.version(),viewports:report},null,2));
  } finally { await browser.close(); }
}
main().catch(err=>{console.error(err);process.exitCode=1;});
