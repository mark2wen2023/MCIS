import {strict as assert} from 'node:assert'
import {createElement} from 'react'
import {renderToStaticMarkup} from 'react-dom/server'
Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null,setItem:()=>{}}})
async function main(){
 const {parseResult,ASSUMPTIONS,COVERAGE}=await import('../src/currentAnalysis/model')
 const {CurrentResult}=await import('../src/currentAnalysis/CurrentAnalysis')
 const point=(v:string)=>({vesselId:v,timeSec:0,utc:'2026-01-01T00:00:00Z',latDeg:0,lonDeg:.01,sogKn:0,cogDeg:0})
 const a={...point('A'),provenance:'Measured',source:'<img src=x onerror=alert(1)>'},b={...point('B'),provenance:'Interpolated'}
 const input={profile:'MCIS-CURRENT-CPA-1',caseId:'SYNTHETIC',title:'Test',caseEpochUtc:a.utc,isFictionalDemo:true,origin:{latDeg:0,lonDeg:0},vessels:[{vesselId:'A',name:'A'},{vesselId:'B',name:'B'}],window:{fromSec:null,toSec:null},inputDigest:'a'.repeat(64),coreVersion:'synthetic',counts:{own:2,target:1,matched:1,unmatchedOwn:1,unmatchedTarget:0},rows:[{timeSec:0,utc:a.utc,own:a,target:b,currentDistanceNm:1,dcpaNm:1,tcpaMin:null,isDegenerate:true,isDiverging:false}]}
 const parse=(x:unknown)=>parseResult(x,'SYNTHETIC','A','B',null,null)
 const result=parse(input);assert.equal(result.rows.length,1)
 for(const changed of [{caseId:'OTHER'},{inputDigest:'bad'},{counts:{...input.counts,own:3}},{origin:{latDeg:90,lonDeg:0}},{vessels:input.vessels.slice().reverse()},{window:{fromSec:0,toSec:null}},{coreVersion:null},{profile:'OTHER'}])assert.throws(()=>parse({...input,...changed}))
 for(const changed of [{timeSec:1},{utc:'2026-01-01T00:00:01Z'},{tcpaMin:0},{isDiverging:true},{dcpaNm:-1},{own:{...a,vesselId:'OTHER'}},{target:{...b,timeSec:1}},{target:{...b,utc:'2026-01-01T00:00:02Z'}}])assert.throws(()=>parse({...input,rows:[{...input.rows[0],...changed}]}))
 const markup=renderToStaticMarkup(createElement(CurrentResult,{result,charts:false}))
 for(const label of ['记录为实测','记录为插值','未配对点','不适用','未提供','不是证据签名','【推算】'])assert(markup.includes(label),label)
 assert(!markup.includes('<img'));assert(markup.includes('&lt;img'));assert(ASSUMPTIONS.includes('位置参考点未知'));assert(COVERAGE.includes('匹配不等于真实同时采样'))
 const empty=parse({...input,coreVersion:null,counts:{own:0,target:0,matched:0,unmatchedOwn:0,unmatchedTarget:0},rows:[]})
 assert(renderToStaticMarkup(createElement(CurrentResult,{result:empty,charts:false})).includes('未调用计算核心'))
 console.log('W12.2 parser binding, malformed/late-source fields, provenance escaping, null TCPA and empty-state render: passed')
}void main().catch(e=>{console.error(e);process.exitCode=1})
