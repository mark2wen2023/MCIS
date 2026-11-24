'use strict';
(() => {
 const data=JSON.parse(document.getElementById('data').textContent),el=id=>document.getElementById(id);
 const NS='http://www.w3.org/2000/svg',colors=['#4dd0e1','#94adff'];
 let index=data.frames.findIndex(f=>f.relativeSeconds===100);
 function node(parent,tag,text){const n=document.createElement(tag);n.textContent=text;parent.appendChild(n);return n;}
 function svg(parent,tag,attrs,text){const n=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));if(text!==undefined)n.textContent=text;parent.appendChild(n);return n;}
 const fraction=(value,[min,max])=>max===min?.5:(value-min)/(max-min);
 const x=p=>36+fraction(p.lonDeg,data.bounds.lonDeg)*738;
 const y=p=>320-fraction(p.latDeg,data.bounds.latDeg)*250;
 const tx=t=>120+t/220*665;
 function clearDetail(){
  for(const id of ['record-id','raw-time','source-time','correction','aligned-time','pointer','ref'])el(id).textContent='—';
  el('evidence-title').textContent='请选择当前时点记录';el('quality').textContent='未选择';el('file').textContent='未选择文件';el('basis').textContent='点击当前标记或记录按钮查看；旧详情已失效。';el('raw').textContent='未选择；不沿用旧详情。';el('raw-open').disabled=true;el('raw-details').open=false;
  el('warning-title').textContent='来源边界';el('warning').textContent='声明一致不等于真实原件核验，不输出确定碰撞角。';
 }
 function showRecord(record,time,title,quality,warning,sources){
  el('evidence-title').textContent=title;el('record-id').textContent=record.rawRecord.pointId||record.rawRecord.recordId;el('quality').textContent=quality;
  el('raw-time').textContent=time.sourceRecordTime;el('source-time').textContent=time.sourceUtc??'未核实';el('correction').textContent=time.correctionSeconds===null?'未知':(time.correctionSeconds>=0?'+':'')+time.correctionSeconds+' s';el('aligned-time').textContent=time.alignedUtc??'不参与同步';el('basis').textContent=time.basis;
  el('file').textContent=record.path.split('/').at(-1);el('pointer').textContent=record.jsonPointer;el('ref').textContent=(record.gitRef?'MCIS @ '+record.gitRef.slice(0,8)+' · ':'本候选合成设备 · ')+'SHA256 '+record.sha256;
  el('warning-title').textContent=warning[0];el('warning').textContent=warning[1];el('raw').textContent=JSON.stringify({...record,...(sources?{sources}: {})},null,2);el('raw-open').disabled=false;el('raw-details').open=false;
 }
 function showVessel(v){if(!v.records.length)return;showRecord(v.records[0],v.time,v.vesselId.endsWith('A')?'A 船原始轨迹点':'B 船原始轨迹点',v.position.kind==='interpolated'?'输入已存插值':'输入记录 · 合成',v.headingDeg.value===null?['艏向未知','不以航迹向代替艏向，不输出碰撞角。']:['仅为输入方向声明','没有真实船体、碰撞角或真实性核验。'],v.sources);}
 function showDevice(e){showRecord(e.record,e.time,e.record.rawRecord.recordId==='SYN-DEVICE-01'?'设备 01 · 已对齐':'设备 02 · 时间未核实',e.time.alignedUtc?'合成校时记录':'不参与同步',e.time.alignedUtc?['独立设备声明','同案同船关联到输入点，不是设备测位或真实时钟核验。']:['时刻无法核实','不根据屏显猜 UTC，不并入时间轴，不改变当前船位。']);}
 function seek(seconds){const found=data.frames.findIndex(f=>f.relativeSeconds===seconds);if(found<0)return;index=found;el('time').value=String(index);draw();}
 function map(frame){
  const root=el('map');root.replaceChildren();
  for(let i=0;i<=16;i++)svg(root,'line',{x1:i*50,y1:0,x2:i*50,y2:375,stroke:'#203746','stroke-width':.7});
  for(let i=0;i<=8;i++)svg(root,'line',{x1:0,y1:i*47,x2:810,y2:i*47,stroke:'#203746','stroke-width':.7});
  for(const [i,h] of data.history.entries()){
   for(let k=1;k<h.points.length;k++){
    const a=h.points[k-1],b=h.points[k];
    if(!a.position.value||!b.position.value||b.seconds-a.seconds>h.threshold||h.gaps.some(g=>a.seconds<g[1]&&b.seconds>g[0]))continue;
    svg(root,'line',{x1:x(a.position.value),y1:y(a.position.value),x2:x(b.position.value),y2:y(b.position.value),stroke:colors[i],'stroke-width':1,opacity:.32,'stroke-dasharray':a.position.kind==='interpolated'||b.position.kind==='interpolated'?'4 4':'none','data-history':h.vesselId,'data-from':a.seconds,'data-to':b.seconds});
   }
  }
  for(const [i,v] of frame.vessels.entries()){
   if(!v.position?.value)continue;
   const p=v.position.value;svg(root,'circle',{cx:x(p),cy:y(p),r:12,fill:colors[i],opacity:.12});
   const mark=svg(root,'circle',{cx:x(p),cy:y(p),r:6,fill:colors[i],stroke:colors[i],'stroke-width':2,'data-current':v.vesselId});mark.onclick=()=>showVessel(v);
   svg(root,'text',{x:x(p)+15,y:y(p)-12,fill:colors[i],'font-size':12},(i?'B':'A')+' 船 · '+v.records[0].rawRecord.pointId);
  }
 }
 function timeline(frame){
  const root=el('timeline');root.replaceChildren();
  for(const t of [0,60,100,150,220])svg(root,'text',{x:tx(t),y:13,fill:'#8fa6b8','font-size':11,'text-anchor':'middle'},'T+'+t);
  for(const [i,h] of data.history.entries()){
   const rowY=40+i*34;svg(root,'text',{x:4,y:rowY+4,fill:'#dce7ef','font-size':12},i?'B 船':'A 船');
   let start=0;for(const [lo,hi] of [...h.gaps,[220,220]]){svg(root,'line',{x1:tx(start),y1:rowY,x2:tx(lo),y2:rowY,stroke:colors[i],'stroke-width':3,opacity:.75});start=hi;}
   for(const [lo,hi] of h.gaps){svg(root,'rect',{x:tx(lo),y:rowY-6,width:tx(hi)-tx(lo),height:12,fill:'#62431d','data-gap':lo+':'+hi});for(let n=tx(lo);n<tx(hi)-3;n+=6)svg(root,'line',{x1:n,y1:rowY+5,x2:Math.min(n+4,tx(hi)),y2:rowY-5,stroke:'#ffb64f','stroke-width':.6});}
  }
  svg(root,'text',{x:4,y:112,fill:'#dce7ef','font-size':12},'设备');svg(root,'line',{x1:tx(0),y1:108,x2:tx(220),y2:108,stroke:'#253f50','stroke-width':3});
  svg(root,'path',{d:'M '+tx(100)+' 102 l 6 6 l -6 6 l -6 -6 Z',fill:'#ffb64f','data-device':'SYN-DEVICE-01'}).onclick=()=>{seek(100);showDevice(data.frames[index].events[0]);};
  svg(root,'line',{x1:tx(frame.relativeSeconds),y1:21,x2:tx(frame.relativeSeconds),y2:122,stroke:'#ffcf7a','stroke-width':1});
  for(const [i,v] of frame.vessels.entries())if(v.position?.value)svg(root,'circle',{cx:tx(frame.relativeSeconds),cy:40+i*34,r:5,fill:colors[i]});
 }
 function draw(){
  const frame=data.frames[index];clearDetail();map(frame);timeline(frame);el('point-options').replaceChildren();
  el('source-a').disabled=!frame.vessels[0].records.length;el('source-b').disabled=!frame.vessels[1].records.length;
  const status=[];for(const [i,v] of frame.vessels.entries()){
   if(v.records.length){const b=node(el('point-options'),'button',(i?'B':'A')+' 船 · '+v.records[0].rawRecord.pointId+(v.position.kind==='interpolated'?' · 已存插值':''));b.onclick=()=>showVessel(v);status.push((i?'B':'A')+'：当前输入点');}
   else status.push((i?'B':'A')+'：'+(v.status==='declared_gap'?'缺轨，不补位置':'此时点无精确观测，不沿用旧位置'));
  }
  el('state-note').textContent=status.join('　/　');el('clock').textContent=frame.alignedUtc+'　·　T+'+frame.relativeSeconds+'s　·　'+frame.caseId;
  el('prev').disabled=index===0;el('next').disabled=index===data.frames.length-1;
 }
 for(const [i,f] of data.frames.entries()){const o=node(el('time'),'option',f.alignedUtc.slice(11)+'　 T+'+f.relativeSeconds+'s');o.value=String(i);}
 el('time').value=String(index);el('time').onchange=()=>{const i=Number(el('time').value);if(!Number.isInteger(i)||i<0||i>=data.frames.length)return;index=i;draw();};
 el('prev').onclick=()=>{if(index>0){index--;el('time').value=String(index);draw();}};el('next').onclick=()=>{if(index<data.frames.length-1){index++;el('time').value=String(index);draw();}};
 el('source-a').onclick=()=>showVessel(data.frames[index].vessels[0]);el('source-b').onclick=()=>showVessel(data.frames[index].vessels[1]);
 el('device-known').onclick=()=>{seek(100);showDevice(data.frames[index].events[0]);};el('device-unknown').onclick=()=>showDevice(data.frames[index].excludedDevices[0]);
 el('raw-open').onclick=()=>{if(el('raw-open').disabled)return;el('raw-details').open=true;el('raw').focus();};
 el('nav-toggle').onclick=()=>{const open=el('nav-toggle').getAttribute('aria-expanded')!=='true';el('nav-toggle').setAttribute('aria-expanded',String(open));el('navigation').classList.toggle('open',open);};
 draw();showVessel(data.frames[index].vessels[0]);
})();
