// Supplemental: screenshot #preview-status after scroll-into-view. Not a substitute for check.cjs.
'use strict';
const fs=require('fs');const path=require('path');
const {chromium}=require('/usr/local/lib/pnpm/5/.pnpm/playwright@1.63.0-alpha-2026-08-31/node_modules/playwright');
const digest='ddd0'.repeat(16), sourceDigest='a5e1'.repeat(16);
const status='PDF派生页 · 物理页 1 · 原PDF SHA256 '+sourceDigest+' · 派生PNG SHA256 '+digest+'；不是登记原图、OCR结果或事实核验。';
const before=fs.readFileSync('/workspace/mcis-w42-base-3ae5166/service/mcis_service/image_review/review.html','utf8');
const after=fs.readFileSync('/workspace/mcis-w42-b2bc858/service/mcis_service/image_review/review.html','utf8');
function inert(html){return html.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'');}
(async()=>{
  const browser=await chromium.launch({headless:true,chromiumSandbox:true,executablePath:'/opt/google/chrome/google-chrome'});
  const out='/workspace/mcis-w42-report/screenshots/status-element'; fs.mkdirSync(out,{recursive:true});
  for (const width of [390,1440]) {
    const ctx=await browser.newContext({offline:true,serviceWorkers:'block',viewport:{width,height:900}});
    for (const [mode,html] of [['baseline',before],['candidate',after]]) {
      const page=await ctx.newPage();
      await page.setContent(inert(html),{waitUntil:'load'});
      await page.locator('#preview-status').evaluate((p,next)=>{p.textContent=next;},status);
      await page.locator('#preview-status').scrollIntoViewIfNeeded();
      await page.locator('#preview-status').screenshot({path:path.join(out,mode+'-'+width+'-status-el.png')});
      const m=await page.locator('#preview-status').evaluate((p,needle)=>{
        const r=document.createRange(),node=p.firstChild,start=node.textContent.indexOf(needle);
        r.setStart(node,start);r.setEnd(node,start+needle.length);
        return {text:p.textContent,box:p.getBoundingClientRect(),nRects:[...r.getClientRects()].length,scrollW:document.documentElement.scrollWidth,clientW:document.documentElement.clientWidth};
      },digest);
      console.log(JSON.stringify({mode,width,...m,textLen:m.text.length}));
      await page.close();
    }
    await ctx.close();
  }
  await browser.close();
})();
