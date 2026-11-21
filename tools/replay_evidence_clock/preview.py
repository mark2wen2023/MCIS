"""Generate one network-free synthetic evidence panel, not a service or 3D engine."""
import argparse
import json
from pathlib import Path
import runpy

HERE=Path(__file__).resolve().parent
Q=runpy.run_path(str(HERE/'query.py'))

def build(target):
    tracks,device=Q['load_inputs']()
    times={0,60,60.001,80,99.999,100,121,121.001,124.25,127.499,127.5,220}
    for t in tracks:
        times.update((Q['stamp'](p['time']['alignedUtc'])-Q['ORIGIN']).total_seconds() for p in t['document']['points'])
    frames=[Q['query'](tracks,device,s) for s in sorted(times)]
    positions=[p['position']['value'] for t in tracks for p in t['document']['points'] if p['position']['value']]
    bounds={k:[min(p[k] for p in positions),max(p[k] for p in positions)] for k in ['latDeg','lonDeg']}
    payload=json.dumps({'frames':frames,'bounds':bounds},ensure_ascii=False,allow_nan=False).replace('<','\\u003c')
    html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src 'none'; base-uri 'none'; form-action 'none'">
<title>粤海探析 · 合成共享时点证据</title><style>
body{margin:0;background:#0c1219;color:#dbe7ef;font:15px system-ui}header{padding:20px;border-bottom:1px solid #2a3a4d}main{display:grid;grid-template-columns:minmax(0,1fr) 440px;gap:16px;padding:20px}section{background:#111a24;padding:16px;border:1px solid #2a3a4d;margin-bottom:16px}button,select{background:#182430;color:#dbe7ef;border:1px solid #4dd0e1;padding:9px;margin:5px}button:focus-visible,select:focus-visible{outline:3px solid #ffd580}pre{white-space:pre-wrap;overflow-wrap:anywhere}svg{width:100%;background:#182430}h1{font-size:22px}h2{font-size:18px}.warn{color:#ffd580}@media(max-width:850px){main{display:block}}
</style><header><h1>粤海探析 · 共享时点与原始记录</h1><p>纯合成、离线只读二维预览。不是三维重建或业务导出；不认证原件、不裁定接触或碰撞角。</p><label>共同起点后的秒数 <select id="time"></select></label><button id="prev">上一时点</button><button id="next">下一时点</button><p id="clock" role="status"></p></header>
<main><div><section><h2>同一时点的已提供位置</h2><svg id="plot" viewBox="0 0 700 400" role="img" aria-label="合成位置散点，非等距地图"></svg><p>只显示此时点输入已有位置；没有观测即不显示。不连航线、不跨缺口插值。输入本身标为 interpolated 的点仍明确标注。点位不是船体、航行图或量距依据。</p><div id="vessels"></div></section><section><h2>同步的设备记录</h2><div id="events"></div></section><section><h2>未核实时间（不参与同步）</h2><div id="excluded"></div></section></div>
<aside><section><h2>来源与版本定位</h2><p>点击记录查看原始 JSON。Git ref / 文件摘要 / JSON Pointer 固定输入，不代表持久报告引用或读取授权。</p><pre id="detail">请选择一条记录。</pre></section><section><h2>边界</h2><p class="warn">缺艏向不使用 COG；没有确定碰撞角。设备 +7 秒与船 B +12 秒均为手造声明，无法核实的设备时间单独列出。实际 mcis-3d / Unity 连点与播放尚未接入。</p></section></aside></main>
<script id="data" type="application/json">PAYLOAD</script><script>
'use strict';
const data=JSON.parse(document.getElementById('data').textContent),el=id=>document.getElementById(id);
function add(parent,tag,text){const n=document.createElement(tag);n.textContent=text;parent.appendChild(n);return n;}
function selectRecord(record){el('detail').textContent=JSON.stringify(record,null,2);}
function timeText(t){return '原始时刻：'+t.sourceRecordTime+' | UTC：'+(t.sourceUtc??'未核实')+' | 校正秒：'+(t.correctionSeconds??'未知')+' | 对齐：'+(t.alignedUtc??'不参与同步')+' | 状态：'+t.status+' | 依据：'+t.basis;}
function draw(){const frame=data.frames[Number(el('time').value)];el('clock').textContent=frame.caseId+' / '+frame.alignedUtc+' / T+'+frame.relativeSeconds+'秒';el('detail').textContent='请选择此时点记录；未沿用上一时点定位。';for(const id of ['plot','vessels','events','excluded'])el(id).replaceChildren();
 for(const [i,v] of frame.vessels.entries()){
  const box=add(el('vessels'),'article','');add(box,'h3',v.vesselId);
  add(box,'p',v.status==='declared_gap'?'已声明缺轨：此时点无位置，禁止跨缺口插值。':v.status==='no_observation_at_time'?'此时点无观测：未补点，未沿用上次位置。':'输入位置类型：'+v.position.kind+'；艏向：'+(v.headingDeg.value??'未知')+'；COG：'+v.courseDeg.value+'（不代替艏向）');
  if(v.time)add(box,'p',timeText(v.time));
  for(const r of v.records){const b=add(box,'button','查看原始点 '+r.rawRecord.pointId);b.onclick=()=>selectRecord({...r,sources:v.sources});}
  if(v.position?.value){const p=v.position.value,c=document.createElementNS('http://www.w3.org/2000/svg','circle'),b=data.bounds;
   c.setAttribute('cx',40+(p.lonDeg-b.lonDeg[0])/(b.lonDeg[1]-b.lonDeg[0])*620);c.setAttribute('cy',360-(p.latDeg-b.latDeg[0])/(b.latDeg[1]-b.latDeg[0])*320);c.setAttribute('r',9);c.setAttribute('fill',i?'#ffd580':'#4dd0e1');c.onclick=()=>selectRecord(v.records[0]);el('plot').appendChild(c);
  }
 }
 if(!frame.events.length)add(el('events'),'p','此时点没有已对齐设备事件；未把未知时刻当当前事件。');
 for(const [id,items] of [['events',frame.events],['excluded',frame.excludedDevices]])for(const e of items){add(el(id),'p',e.record.rawRecord.recordId+' · '+timeText(e.time));const b=add(el(id),'button','查看设备原始记录');b.onclick=()=>selectRecord(e);}
}
for(const [i,f] of data.frames.entries()){const o=add(el('time'),'option','T+'+f.relativeSeconds+'s');o.value=String(i);}
el('time').value=String(data.frames.findIndex(f=>f.relativeSeconds===100));el('time').onchange=draw;
el('prev').onclick=()=>{el('time').value=String(Math.max(0,Number(el('time').value)-1));draw();};el('next').onclick=()=>{el('time').value=String(Math.min(data.frames.length-1,Number(el('time').value)+1));draw();};draw();
</script></html>'''.replace('PAYLOAD',payload)
    with target.open('x',encoding='utf-8') as f:f.write(html)
    return html

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();build(args.output);print('PASS new offline HTML generated; browser/3D not executed')
