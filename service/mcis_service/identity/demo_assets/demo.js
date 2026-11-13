'use strict';
const nonce=document.querySelector('meta[name="demo-csrf"]').content;
const button=document.querySelector('#run'),status=document.querySelector('#status');
let busy=false,epoch=0;
const controls=[button,...document.querySelectorAll('input[name="choice"]')];
const setBusy=value=>{busy=value;controls.forEach(control=>{control.disabled=value;});};
const invalidate=()=>{epoch++;setBusy(false);document.querySelector('#result').hidden=true;document.querySelector('#empty').hidden=false;status.textContent='选择或页面已变化，旧结果已清除；已发出的演示可能仍在收尾。';};
window.addEventListener('pagehide',invalidate);
document.querySelectorAll('input[name="choice"]').forEach(input=>input.addEventListener('change',invalidate));
button.addEventListener('click',async()=>{
 if(busy)return;setBusy(true);const attempt=++epoch;
 document.querySelector('#result').hidden=true;document.querySelector('#empty').hidden=false;
 status.textContent='正在核查：受保护目录 → 选择版本 → 计算与临时保存 → 读取。';
 try{
  const choice=document.querySelector('input[name="choice"]:checked').value;
  const response=await fetch('/run',{method:'POST',credentials:'omit',cache:'no-store',redirect:'error',headers:{'Content-Type':'application/json','X-Demo-CSRF':nonce},body:JSON.stringify({choice})});
  if(!response.ok)throw Error(String(response.status));
  const value=await response.json();
  if(attempt!==epoch)return;
  const expected=choice==='both'?['EV-001','EV-002']:choice==='1'?['EV-001']:['EV-002'];
  if(value.fixture!=='fictional'||value.caseId!=='CASE-TRIAL-FICTIONAL'||value.saved!==true||value.read!==true||value.status!=='unreviewed'||value.observationApproval!=='not_assessed'||value.temporaryDataCleaned!==true||value.productionLogin!==false||value.networkListener!==false||value.sourceRelationship!=='not_verified'||value.coreImplementationVersionStatus!=='not_attested'||value.sourcesImported!==expected.length||JSON.stringify(value.selectedSourceIds)!==JSON.stringify(expected)||typeof value.runId!=='string'||!/^[-0-9a-f]{36}$/.test(value.runId)||!Array.isArray(value.conflicts)||value.conflicts.length>128||value.conflicts.some(c=>!c||typeof c.delta!=='number'||!Number.isFinite(c.delta)||c.deltaUnit!=='deg'))throw Error('shape');
  const deltas=value.conflicts.map(c=>c.delta).filter(n=>typeof n==='number'&&Number.isFinite(n));
  document.querySelector('#metric').textContent=deltas.length?`差异 ${deltas.join('、')}°`:'未列出冲突候选';
  document.querySelector('#summary').textContent=`已处理 ${value.sourcesImported} 份虚构来源。未审核；无冲突不代表证据一致。临时数据已清理。`;
  document.querySelector('#run-id').textContent=`本次演示编号：${value.runId}`;
  document.querySelector('#result').hidden=false;document.querySelector('#empty').hidden=true;
  status.textContent='演示完成。结果曾临时保存并读取，不保留正式案件。';
 }catch(error){if(attempt===epoch)status.textContent=error.message==='429'?'运行繁忙或已达五次上限；请等待或由本机操作者重启演示。':error.message==='410'?'演示已到期，请由本机操作者重新启动。':'本次演示未确认完成。请检查本机服务；不会回退到旧接口或模拟结果。';}
 finally{if(attempt===epoch){setBusy(false);}}
});
