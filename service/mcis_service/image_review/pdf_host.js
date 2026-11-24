/* Synthetic-only host bridge. Request generation is independent of decoder generation. */
(function(root){
'use strict';
function create({preview,lines,current,request}){
 let generation=0;
 function clear(){generation++;preview.clear();lines.hidden=false;for(const row of lines.children){row.classList.remove('selected');row.querySelector('[aria-pressed]')?.setAttribute('aria-pressed','false');}}
 function equal(a,b){return !!a&&!!b&&['caseId','runId','revision','sourceSha256','physicalPage'].every(k=>a[k]===b[k]);}
 async function load(){
  clear();const token=generation;const expected=current();
  if(!expected||expected.caseId!=='SYN-XREPO-001'||expected.physicalPage!==1)throw Error('请先读取匹配的合成审阅运行');
  lines.hidden=true;
  try{
   const d=await request(expected);
   if(token!==generation)return;
   if(!equal(expected,current()))throw Error('当前案、运行或版本已变化');
   if(!d||d.caseId!==expected.caseId||d.runId!==expected.runId||d.revision!==expected.revision
     ||d.description?.sourceSha256!==expected.sourceSha256||d.description?.physicalPage!==expected.physicalPage
     ||typeof d.pngBase64!=='string'||d.pngBase64.length>1400000)throw Error('派生页绑定不符');
   const bytes=Uint8Array.from(atob(d.pngBase64),c=>c.charCodeAt(0));
   await preview.loadDerived(bytes,d.description);
   if(token!==generation)return;
   if(!equal(expected,current()))throw Error('当前版本已变化');
  }catch(e){if(token===generation){clear();throw e;}}
 }
 return {load,clear,version:()=>generation};
}
root.SyntheticPdfHost={create};
})(typeof module==='object'?module.exports:globalThis);
