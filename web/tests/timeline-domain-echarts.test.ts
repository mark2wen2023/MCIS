import assert from 'node:assert/strict'
import * as echarts from 'echarts'
import { timelineDomain, timelineAxis } from '../src/timeline/domain'
// Uses the exact x-axis factory consumed by EvidencePage, including tick policy/labels.
let cases=0
for (const span of [30,86400,259200,604800,31536000,1e12]) {
  const events=[{timeSec:-span},{timeSec:0},{timeSec:span}]
  const domain=timelineDomain(false,events,[],[])
  const config=timelineAxis(domain,'2026-01-01T00:00:00Z',480)
  assert.ok(config.ok)
  if (!config.ok) throw Error('unexpected invalid range')
  const chart=echarts.init(null,undefined,{renderer:'svg',ssr:true,width:800,height:400})
  const warnings:string[]=[];const warn=console.warn
  console.warn=(...args:unknown[])=>warnings.push(args.join(' '))
  try {
    chart.setOption({grid:{left:80,right:40},xAxis:config.axis,yAxis:{type:'value',min:-1,max:1},series:[{type:'scatter',data:events.map(e=>[e.timeSec,0])}]})
    for(const e of events){const p=chart.convertToPixel({seriesIndex:0},[e.timeSec,0]) as number[];assert.ok(p.every(Number.isFinite));assert.ok(p[0]>=80-1e-6&&p[0]<=760+1e-6,JSON.stringify(p))}
    const svg=chart.renderToSVGString()
    assert.ok(svg.length<50000,'bounded output, not thousands of ticks')
    assert.ok(svg.includes(config.axis.axisLabel.formatter(0)),'actual x-axis zero tick label rendered')
    assert.deepEqual(warnings,[])
  } finally {console.warn=warn;chart.dispose()}
  console.log('ok exact production axis SSR span '+span);cases++
}
for(const span of [1e100,1e308]) {
  const result=timelineAxis(timelineDomain(false,[{timeSec:-span},{timeSec:span}],[],[]),'2026-01-01T00:00:00Z',480)
  assert.equal(result.ok,false)
  assert.ok(!('axis' in result),'unsupported evidence range not silently clipped')
  if(!result.ok)assert.ok(result.message.includes('未绘制'))
  cases++
}
assert.equal(timelineAxis({min:0,max:60},'bad',480).ok,false);cases++
const long=timelineAxis({min:-86400,max:86400},'2026-01-01T00:00:00Z',480)
assert.ok(long.ok)
if(long.ok)assert.notEqual(long.axis.axisLabel.formatter(-86400),long.axis.axisLabel.formatter(0));cases++
console.log(cases+' production-axis render/guard cases passed')
