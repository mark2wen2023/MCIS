import assert from 'node:assert/strict'
import {renderToStaticMarkup} from 'react-dom/server'
import {PointDetail} from '../../web/src/tracks/TrackView'
import type {TrackPoint} from '../../web/src/tracks/model'
const point=(timeSec:number,provenance?:TrackPoint['provenance']):TrackPoint=>({vesselId:'V',timeSec,utc:new Date(Date.UTC(2026,0,1)+timeSec*1000).toISOString(),lonDeg:120,latDeg:30,sogKn:1,cogDeg:0,provenance,source:'<script>source</script>'})
const points=[point(0,'Measured'),point(5,'Interpolated'),point(20,'Measured')]
const filtered=points.filter(p=>p.provenance==='Measured');const selected=1
const index=points.indexOf(filtered[selected]!)
const html=renderToStaticMarkup(<PointDetail point={filtered[selected]!} index={index} previous={points[index-1]}/>)
assert.ok(html.includes('15 s'));assert.ok(!html.includes('相对时间差（当前减前点）</dt><dd>20 s'))
assert.ok(html.includes('2026-01-01T00:00:05.000Z'));assert.ok(html.includes('记录为插值'))
assert.ok(html.includes('选中第 3 点'));assert.ok(html.includes('&lt;script&gt;source&lt;/script&gt;'))
for(const [a,b,label] of [[5,5,'0 s（同时间记录）'],[10,5,'-5 s（返回时间倒退）']] as const){
const h=renderToStaticMarkup(<PointDetail point={point(b)} index={1} previous={point(a)}/>);assert.ok(h.includes(label));assert.ok(h.includes('未提供来源类型'))}
const first=renderToStaticMarkup(<PointDetail point={points[0]!} index={0}/>);assert.ok(first.includes('时间窗外是否存在前点未知'))
console.log('detail SSR: filtering, original index, UTC, source, duplicates, reverse, unknown, escaping passed')
