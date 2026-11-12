import assert from 'node:assert/strict'
import {renderToStaticMarkup} from 'react-dom/server'
import {parseResult,parseMetadata} from '../../web/src/currentAnalysis/model'
import {CurrentResult} from '../../web/src/currentAnalysis/CurrentAnalysis'
import {plotIndices} from '../../web/src/tracks/model'
const cid='ACCEPT-SYNTHETIC',epoch='2026-01-01T00:00:00Z'
function fixture(){
 const p={vesselId:'A',timeSec:0,utc:epoch,latDeg:0,lonDeg:0,sogKn:1,cogDeg:90,source:'<img src=x onerror=alert(1)>'}
 return {caseId:cid,title:'Synthetic test only',isFictionalDemo:false,caseEpochUtc:epoch,profile:'MCIS-CURRENT-CPA-1',origin:{latDeg:0,lonDeg:0},vessels:[{vesselId:'A',name:'A'},{vesselId:'B',name:'B'}],window:{fromSec:null,toSec:null},inputDigest:'f'.repeat(64),coreVersion:'fixture',counts:{own:1,target:1,matched:1,unmatchedOwn:0,unmatchedTarget:0},rows:[{timeSec:0,utc:epoch,own:p,target:{...p,vesselId:'B'},currentDistanceNm:.3,dcpaNm:0,tcpaMin:0,isDegenerate:false,isDiverging:true}]}
}
const parse=(v:unknown)=>parseResult(v,cid,'A','B',null,null)
let assertions=0
function check(fn:()=>void){fn();assertions++}
check(()=>assert.equal(parse(fixture()).rows[0]!.isDiverging,true))
const attacks:Array<[string,(x:any)=>void]>=[
 ['cross-case',x=>x.caseId='OTHER'],['vessel reversal',x=>x.vessels.reverse()],['foreign own point',x=>x.rows[0].own.vesselId='B'],['wrong window',x=>x.window.toSec=1],['mismatched count',x=>x.counts.matched=0],['fractional count',x=>x.counts.own=1.1],['invalid digest',x=>x.inputDigest='not-signature'],['missing version',x=>x.coreVersion=null],['duplicate rows',x=>{x.rows.push(structuredClone(x.rows[0]));x.counts={own:2,target:2,matched:2,unmatchedOwn:0,unmatchedTarget:0}}],['nonfinite distance',x=>x.rows[0].currentDistanceNm=Infinity],['nonfinite tcpa',x=>x.rows[0].tcpaMin=NaN],['negative dcpa',x=>x.rows[0].dcpaNm=-.1],['negative time wrong flag',x=>{x.rows[0].tcpaMin=-1;x.rows[0].isDiverging=false}],['degenerate finite time',x=>x.rows[0].isDegenerate=true],['false degenerate null time',x=>x.rows[0].tcpaMin=null],['invalid UTC',x=>x.rows[0].utc='2026-02-30T00:00:00Z'],['UTC versus epoch drift',x=>x.rows[0].own.utc='2026-01-01T00:00:01Z'],['fake provenance',x=>x.rows[0].target.provenance='Certified']]
for(const [name,alter] of attacks)check(()=>{const x=fixture();alter(x);assert.throws(()=>parse(x),undefined,name)})
for(const provenance of ['Measured','Interpolated','ManualDrawn','Simulated',undefined])check(()=>{const x:any=fixture();if(provenance)x.rows[0].own.provenance=provenance;assert.equal(parse(x).rows[0]!.own.provenance,provenance)})
check(()=>{const x=fixture();x.rows[0]!.isDegenerate=true;x.rows[0]!.isDiverging=false;(x.rows[0] as any).tcpaMin=null;assert.equal(parse(x).rows[0]!.tcpaMin,null)})
check(()=>{const html=renderToStaticMarkup(<CurrentResult result={parse(fixture())} charts={false}/>);assert(!html.includes('<img'));assert(html.includes('&lt;img'));assert(html.includes('核心标记已远离'));assert(html.includes('未提供来源类型'))})
check(()=>{const x=fixture();x.rows=[];x.coreVersion=null as any;x.counts={own:2,target:3,matched:0,unmatchedOwn:2,unmatchedTarget:3};const html=renderToStaticMarkup(<CurrentResult result={parse(x)} charts={false}/>);assert(html.includes('没有可配对同刻点'));assert(!html.includes('<table'))})
for(const n of [0,1,1999,2000,2001,2501,5000])check(()=>{const ids=plotIndices(n);assert.equal(ids.length,Math.min(n,2000));assert.equal(new Set(ids).size,ids.length);if(n){assert.equal(ids[0],0);assert.equal(ids.at(-1),n-1)}})
// Characterize, don't hide, the malformed-metadata user-facing error.
let metadataMessage='';try{parseMetadata(cid,{},[])}catch(e){metadataMessage=(e as Error).message}
console.log(JSON.stringify({assertions,metadataMessage,browserCoverage:false}))
// The component now delegates TrackDataError to the existing localized formatter.
import {readError} from '../../web/src/tracks/api'
import {TrackDataError} from '../../web/src/tracks/model'
for(const code of ['FORMAT','METADATA_LIMIT'])check(()=>{const text=readError(new TrackDataError(code));assert(/[\u3400-\u9fff]/.test(text));assert.notEqual(text,code)})
console.log(JSON.stringify({totalAssertions:assertions,errorLocalization:true,browserCoverage:false}))
