import assert from 'node:assert/strict'
import {createElement} from 'react'
import {renderToStaticMarkup} from 'react-dom/server'
import {AnalysisView} from '../src/analysis/AnalysisView'
import type {AnalysisCase} from '../src/analysis/types'
const ref={path:'synthetic-only',sha256:'a'.repeat(64),role:'合成字段'}
const data:AnalysisCase={caseId:'SYN-NULL-CPA',key:'synthetic',title:'纯合成',isFictionalDemo:true,sourceLabel:'合成输入，非实测',sourceRefs:[],epochLocal:'2026-01-01T08:00:00',timeZone:'UTC+8',vessels:[{vesselId:'A',name:'合成 A'},{vesselId:'B',name:'合成 B'}],thresholds:{},baseline:{label:'合成计算',stepSec:1,cutAtSec:1,series:[{t:0,clock:'08:00:00',distanceNm:1,dcpaNm:0.25,tcpaMin:3,riskLevel:'Warning'},{t:1,clock:'08:00:01',distanceNm:1,dcpaNm:null,tcpaMin:null,riskLevel:'Warning'}],keyMoments:[{kind:'minDcpa',label:'合成缺失值',t:1,clock:'08:00:01',value:null,unit:'nm',source:'合成不可用'}]},whatif:null,notes:['未提供假设情景'],meta:{seedSha256:'b'.repeat(64),seedVerified:false,generatedAt:'合成未生成',generator:'synthetic',coreVersion:'not-run',coreDll:ref,w14Export:ref,w14Frozen:ref,crossCheck:{against:[],valuesCompared:0,maxAbsDiff:0,tolerance:0,ok:false},disclaimer:'仅显示测试'}}

for (const seedVerified of [false,true]) {
  const input = {...data, meta:{...data.meta,seedVerified}}
  const before = JSON.stringify(input)
  const html = renderToStaticMarkup(createElement(AnalysisView,{data:input,cases:[],selected:'baseline',onSelect:()=>{},onSwitchCase:()=>{},charts:false}))
  const scope = html.match(/data-testid="analysis-result-scope">([^<]+)</)?.[1]
  assert.ok(scope)
  assert.match(scope!,/既有离线分析结果（种子数据）/)
  assert.match(scope!,/非当前登记航迹重新计算/)
  assert.match(scope!,/尚未绑定当前登记原件版本/)
  assert.match(scope!,/同案登记航迹变更不代表这些结果已更新/)
  assert.match(scope!,/种子自检不代表当前版本核验/)
  assert.ok(html.indexOf('analysis-result-scope') < html.indexOf('an-top'))
  assert.ok(html.includes(seedVerified ? '已自检' : '未自检'))
  assert.equal(JSON.stringify(input),before)
}
console.log('PASS 18 synthetic SSR assertions; no seed, service, core or browser execution')
