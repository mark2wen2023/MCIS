import assert from 'node:assert/strict'
import * as echarts from 'echarts'
import { timelineDomain } from '../src/timeline/domain'
// Real ECharts SVG SSR, not browser interaction or the complete application.
for (const fictional of [false,true]) {
  const events=[{timeSec:-30},{timeSec:0},{timeSec:800}]
  const domain=timelineDomain(fictional,events,[],[{timeSec:-60}])
  const chart=echarts.init(null,undefined,{renderer:'svg',ssr:true,width:800,height:400})
  chart.setOption({grid:{left:80,right:40},xAxis:{type:'value',...domain},yAxis:{type:'value',min:-1,max:1},series:[{type:'scatter',data:events.map(e=>[e.timeSec,0])}]})
  for (const e of events) {
    const point=chart.convertToPixel({seriesIndex:0},[e.timeSec,0]) as number[]
    assert.ok(point.every(Number.isFinite))
    assert.ok(point[0]>=80 && point[0]<=760)
  }
  assert.ok(chart.renderToSVGString().includes('<svg'))
  chart.dispose()
  console.log('ok ECharts SSR domain '+(fictional?'fictional':'real'))
}
