'use strict';
// Alternate binding of the existing shell, NEVER loaded by the frozen demo.
// No transport, credential storage, cached authority or automatic query.
(() => {
 const DISPLAY_ONLY = false; // Set only by explicit offline shell construction.
 const el=id=>document.getElementById(id), text=(id,v)=>{el(id).textContent=v;};
 const node=(parent,tag,v)=>{const n=document.createElement(tag);n.textContent=v;parent.appendChild(n);return n;};
 const svg=(parent,tag,attrs)=>{const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));parent.appendChild(n);return n;};
 const utc=s=>typeof s==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z$/.test(s)&&Number.isFinite(Date.parse(s))&&new Date(s).toISOString()===(s.length===20?s.slice(0,-1)+'.000Z':s);
 const id=s=>typeof s==='string'&&/^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$/.test(s), digest=s=>typeof s==='string'&&/^[a-f0-9]{64}$/.test(s);
 const keys=(o,names)=>o!==null&&typeof o==='object'&&!Array.isArray(o)&&Object.keys(o).sort().join('|')===[...names].sort().join('|');
 const quality={recorded:'契约记录点 · 未认证',interpolated:'契约已存插值 · 非本次计算',calculated:'契约计算值',manual_assumption:'人工假设值',schematic:'示意值',missing:'缺失'};
 const pinKeys=['caseId','evidenceId','requestDigest','sourceSha256'],clone=o=>JSON.parse(JSON.stringify(o));
 const goodPin=(p,c)=>keys(p,pinKeys)&&p.caseId===c&&id(p.evidenceId)&&digest(p.requestDigest)&&digest(p.sourceSha256);
 const assert=b=>{if(!b)throw new Error('INVALID_MODEL');};
 function validate(r,s,t){
  assert(keys(r,['caseId','alignedUtc','vessels','authenticityVerified','collisionDetermined'])&&r.caseId===s.caseId&&r.alignedUtc===t&&r.authenticityVerified===false&&r.collisionDetermined===false);
  assert(Array.isArray(r.vessels)&&r.vessels.length===2);const seen=new Set();
  r.vessels.forEach((v,i)=>{
   assert(keys(v,['vesselId','position','headingDeg','courseDeg','time','courseUsedAsHeading','collisionAngle',...(DISPLAY_ONLY?[]:['original']),'locator','status',...(v.status==='declared_gap'?['gap']:[])]));
   assert(typeof v.vesselId==='string'&&v.vesselId.length>0&&v.vesselId.length<=128&&!seen.has(v.vesselId));seen.add(v.vesselId);
   assert((DISPLAY_ONLY?v.vesselId===s.vesselIds[i]:goodPin(v.original,s.caseId)&&pinKeys.every(k=>v.original[k]===s.pins[i][k]))&&v.courseUsedAsHeading===false&&v.collisionAngle===null);
   if(v.status==='input_point'){
    assert(keys(v.locator,['jsonPointer'])&&/^\/points\/(0|[1-9]\d*)$/.test(v.locator.jsonPointer));
    assert(keys(v.time,['sourceUtc','alignedUtc','correctionSeconds','status'])&&utc(v.time.sourceUtc)&&v.time.alignedUtc===t&&['referenced','corrected'].includes(v.time.status));
    assert(Number.isFinite(v.time.correctionSeconds)&&Date.parse(v.time.sourceUtc)+v.time.correctionSeconds*1000===Date.parse(t)&&(v.time.status!=='referenced'||v.time.correctionSeconds===0));
    for(const f of ['position','headingDeg','courseDeg']){assert(keys(v[f],['value','kind'])&&Object.hasOwn(quality,v[f].kind));assert((v[f].kind==='missing')===(v[f].value===null));}
    const p=v.position.value;assert(p&&keys(p,['latDeg','lonDeg'])&&Number.isFinite(p.latDeg)&&Math.abs(p.latDeg)<=90&&Number.isFinite(p.lonDeg)&&Math.abs(p.lonDeg)<=180);
    for(const f of ['headingDeg','courseDeg'])assert(v[f].value===null||(Number.isFinite(v[f].value)&&v[f].value>=0&&v[f].value<360));
   }else{
    assert(v.position===null&&v.headingDeg===null&&v.courseDeg===null&&v.time===null);
    if(v.status==='declared_gap'){
     assert(keys(v.gap,['startUtc','endUtc'])&&utc(v.gap.startUtc)&&utc(v.gap.endUtc)&&Date.parse(v.gap.startUtc)<Date.parse(t)&&Date.parse(t)<Date.parse(v.gap.endUtc));
     assert(keys(v.locator,['jsonPointer'])&&/^\/sampling\/missingIntervals\/(0|[1-9]\d*)$/.test(v.locator.jsonPointer));
    }else assert(v.status==='no_observation_at_time'&&v.locator===null);
   }
  });return clone(r);
 }
 let query=null,selection=null,epoch=0,serial=0,current=null,everReady=false,flight=null;
 function clear(message){
  current=null;for(const key of ['map','timeline','point-options'])el(key).replaceChildren();
  for(const key of ['record-id','raw-time','source-time','correction','aligned-time','pointer','ref','clock'])text(key,'—');
  text('evidence-title','未显示登记证据');text('quality','未选择');text('file','未选择证据');text('basis','原文与校时依据须另经授权读取。');text('raw','本模式不返回原文。');
  text('warning-title','访问边界');text('warning','当前模型不构成原件真实性或碰撞判定。');text('state-note',message);
  el('raw-open').disabled=true;el('raw-details').open=false;
  for(const key of ['source-a','source-b','device-known','device-unknown']){el(key).disabled=true;el(key).onclick=null;}
  text('source-a','第一份原件 · 未载入');text('source-b','第二份原件 · 未载入');
 }
 function controls(){const i=selection?selection.times.indexOf(el('time').value):-1;el('time').disabled=!query||!selection;el('registered-load').disabled=!query||!selection||(flight?.epoch===epoch&&flight?.time===el('time').value);el('prev').disabled=i<=0;el('next').disabled=!selection||i<0||i===selection.times.length-1;}
 function detail(v,token){
  if(token!==serial||!current||!selection)return;
  text('evidence-title',v.vesselId);text('record-id',v.locator?.jsonPointer??'无精确记录');text('quality',v.status==='declared_gap'?'声明缺轨':quality[v.position.kind]);
  text('raw-time','本模型未返回');text('source-time',v.time?.sourceUtc??'—');text('aligned-time',current.alignedUtc);text('correction',v.time?String(v.time.correctionSeconds)+' s':'—');
  text('basis',v.time?'校时数值为来源声明，待人工复核；校时依据未交付、人审未签。等时仅为展示对齐，事件先后或同时仍未确定。':'声明缺轨范围不是位置观测；本模型没有可复核的该时点记录。');
  text('file','服务定位 · 不显示内部标识');text('pointer',v.locator?.jsonPointer??'没有对应点行');text('ref','仅展示服务提供的 JSON 路径；内部固定定位已作一致性校验，不代表授权');
  text('warning',v.status==='input_point'&&v.headingDeg.value===null?'艏向未知，不以 COG 替代。':'固定原件定位，不回退 latest；已有返回值不代表持续授权。');
 }
 function render(model,token){
  current=model;text('clock',model.caseId+' · '+model.alignedUtc);
  text('state-note',model.vessels.map(v=>v.vesselId+'：'+({input_point:quality[v.position?.kind],declared_gap:'声明缺轨，不补位置',no_observation_at_time:'无精确行，不沿用旧位置'}[v.status])).join(' / '));
  const pts=model.vessels.filter(v=>v.position?.value).map(v=>v.position.value),lo=k=>Math.min(...pts.map(p=>p[k])),hi=k=>Math.max(...pts.map(p=>p[k]));
  const axis=(p,k,start,size)=>hi(k)===lo(k)?start+size/2:start+(p[k]-lo(k))/(hi(k)-lo(k))*size;
  for(const [i,v] of model.vessels.entries()){
   const b=node(el('point-options'),'button',v.vesselId+' · '+(v.status==='input_point'?'查看对应行':v.status==='declared_gap'?'查看缺轨定位':'无精确行'));
   b.disabled=v.locator===null;b.onclick=()=>{if(v.locator)detail(v,token);};
   const side=el(i?'source-b':'source-a');side.disabled=b.disabled;side.textContent=v.vesselId+' · 定位';side.onclick=b.onclick;
   if(v.position?.value){const p=v.position.value,m=svg(el('map'),'circle',{cx:axis(p,'lonDeg',70,660),cy:375-axis(p,'latDeg',65,240),r:7,fill:i?'#94adff':'#4dd0e1','data-current':v.vesselId});m.onclick=()=>detail(v,token);}
   const total=selection.times.length,index=selection.times.indexOf(model.alignedUtc);
   svg(el('timeline'),'circle',{cx:120+(total>1?index/(total-1):0)*665,cy:40+i*34,r:v.status==='input_point'?6:3,fill:v.status==='input_point'?'#4dd0e1':'#ffb64f','data-status':v.status});
  }
 }
 async function load(time){
  if(flight?.epoch===epoch&&flight?.time===time)return;
  const ticket=++serial,context=epoch,s=selection,reader=query;clear('正在查询；当前坐标和旧来源已清除。');
  if(!s||!reader||!s.times.includes(time)){clear('尚未选择有效案件与查询时点。');return;}
  const attempt={epoch:context,time};flight=attempt;el('time').value=time;controls();
  try{
   const result=await reader(Object.freeze({caseId:s.caseId,...(DISPLAY_ONLY?{}:{pins:clone(s.pins)}),alignedUtc:time}));
   if(ticket!==serial||context!==epoch)return;
   render(validate(result,s,time),ticket);everReady=true;
  }catch(error){
   if(ticket!==serial||context!==epoch)return;
   clear((everReady?'此前显示已清除；':'首次载入未通过；')+(['ACCESS_DENIED','SESSION_EXPIRED'].includes(error?.code)?'访问未获确认，请重新核对授权。':'本次未取得有效结果；未显示登记证据。'));
  }finally{if(flight===attempt)flight=null;controls();}
 }
 function selectCase(value){
  ++epoch;++serial;selection=null;everReady=false;clear('未选择案件。');el('time').replaceChildren();text('registered-case','未选案件');
  try{
   if(DISPLAY_ONLY){
    assert(keys(value,['caseId','vesselIds','times'])&&id(value.caseId)&&Array.isArray(value.vesselIds)&&value.vesselIds.length===2&&value.vesselIds.every(id)&&value.vesselIds[0]!==value.vesselIds[1]);
   }else{
   assert(keys(value,['caseId','pins','times'])&&id(value.caseId)&&Array.isArray(value.pins)&&value.pins.length===2&&value.pins.every(p=>goodPin(p,value.caseId)));
   assert(value.pins[0].requestDigest!==value.pins[1].requestDigest&&value.pins[0].evidenceId!==value.pins[1].evidenceId);
   }
   assert(Array.isArray(value.times)&&value.times.length>0&&value.times.length<=1000&&value.times.every(utc)&&value.times.every((t,i)=>i===0||Date.parse(t)>Date.parse(value.times[i-1])));
   selection=clone(value);text('registered-case',selection.caseId);
   for(const time of selection.times){const o=node(el('time'),'option',time);o.value=time;}el('time').value=selection.times[0];clear('已选择案件；请显式查询。尚未载入登记证据。');
  }catch{clear('案件或固定定位配置无效；未开始读取。');}controls();
 }
 function stage(time){
  if(!selection||!selection.times.includes(time))return;
  ++serial;clear('时点已暂选，尚未查询；旧坐标和来源已清除。');el('time').value=time;
  text('clock','待提交查询时点 · '+time);
  const i=selection.times.indexOf(time),n=selection.times.length;
  svg(el('timeline'),'line',{x1:120+(n>1?i/(n-1):0)*665,x2:120+(n>1?i/(n-1):0)*665,y1:20,y2:110,stroke:'#ffb64f','data-preview':'unqueried'});
  controls();
 }
 el('time').oninput=()=>stage(el('time').value);
 el('time').onchange=()=>stage(el('time').value);
 el('prev').onclick=()=>{if(selection){const i=selection.times.indexOf(el('time').value);if(i>0)stage(selection.times[i-1]);}};
 el('next').onclick=()=>{if(selection){const i=selection.times.indexOf(el('time').value);if(i+1<selection.times.length)stage(selection.times[i+1]);}};
 el('registered-load').onclick=()=>load(el('time').value);
 el('nav-toggle').onclick=()=>{const open=el('nav-toggle').getAttribute('aria-expanded')!=='true';el('nav-toggle').setAttribute('aria-expanded',String(open));el('navigation').classList.toggle('open',open);};
 globalThis.MCISRegisteredWorkbench=Object.freeze({
  attach(adapter){++epoch;++serial;query=null;selection=null;everReady=false;clear('未接业务查询。');el('time').replaceChildren();text('registered-case','未选案件');controls();if(typeof adapter!=='function')throw new Error('QUERY_ADAPTER_REQUIRED');query=adapter;clear('查询适配器已注入；尚未选案。');el('time').replaceChildren();text('registered-case','未选案件');controls();},
  selectCase,load,
  invalidate(){++epoch;++serial;selection=null;query=null;everReady=false;clear('上下文已失效；请重新确认身份与案件。');el('time').replaceChildren();text('registered-case','未选案件');controls();}
 });
 clear('未接业务查询；没有身份或案件数据。');controls();
})();
