import assert from 'node:assert/strict'
import * as echarts from 'echarts'
import {timelineDomain,timelineAxis} from '../src/timeline/domain'
let n=0
function test(name:string,f:()=>void){f();n++;console.log('ok '+name)}
test('invalid numeric endpoints/order/offset fail closed',()=>{
 for(const d of [{min:NaN,max:60},{min:0,max:Infinity},{min:-Infinity,max:60},{min:60,max:0},{min:0,max:0},{min:-1e308,max:1e308}])assert.equal(timelineAxis(d,'2026-01-01T00:00:00Z',480).ok,false)
 for(const offset of [NaN,Infinity,-Infinity,1e308])assert.equal(timelineAxis({min:0,max:60},'2026-01-01T00:00:00Z',offset).ok,false)
})
test('date limit valid at boundary rejected immediately beyond',()=>{
 assert.equal(timelineAxis({min:0,max:8640000000000},'1970-01-01T00:00:00Z',0).ok,true)
 const result=timelineAxis({min:0,max:8640000000000.001},'1970-01-01T00:00:00Z',0)
 assert.equal(result.ok,false); assert.ok(!('axis' in result))
})
test('offset can itself push valid seconds outside date limit',()=>assert.equal(timelineAxis({min:0,max:8640000000000},'1970-01-01T00:00:00Z',1).ok,false))
test('epoch timezone and display offset combine once',()=>{
 const a=timelineAxis({min:0,max:86400},'2026-01-01T08:00:00+08:00',480)
 assert.ok(a.ok);if(a.ok){assert.equal(a.axis.axisLabel.formatter(0),'2026-01-01 08:00');assert.equal(a.axis.axisLabel.formatter(86400),'2026-01-02 08:00')}
})
test('factory retains frozen extrema with no interval/clipping',()=>{
 const d=Object.freeze({min:-31536000,max:31536000})
 const a=timelineAxis(d,'2026-01-01T00:00:00Z',0)
 assert.ok(a.ok);if(a.ok){assert.equal(a.axis.min,d.min);assert.equal(a.axis.max,d.max);assert.equal(a.axis.splitNumber,8);assert.ok(!('interval' in a.axis))}
 assert.deepEqual(d,{min:-31536000,max:31536000})
})
test('asymmetric week exact production axis SSR bounded and endpoints visible',()=>{
 const events=[{timeSec:-604800},{timeSec:5,endTimeSec:1209600}]
 const d=timelineDomain(false,events,[{timeSec:-86400}],[{timeSec:900000}])
 const a=timelineAxis(d,'2026-01-01T00:00:00Z',-300);assert.ok(a.ok);if(!a.ok)return
 const chart=echarts.init(null,undefined,{renderer:'svg',ssr:true,width:800,height:400})
 try{chart.setOption({animation:false,grid:{left:80,right:40},xAxis:a.axis,yAxis:{type:'value'},series:[{type:'scatter',data:[[d.min,0],[d.max,0]]}]})
 for(const x of [d.min,d.max]){const p=chart.convertToPixel({seriesIndex:0},[x,0]) as number[];assert.ok(p.every(Number.isFinite));assert.ok(p[0]>=80-1e-6&&p[0]<=760+1e-6)}
 const svg=chart.renderToSVGString();assert.ok(svg.length<50000);assert.ok(svg.includes('2025-')||svg.includes('2026-'))
 }finally{chart.dispose()}
})
console.log(n+' independent production-axis cases passed')
