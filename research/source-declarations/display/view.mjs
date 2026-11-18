import {compareDeclarations} from '../compare.mjs';
// Explicit fixed paths, never inferred from array position, filename or matching values.
const paths={
 audio:['initial.machineDraft.source.evidenceId',['initial.machineDraft.source.currentSha256']],
 pdf:['initial.sourceVersions.pdf.evidenceId',['initial.candidate.source.pdf_sha256','initial.sourceVersions.pdf.sha256']],
 image:['initial.sourceVersions.image.evidenceId',['initial.candidate.source.image_sha256','initial.sourceVersions.image.sha256']],
 image_raw_output:['initial.sourceVersions.raw.evidenceId',['initial.sourceVersions.raw.sha256','initial.candidate.source.raw_sha256']],
 image_candidate:['initial.sourceVersions.candidate.evidenceId',['initial.sourceVersions.candidate.sha256']],
};
const escape=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels={present:'字段合法（不代表一致）',missing:'缺失',unknown_null:'未知（null）',empty:'空串',invalid:'非法'};
const value=f=>!f?'未比较／未返回字段':f.status==='missing'?'缺失':JSON.stringify(f.raw);
export function displayModel(input){
 const result=compareDeclarations(input);
 return {result,cards:result.results.map(r=>{
  const mapping=paths[r.selected?.sourceRole];
  // Only ID/hash differences may coexist with field comparisons. All other context,
  // history, selection or validity problems conservatively block row conclusions.
  const blocked=r.issues.some(i=>!['id_mismatch','digest_mismatch','source_inconsistent'].includes(i.code));
  const pairs=mapping?[
   ['interview.record.evidenceId','media.'+mapping[0],'id'],
   ...mapping[1].map(p=>['interview.record.sourceSha256','media.'+p,'digest'])]:[];
  return {result:r,rows:pairs.map(([left,right,kind])=>{
   const a=r.fields.find(f=>f.path===left),b=r.fields.find(f=>f.path===right);
   const allowed=!blocked&&a?.status==='present'&&b?.status==='present';
   const same=allowed&&(kind==='digest'?a.raw.toLowerCase()===b.raw.toLowerCase():a.raw===b.raw);
   return {left,right,a,b,status:!allowed?'不可比较':same?'声明值一致':'声明值不一致'};
  })};
 })};
}
const issues=(xs,aggregate=false)=>xs.length?'<ul>'+xs.map(i=>'<li>'+escape(i.code)+(i.path?'：'+escape(i.path):'')+(i.role?'：'+escape(i.role):'')+'</li>').join('')+'</ul>':(aggregate?'<p>无额外聚合问题；请查看各声明项问题。</p>':'<p>本声明项无报告问题；不代表已核验。</p>');
export function renderDeclarationView(input){
 const m=displayModel(input);
 return '<section><h1>合成来源声明比较</h1><p><strong>仅手造内存场景。未读取或核验原件，未证明人工批准，未建立关联。</strong></p><p>调用者历史不等于服务端完整历史；本原型无 API、上传、保存或关联功能。</p><h2>整体：'+(m.result.status==='declarations_equal'?'声明一致':'整体不可确定')+'</h2>'+issues(m.result.issues,true)+m.cards.map((c,index)=>'<article><h2>声明项 '+(index+1)+'：'+escape(c.result.selected?.sourceRole??'角色未知')+'</h2><p>单项状态：'+escape(c.result.status)+'</p>'+issues(c.result.issues)+'<table><caption>实际比较字段（单行一致不代表整体一致）</caption><thead><tr><th>笔录字段和值</th><th>运行字段和值</th><th>比较结论</th></tr></thead><tbody>'+c.rows.map(r=>'<tr><td>'+escape(r.left)+'<br>'+escape(value(r.a))+'</td><td>'+escape(r.right)+'<br>'+escape(value(r.b))+'</td><td>'+r.status+'</td></tr>').join('')+'</tbody></table>'+(!c.rows.length?'<p>不可比较：上下文不可用或角色未定义。</p>':'')+'<details open><summary>身份、字段有效性与原始声明</summary><ul>'+c.result.fields.map(f=>'<li>'+escape(f.path)+'：'+escape(labels[f.status]??'未知状态')+'；'+escape(value(f))+'</li>').join('')+'</ul></details></article>').join('')+'</section>';
}
