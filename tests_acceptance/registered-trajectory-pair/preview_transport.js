'use strict';
// Preview-only finite frames from real synthetic registration/query; NO HTTP.
(() => {
 const frames=/* FRAMES */, api=globalThis.MCISRegisteredWorkbench;
 const el=id=>document.getElementById(id),copy=x=>JSON.parse(JSON.stringify(x));
 const config={caseId:frames[0].caseId,pins:frames[0].vessels.map(v=>v.original),times:frames.map(f=>f.alignedUtc)};
 let count=0,generation=0;
 const reader=async q=>{
  count++;el('preview-count').textContent='模拟查询次数：'+count;
  if(q.caseId!==config.caseId||JSON.stringify(q.pins)!==JSON.stringify(config.pins))throw {code:'ACCESS_DENIED'};
  const frame=frames.find(f=>f.alignedUtc===q.alignedUtc);if(!frame)throw Error('UNAVAILABLE');
  return copy(frame);
 };
 function reset(){generation++;api.attach(reader);api.selectCase(config);el('preview-event').textContent='重新选择合成案；尚未查询。';el('preview-slider').value='0';}
 el('preview-slider').oninput=()=>{el('time').value=config.times[Number(el('preview-slider').value)];el('time').oninput();};
 el('preview-reset').onclick=reset;
 el('preview-late').onclick=async()=>{
  const token=++generation;let resolve;
  api.attach(q=>{count++;el('preview-count').textContent='模拟查询次数：'+count;return new Promise(r=>resolve=r);});api.selectCase(config);
  const pending=api.load(config.times[0]);api.invalidate();
  el('preview-event').textContent='已离开当前案；等待旧合成响应，不能回填。';
  await new Promise(r=>setTimeout(r,250));resolve(copy(frames[0]));await pending;
  if(token===generation)el('preview-event').textContent='旧响应已到达并被忽略；没有当前案件或坐标。这里只阻止渲染，不撤回业务审计。';
 };
 reset();
})();
