// Invoked only by preview_browser.cjs --display-only; real browser, never a DOM shim.
'use strict';
const assert=require('node:assert/strict'),path=require('node:path');
module.exports=async({p,width,output,tabTo,slide,count,submit,cleared})=>{
 // Inspect the actual transport's serialized input, not merely visible text.
 const frames=await p.evaluate(()=>{
  const script=[...document.scripts].map(s=>s.textContent).find(s=>s.includes('const frames='));
  return JSON.parse(script.match(/const frames=(.*?), api=globalThis/)[1]);
 });
 const wire=JSON.stringify(frames);
 for(const key of ['original','pins','evidenceId','requestDigest','sourceSha256'])assert(!wire.includes(key));
 assert.equal(frames.length,2);
 assert.deepEqual(frames.map(f=>f.alignedUtc),['2026-02-01T12:01:40.000Z','2026-02-01T12:02:04.250Z']);
 await slide(0);await p.locator('#preview-slider').scrollIntoViewIfNeeded();
 const box=await p.locator('#preview-slider').boundingBox();assert(box&&box.width>20);
 await p.mouse.move(box.x+8,box.y+box.height/2);await p.mouse.down();
 await p.mouse.move(box.x+box.width-8,box.y+box.height/2,{steps:20});await p.mouse.up();
 assert.equal(await p.locator('#preview-slider').inputValue(),'1');assert.equal(await count(),0);await cleared();
 await slide(0);await p.keyboard.press('ArrowRight');await p.keyboard.press('ArrowLeft');assert.equal(await count(),0);
 await submit();await p.waitForFunction(()=>document.querySelectorAll('[data-current]').length===2);
 await tabTo('#source-a');await p.keyboard.press('Enter');
 assert.equal(await p.locator('#pointer').innerText(),'/points/7');assert.match(await p.locator('#quality').innerText(),/契约记录点/);assert.match(await p.locator('#warning').innerText(),/艏向未知/);
 await tabTo('#source-b');await p.keyboard.press('Enter');
 assert.equal(await p.locator('#pointer').innerText(),'/points/12');assert.equal(await p.locator('#source-time').innerText(),'2026-02-01T12:01:28.000Z');
 assert.equal(await p.locator('#aligned-time').innerText(),'2026-02-01T12:01:40.000Z');assert.equal(await p.locator('#correction').innerText(),'12 s');
 assert.match(await p.locator('#basis').innerText(),/校时依据未交付、人审未签/);assert.match(await p.locator('#basis').innerText(),/事件先后或同时仍未确定/);
 assert.equal(await p.locator('#file').innerText(),'服务定位 · 不显示内部标识');assert.match(await p.locator('#ref').innerText(),/仅展示服务提供的 JSON 路径/);
 await p.locator('[data-current]').nth(1).click();assert.equal(await p.locator('#pointer').innerText(),'/points/12');assert.equal(await count(),1);
 assert(await p.locator('#raw-open').isDisabled());await p.screenshot({path:path.join(output,`${width}-display-t100.png`),fullPage:true});
 await slide(1);await cleared();assert.equal(await count(),1);await submit();
 await p.waitForFunction(()=>document.getElementById('state-note').textContent.includes('无精确行'));
 assert.equal(await p.locator('[data-current]').count(),0);assert(await p.locator('#source-b').isDisabled());assert(await p.locator('#point-options button').nth(1).isDisabled());
 await tabTo('#source-a');await p.keyboard.press('Enter');assert.equal(await p.locator('#pointer').innerText(),'/sampling/missingIntervals/1');
 assert.equal(await p.locator('#source-time').innerText(),'—');assert.equal(await p.locator('#correction').innerText(),'—');assert.equal(await p.locator('#quality').innerText(),'声明缺轨');
 await p.screenshot({path:path.join(output,`${width}-display-gap.png`),fullPage:true});
 await p.locator('#preview-late').click();await p.waitForFunction(()=>document.getElementById('preview-event').textContent.includes('被忽略'));
 await cleared();assert.equal(await count(),3);assert.equal(await p.locator('#registered-case').innerText(),'未选案件');
};
