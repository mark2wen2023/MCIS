import assert from 'node:assert/strict'
import {createElement} from 'react'
import {renderToStaticMarkup} from 'react-dom/server'
import {AnalysisView} from '../src/analysis/AnalysisView'
import {curveOption,fmtNm,fmtMoment} from '../src/analysis/derive'
import type {AnalysisCase} from '../src/analysis/types'
const ref={path:'synthetic-only',sha256:'a'.repeat(64),role:'合成字段'}
const data:AnalysisCase={caseId:'SYN-NULL-CPA',key:'synthetic',title:'纯合成',isFictionalDemo:true,sourceLabel:'合成输入，非实测',sourceRefs:[],epochLocal:'2026-01-01T08:00:00',timeZone:'UTC+8',vessels:[{vesselId:'A',name:'合成 A'},{vesselId:'B',name:'合成 B'}],thresholds:{},baseline:{label:'合成计算',stepSec:1,cutAtSec:1,series:[{t:0,clock:'08:00:00',distanceNm:1,dcpaNm:0.25,tcpaMin:3,riskLevel:'Warning'},{t:1,clock:'08:00:01',distanceNm:1,dcpaNm:null,tcpaMin:null,riskLevel:'Warning'}],keyMoments:[{kind:'minDcpa',label:'合成缺失值',t:1,clock:'08:00:01',value:null,unit:'nm',source:'合成不可用'}]},whatif:null,notes:['未提供假设情景'],meta:{seedSha256:'b'.repeat(64),seedVerified:false,generatedAt:'合成未生成',generator:'synthetic',coreVersion:'not-run',coreDll:ref,w14Export:ref,w14Frozen:ref,crossCheck:{against:[],valuesCompared:0,maxAbsDiff:0,tolerance:0,ok:false},disclaimer:'仅显示测试'}}
const opt=curveOption(data,data.baseline.series,data.baseline.keyMoments) as any
assert.deepEqual(opt.series[1].data,[0.25,null]);assert.deepEqual(opt.series[2].data,[3,null])
assert.equal(opt.tooltip.valueFormatter(null),'—');assert.equal(opt.tooltip.valueFormatter(0),'0.000')
assert.equal(fmtNm(null),'—');assert.equal(fmtNm(0),'0.000 nm')
assert.equal(fmtMoment(data.baseline.keyMoments[0]),'—')
const html=renderToStaticMarkup(createElement(AnalysisView,{data,cases:[],selected:'baseline',onSelect:()=>{},onSwitchCase:()=>{},charts:false}))
assert.match(html,/合成缺失值<\/td><td class="mono">—<\/td>/)
assert(!html.includes('data-testid="whatif-table"'))

import {AnalysisChoice} from '../src/analysis/AnalysisChoice'
const calls:string[]=[]
const button=AnalysisChoice({value:'SYN-B',selected:false,onSelect:value=>calls.push(value),children:'<合成 B>'})
assert.equal(button.type,'button');assert.equal(button.props.type,'button')
assert.equal(button.props['aria-pressed'],false)
button.props.onClick();assert.deepEqual(calls,['SYN-B'])
assert.equal(button.props.onKeyDown,undefined) // Native activation, no duplicate handler.
assert.match(renderToStaticMarkup(button),/&lt;合成 B&gt;/)
const list=[{caseId:data.caseId,key:'synthetic-a',title:'合成 A',isFictionalDemo:true,sourceLabel:'synthetic',hasWhatIf:false},{caseId:'SYN-B',key:'synthetic-b',title:'合成 B',isFictionalDemo:true,sourceLabel:'synthetic',hasWhatIf:false}]
const view=(d:AnalysisCase,selected='baseline')=>renderToStaticMarkup(createElement(AnalysisView,{data:d,cases:list,selected,onSelect:()=>{},onSwitchCase:()=>{},charts:false}))
const initial=view(data)
assert.match(initial,/<button type="button" class="an-choice on" aria-pressed="true">合成 A<\/button>/)
assert.match(initial,/<button type="button" class="an-choice" aria-pressed="false">合成 B<\/button>/)
assert.match(initial,/<button type="button" class="an-choice on" aria-pressed="true">案件航迹<\/button>/)
assert(!initial.includes('role="tab"'))
const switched=view({...data,caseId:'SYN-B'})
assert.match(switched,/<button type="button" class="an-choice on" aria-pressed="true">合成 B<\/button>/)
const scenario={id:'SYN-S1',name:'合成假设',changeSummary:'fixture',verdict:'Unknown',verdictText:'未判定',displayVerdictText:'未判定',isCritical:false,criticalReason:'',safeDistanceM:1,sensitivityRangeText:'未知',collision:false,tcSeconds:null,tcLocal:'—',collisionAngleText:'未知',contactPartText:'未知',minClearanceM:1,minClearanceTimeSeconds:0,minDistanceNm:1,minDistanceTimeSeconds:0,minDcpaNm:0,sensitivity:[],series:data.baseline.series,keyMoments:[],trackPlot:{}}
const withScenario:AnalysisCase={...data,whatif:{label:'合成',epochLocal:data.epochLocal,ownVesselId:'A',targetVesselId:'B',safeDistanceM:1,criticalMarginM:0,stepSec:1,disclaimer:'非实测',assumptions:[],inputs:[],rows:[scenario],antennaSensitivity:null,curveNote:'合成'}}
assert.match(view(withScenario,'SYN-S1'),/<button type="button" class="an-choice on" aria-pressed="true">SYN-S1<\/button>/)
const selectSeries=AnalysisChoice({value:'SYN-S1',selected:true,onSelect:value=>calls.push(value),children:'SYN-S1'})
selectSeries.props.onClick();assert.deepEqual(calls,['SYN-B','SYN-S1'])
console.log('PASS 22 synthetic assertions: production selection button callbacks/SSR and existing nullable analysis transforms; not browser keyboard')
