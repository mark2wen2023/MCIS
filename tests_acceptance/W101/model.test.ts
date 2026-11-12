import assert from 'node:assert/strict'
import {parseSnapshot,describe,plotIndices,trackQuery} from '../../web/src/tracks/model'
let n=0;function check(name:string,fn:()=>void){fn();n++;console.log('PASS '+name)}
const c={caseId:'QA',title:'QA fixture',isFictionalDemo:true,caseEpochUtc:'2026-01-01T00:00:00Z'}
const v=[{caseId:'QA',vesselId:'V',name:'v'}]
const p={vesselId:'V',timeSec:-1,utc:'2025-12-31T23:59:59Z',latDeg:-90,lonDeg:-180,sogKn:0,cogDeg:360,source:'<svg onload=alert(1)>'}
const raw=(points:any[])=>({caseId:'QA',tracks:[{vesselId:'V',points}]})
check('preserve exact stored values and unknown provenance',()=>{const out=parseSnapshot('QA',c,v,raw([p]));assert.deepEqual(out.tracks[0].points[0],p);assert.notEqual(out.tracks[0].points[0],p);assert.equal(out.tracks[0].points[0].provenance,undefined)})
for(const bad of [null,[],{},'x'])check('reject wrong envelope '+String(bad),()=>assert.throws(()=>parseSnapshot('QA',c,v,bad)))
for(const [k,bad] of Object.entries({timeSec:Infinity,latDeg:90.0000001,lonDeg:-180.0000001,sogKn:-0.0001,cogDeg:360.00001,hdgDeg:-1,rotDegPerMin:NaN,utc:'2026-02-30T00:00:00Z',source:7,provenance:'AI'}))check('reject '+k,()=>assert.throws(()=>parseSnapshot('QA',c,v,raw([{...p,[k]:bad}]))))
check('reject wrong point ID',()=>assert.throws(()=>parseSnapshot('QA',c,v,raw([{...p,vesselId:'OTHER'}]))))
check('reject wrong response case',()=>assert.throws(()=>parseSnapshot('QA',c,v,{...raw([p]),caseId:'OTHER'})))
check('reject duplicate bucket',()=>assert.throws(()=>parseSnapshot('QA',c,v,{caseId:'QA',tracks:[{vesselId:'V',points:[]},{vesselId:'V',points:[]}]})))
check('reject duplicate vessel',()=>assert.throws(()=>parseSnapshot('QA',c,[...v,...v],raw([]))))
check('50000 exact allowed unchanged',()=>assert.equal(parseSnapshot('QA',c,v,raw(Array(50000).fill(p))).tracks[0].points.length,50000))
check('50001 rejected whole batch',()=>assert.throws(()=>parseSnapshot('QA',c,v,raw(Array(50001).fill(p)))))
for(const length of [0,1,1999,2000,2001,50000])check('plot actual indices '+length,()=>{const ids=plotIndices(length);assert.equal(ids.length,Math.min(length,2000));assert.equal(new Set(ids).size,ids.length);assert.ok(ids.every(i=>Number.isInteger(i)&&i>=0&&i<length));if(length){assert.equal(ids[0],0);assert.equal(ids.at(-1),length-1)}})
check('statistics do not repair returned order',()=>{const points=[{...p,timeSec:3},{...p,timeSec:3},{...p,timeSec:1},{...p,timeSec:11,lonDeg:180}];const before=JSON.stringify(points);const d=describe(points);assert.equal(d.duplicateTimes,1);assert.equal(d.reversedTimes,1);assert.equal(d.maxInterval,10);assert.ok(d.spansDateline);assert.equal(JSON.stringify(points),before)})
for(const [a,b] of [['Infinity',''],['0x10',''],['1','0'],['1e13',''],['NaN','']])check('window rejects '+a+':'+b,()=>assert.throws(()=>trackQuery(a,b)))
check('window omits resampling',()=>assert.equal(trackQuery('-1','0'),'?fromSec=-1&toSec=0'))
// Separate engineering metadata budget, not a maritime limit.
check('allow exactly 1000 vessels metadata',()=>assert.equal(parseSnapshot('QA',c,Array.from({length:1000},(_,i)=>({caseId:'QA',vesselId:'V'+i,name:'v'})),raw([])).vessels.length,1000))
check('allow exactly 1000 empty buckets',()=>assert.equal(parseSnapshot('QA',c,[],{caseId:'QA',tracks:Array.from({length:1000},(_,i)=>({vesselId:'V'+i,points:[]}))}).tracks.length,1000))
check('reject 1001 vessels metadata',()=>assert.throws(()=>parseSnapshot('QA',c,Array.from({length:1001},(_,i)=>({caseId:'QA',vesselId:'V'+i,name:'v'})),raw([]))))
check('reject 1001 empty track buckets',()=>assert.throws(()=>parseSnapshot('QA',c,[],{caseId:'QA',tracks:Array.from({length:1001},(_,i)=>({vesselId:'V'+i,points:[]}))})))
console.log(n+' independent model checks passed')
