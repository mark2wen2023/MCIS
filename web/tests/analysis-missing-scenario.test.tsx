// Constructed metadata only; no stored cases/core/model/browser.
import {strict as assert} from 'node:assert'
import {renderToStaticMarkup} from 'react-dom/server'
import {AnalysisView} from '../src/analysis/AnalysisView'
import {BASELINE} from '../src/analysis/derive'
import type {AnalysisCase, ScenarioRow} from '../src/analysis/types'
const ref={path:'synthetic-reference',sha256:'0'.repeat(64),role:'synthetic only'}
const data:AnalysisCase={caseId:'SYNTHETIC-A',key:'synthetic',title:'合成分析',isFictionalDemo:true,sourceLabel:'合成资料',sourceRefs:[],epochLocal:'synthetic',timeZone:'UTC',vessels:[],thresholds:{},baseline:{label:'SYNTHETIC-BASELINE',stepSec:1,cutAtSec:0,series:[],keyMoments:[]},whatif:null,notes:[],meta:{seedSha256:'0'.repeat(64),seedVerified:false,generatedAt:'synthetic',generator:'synthetic',coreVersion:'not-run',coreDll:ref,w14Export:ref,w14Frozen:ref,crossCheck:{against:[],valuesCompared:0,maxAbsDiff:0,tolerance:0,ok:false},disclaimer:'synthetic not computed'}}
function html(selected:string,d=data){return renderToStaticMarkup(<AnalysisView data={d} cases={[]} selected={selected} onSelect={()=>{}} onSwitchCase={()=>{}} charts={false}/>)}
const missing=html('MISSING')
assert.ok(missing.includes('指定分析方案未找到'),'missing scenario must be explicit')
assert.ok(!missing.includes('SYNTHETIC-BASELINE'),'do not silently render baseline')
assert.ok(missing.includes('SYNTHETIC-A')&&missing.includes('MISSING'))
assert.ok(html(BASELINE).includes('SYNTHETIC-BASELINE'))
const row:ScenarioRow={id:'SYN-2',name:'合成方案',changeSummary:'synthetic',verdict:'Unknown',verdictText:'unknown',displayVerdictText:'unknown',isCritical:false,criticalReason:'',safeDistanceM:0,sensitivityRangeText:'',collision:false,tcSeconds:null,tcLocal:'unknown',collisionAngleText:'unknown',contactPartText:'unknown',minClearanceM:0,minClearanceTimeSeconds:0,minDistanceNm:0,minDistanceTimeSeconds:0,minDcpaNm:0,sensitivity:[],series:[],keyMoments:[],trackPlot:{}}
const withRows={...data,whatif:{label:'synthetic',epochLocal:'synthetic',ownVesselId:'a',targetVesselId:'b',safeDistanceM:0,criticalMarginM:0,stepSec:1,disclaimer:'synthetic',assumptions:[],inputs:[],rows:[row],antennaSensitivity:null,curveNote:'synthetic'}}
assert.ok(html('SYN-2',withRows).includes('W14 情景 SYN-2'))
assert.ok(html('MISSING',withRows).includes('指定分析方案未找到'))
let chosen=''
const prompt=AnalysisView({data,cases:[],selected:'MISSING',onSelect:id=>{chosen=id},onSwitchCase:()=>{},charts:false})
const button=(prompt.props.children as any[]).find(n=>n?.type==='button')
assert.equal(chosen,'','no automatic selection')
button.props.onClick()
assert.equal(chosen,BASELINE,'explicit user action selects baseline')
console.log('analysis scenario: 8 synthetic rendering/action assertions passed')
