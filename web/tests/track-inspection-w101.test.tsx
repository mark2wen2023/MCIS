import { renderToStaticMarkup } from 'react-dom/server'
import { parseSnapshot, describe, plotIndices, trackQuery, validUtc, POINT_LIMIT, PLOT_LIMIT, TrackDataError } from '../src/tracks/model'
import { TrackView } from '../src/tracks/TrackView'
let n=0;function check(v:unknown,msg:string){if(!v)throw Error(msg);n++}
const c={caseId:'CASE-A',title:'<script>测试</script>',caseEpochUtc:'2026-01-01T00:00:00Z',isFictionalDemo:false}
const v=[{caseId:c.caseId,vesselId:'ship /?x',name:'船舶'}]
const p={vesselId:v[0].vesselId,timeSec:0,utc:c.caseEpochUtc,latDeg:30,lonDeg:121,sogKn:0,cogDeg:360,provenance:'Measured',source:'<img src=x>'}
const response=(points:unknown[])=>({caseId:c.caseId,tracks:[{vesselId:p.vesselId,points}]})
const parsed=parseSnapshot(c.caseId,c,v,response([p]))
check(parsed.tracks[0]!.points[0]!==p,'cloned not mutating input')
check(parsed.tracks[0]!.points[0]!.cogDeg===360,'contract inclusive360')
check(parseSnapshot(c.caseId,c,[],{caseId:c.caseId,tracks:[]}).tracks.length===0,'emptycase')
function rejects(caseRaw:unknown,vessels:unknown,tracks:unknown){let rejected=false;try{parseSnapshot(c.caseId,caseRaw,vessels,tracks)}catch{rejected=true}check(rejected,'malformed rejected')}
for(const key of ['timeSec','latDeg','lonDeg','sogKn','cogDeg'])for(const x of [null,'0',NaN,Infinity,-Infinity,{},[]])rejects(c,v,response([{...p,[key]:x}]))
for(const delta of [{latDeg:90.00001},{latDeg:-90.00001},{lonDeg:180.00001},{lonDeg:-180.00001},{sogKn:-1},{cogDeg:-.1},{cogDeg:360.00001},{hdgDeg:361},{rotDegPerMin:NaN},{timeSec:1e13},{source:null},{provenance:'Unknown'},{provenance:['Measured']},{provenance:null},{vesselId:'other'},{utc:'2026-02-30T00:00:00Z'},{utc:'2026-01-01T00:00:00+08:00'}])rejects(c,v,response([{...p,...delta}]))
for(const delta of [{latDeg:90,lonDeg:180},{latDeg:-90,lonDeg:-180},{timeSec:-1e12},{hdgDeg:null,rotDegPerMin:null},{hdgDeg:0},{hdgDeg:360},{provenance:undefined,source:undefined}])check(parseSnapshot(c.caseId,c,v,response([{...p,...delta}])).tracks[0]!.points.length===1,'valid boundary retained')
rejects({...c,caseId:'CASE-B'},v,response([p]));rejects(c,[{...v[0],caseId:'CASE-B'}],response([p]));rejects(c,v,{...response([p]),caseId:'CASE-B'});rejects(c,v,{caseId:c.caseId,tracks:[response([p]).tracks[0],response([]).tracks[0]]})
const sourcePoints=[{...p,timeSec:2},{...p,timeSec:2},{...p,timeSec:-3,source:''},{...p,timeSec:60,provenance:undefined}]
const stats=describe(parseSnapshot(c.caseId,c,v,response(sourcePoints)).tracks[0]!.points)
check(stats.duplicateTimes===1&&stats.reversedTimes===1&&stats.maxInterval===63,'descriptive timing not cleaning')
check(stats.missingSource===1&&stats.provenance.Unknown===1&&stats.count===4,'unknown never measured')
check(describe([]).maxInterval===null&&describe([]).minTime===null,'empty stats honest')
check(describe([{...p,lonDeg:179},{...p,lonDeg:-179}] as any).spansDateline,'dateline warning')
check(trackQuery('','')==='','no step default')
check(trackQuery('-2','0')==='?fromSec=-2&toSec=0','negative simulation bounds')
check(trackQuery('1e2',' 100 ')==='?fromSec=100&toSec=100','finite decimal syntax')
for(const [a,b] of [['NaN',''],['Infinity',''],['0x10',''],['1e309',''],['1e13',''],['2','1'],['1,2',''],[' ','abc']]){let err=false;try{trackQuery(a,b)}catch{err=true}check(err,'invalid range')}
for(const value of ['2026-01-01T00:00:00Z','2024-02-29T23:59:59.123Z'])check(validUtc(value),'valid UTC')
for(const value of ['2026-02-29T00:00:00Z','2026-01-01T24:00:00Z','2026-13-01T00:00:00Z','2026-01-01T00:00:60Z','not date'])check(!validUtc(value),'invalid UTC')
for(const count of [0,1,2000,2001,50000]){const idx=plotIndices(count);check(idx.length===Math.min(PLOT_LIMIT,count),'plot budget');check(new Set(idx).size===idx.length,'no repeated sampledpoint');if(count)check(idx[0]===0&&idx.at(-1)===count-1,'endpoints included')}
const big=Array.from({length:POINT_LIMIT},(_,i)=>({...p,timeSec:i}));const begin=performance.now();check(parseSnapshot(c.caseId,c,v,response(big)).tracks[0]!.points.length===POINT_LIMIT,'50k accepted');console.log(`50k parse: ${(performance.now()-begin).toFixed(1)} ms`)
let tooBig:unknown;try{parseSnapshot(c.caseId,c,v,response([...big,p]))}catch(e){tooBig=e}check(tooBig instanceof TrackDataError&&tooBig.code==='LIMIT','50k+1 rejected not truncated')
const html=renderToStaticMarkup(<TrackView snapshot={parsed}/>);check(!html.includes('<script>')&&!html.includes('<img '),'escaped labels');for(const text of ['非虚构案件','未提供','不证明证据完整或可信','不自动判定缺口或异常','UTC','非 ENC'])check(html.includes(text),'honest '+text)
check(renderToStaticMarkup(<TrackView snapshot={parseSnapshot(c.caseId,c,[],{caseId:c.caseId,tracks:[]})}/>).includes('本案没有船舶或已保存航迹'),'emptycase visible')
async function main(){
Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null,setItem:()=>{}}})
const {loadTracks}=await import('../src/tracks/api');let calls:any[]=[]
globalThis.fetch=async(url,options)=>{calls.push({url,options});return new Response(JSON.stringify(String(url).includes('/vessels')?v:String(url).includes('/tracks')?response([p]):c))}
await loadTracks(c.caseId,'Investigator\n调查员 A','?fromSec=0',new AbortController().signal)
check(calls.length===3,'parallel3 reads');check(calls.every(x=>!x.options.method&&!x.options.body),'GET only no writes');check(calls.some(x=>x.url==='/api/v1/cases/CASE-A/tracks?fromSec=0'),'read range');check(calls.every(x=>!x.url.includes('stepSec')),'never resamples');check(calls.every(x=>x.options.signal),'all reads abortable')
console.log(`W10.1 ${n} assertions passed`)
}
main().catch(e=>{console.error(e);process.exitCode=1})
