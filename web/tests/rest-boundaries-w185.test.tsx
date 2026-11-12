import {strict as assert} from 'node:assert'
import {renderToStaticMarkup} from 'react-dom/server'
import {RestResult} from '../src/humanFactorsPreview/Result'
import type {Preview} from '../src/humanFactorsPreview/model'
const base:Preview={profile:'MCIS-REST-PREVIEW-1',caseId:'SYNTHETIC',inputSha256:'a'.repeat(64),sources:[],sourceBinding:'registered-metadata-only',persisted:false,assessment:'technical-preview-only',result:{coreVersion:'mcis-rest/1',mode:'rest-baseline-no-exceptions',totals:{restHours:0,workHours:0,unknownHours:0},coverage:{recordHours:0,has24hWindow:false,has7dWindow:false,unknownHours:0},findings:[],insufficientData:[],assumptions:['历史说明：判合规 <img onerror=x>']},limitations:[]}
// Synthetic rendered envelopes, not claims of independently rerunning the physics/core.
for(const [name,hours,rest] of [['three-segments-6+4+1',24,11],['short-record',5,5],['one-minute-rest',24,1/60]] as const){
 const preview={...base,result:{...base.result,totals:{restHours:rest,workHours:hours-rest,unknownHours:0},coverage:{recordHours:hours,has24hWindow:hours>=24,has7dWindow:false,unknownHours:0}}}
 const html=renderToStaticMarkup(<RestResult preview={preview}/>);assert.ok(html.includes('未评估总休息段数'),name);assert.ok(html.includes('窗口覆盖不足时不能判断合规'),name);assert.ok(html.includes('短 Rest 未经专业认定'),name);assert.ok(html.includes('核心历史说明中的'),name);assert.ok(html.includes('不表示数据充分'),name);assert.ok(html.includes('<details>'),name);assert.ok(!html.includes('<details open'),name);assert.ok(html.includes('历史说明：判合规 &lt;img'),name);assert.ok(!html.includes('<img'),name)
}
console.log('W18.5 synthetic UI boundary regressions passed: three segments, short coverage, short rest; raw legacy wording preserved collapsed and escaped')
