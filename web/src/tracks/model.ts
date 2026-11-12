export const POINT_LIMIT = 50000
export const METADATA_LIMIT = 1000
export const PLOT_LIMIT = 2000
export const PAGE_SIZE = 100
export const provenanceLabels = { Measured: '记录为实测', Interpolated: '记录为插值', ManualDrawn: '记录为手绘', Simulated: '记录为仿真', Unknown: '未提供来源类型' } as const
export type Provenance = Exclude<keyof typeof provenanceLabels, 'Unknown'>
export interface TrackPoint { vesselId:string; timeSec:number; utc:string; latDeg:number; lonDeg:number; sogKn:number; cogDeg:number; hdgDeg?:number|null; rotDegPerMin?:number|null; provenance?:Provenance; source?:string }
export interface Track {vesselId:string; points:TrackPoint[]}
export interface TrackCase {caseId:string; title:string; isFictionalDemo:boolean; caseEpochUtc:string}
export interface TrackVessel {vesselId:string; name:string}
export interface Snapshot {case:TrackCase; vessels:TrackVessel[]; tracks:Track[]}
export class TrackDataError extends Error { code:'FORMAT'|'LIMIT'|'METADATA_LIMIT'; constructor(code:'FORMAT'|'LIMIT'|'METADATA_LIMIT'){super(code);this.code=code} }
function fail(): never {throw new TrackDataError('FORMAT')}
function record(v:unknown):Record<string,unknown>{if(!v||typeof v!=='object'||Array.isArray(v))fail();return v as Record<string,unknown>}
function nonempty(v:unknown):v is string{return typeof v==='string'&&!!v.trim()}
function finite(v:unknown):v is number{return typeof v==='number'&&Number.isFinite(v)}
function angle(v:unknown):v is number{return finite(v)&&v>=0&&v<=360}
export function validUtc(v:unknown):v is string {
  if(typeof v!=='string'||!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$/.test(v))return false
  const date=new Date(v)
  return Number.isFinite(date.getTime())&&date.toISOString().slice(0,19)===v.slice(0,19)
}
export function parseSnapshot(caseId:string,caseRaw:unknown,vesselsRaw:unknown,tracksRaw:unknown):Snapshot {
  const c=record(caseRaw),r=record(tracksRaw)
  if(c.caseId!==caseId||!nonempty(c.title)||typeof c.isFictionalDemo!=='boolean'||!validUtc(c.caseEpochUtc)||r.caseId!==caseId||!Array.isArray(r.tracks)||!Array.isArray(vesselsRaw))fail()
  if(r.tracks.length>METADATA_LIMIT||vesselsRaw.length>METADATA_LIMIT)throw new TrackDataError('METADATA_LIMIT')
  const vesselIds=new Set<string>()
  const vessels=vesselsRaw.map(v=>{const x=record(v);if(x.caseId!==caseId||!nonempty(x.vesselId)||vesselIds.has(x.vesselId)||!nonempty(x.name))fail();vesselIds.add(x.vesselId);return {vesselId:x.vesselId,name:x.name}})
  const ids=new Set<string>();let total=0
  const tracks=r.tracks.map(raw=>{
    const t=record(raw)
    if(!nonempty(t.vesselId)||ids.has(t.vesselId)||!Array.isArray(t.points))fail()
    ids.add(t.vesselId);total+=t.points.length;if(total>POINT_LIMIT)throw new TrackDataError('LIMIT')
    const points=t.points.map(rawPoint=>{
      const p=record(rawPoint)
      if(p.vesselId!==t.vesselId||!finite(p.timeSec)||Math.abs(p.timeSec)>1e12||!validUtc(p.utc)||!finite(p.latDeg)||Math.abs(p.latDeg)>90||!finite(p.lonDeg)||Math.abs(p.lonDeg)>180||!finite(p.sogKn)||p.sogKn<0||!angle(p.cogDeg))fail()
      if(p.hdgDeg!=null&&!angle(p.hdgDeg))fail()
      if(p.rotDegPerMin!=null&&!finite(p.rotDegPerMin))fail()
      if(p.provenance!==undefined&&(typeof p.provenance!=='string'||!['Measured','Interpolated','ManualDrawn','Simulated'].includes(p.provenance)))fail()
      if(p.source!==undefined&&typeof p.source!=='string')fail()
      return {...p} as unknown as TrackPoint
    })
    return {vesselId:t.vesselId,points}
  })
  return {case:{caseId,title:c.title,isFictionalDemo:c.isFictionalDemo,caseEpochUtc:c.caseEpochUtc},vessels,tracks}
}
export function trackQuery(from:string,to:string):string {
  const parse=(s:string)=>{if(!s.trim())return undefined;if(!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(s.trim()))throw Error('时间窗请输入有限十进制秒数。');const n=Number(s);if(!Number.isFinite(n)||Math.abs(n)>1e12)throw Error('时间窗必须在 ±10¹² 秒内。');return n}
  const a=parse(from),b=parse(to);if(a!==undefined&&b!==undefined&&a>b)throw Error('起始时间不能晚于结束时间。')
  const params=new URLSearchParams();if(a!==undefined)params.set('fromSec',String(a));if(b!==undefined)params.set('toSec',String(b));return params.size?'?'+params.toString():''
}
export function describe(points:TrackPoint[]) {
  let minTime=Infinity,maxTime=-Infinity,minLon=Infinity,maxLon=-Infinity,maxInterval:number|null=null,duplicateTimes=0,reversedTimes=0,missingSource=0
  const provenance:Record<keyof typeof provenanceLabels,number>={Measured:0,Interpolated:0,ManualDrawn:0,Simulated:0,Unknown:0}
  for(let i=0;i<points.length;i++){
    const p=points[i]!;minTime=Math.min(minTime,p.timeSec);maxTime=Math.max(maxTime,p.timeSec);minLon=Math.min(minLon,p.lonDeg);maxLon=Math.max(maxLon,p.lonDeg)
    provenance[p.provenance??'Unknown']++;if(!p.source?.trim())missingSource++
    if(i){const delta=p.timeSec-points[i-1]!.timeSec;if(delta===0)duplicateTimes++;else if(delta<0)reversedTimes++;else maxInterval=Math.max(maxInterval??0,delta)}
  }
  return {count:points.length,minTime:points.length?minTime:null,maxTime:points.length?maxTime:null,maxInterval,duplicateTimes,reversedTimes,missingSource,provenance,spansDateline:maxLon-minLon>180}
}
export function plotIndices(length:number):number[]{
  if(length<=PLOT_LIMIT)return Array.from({length},(_,i)=>i)
  return Array.from({length:PLOT_LIMIT},(_,i)=>Math.floor(i*(length-1)/(PLOT_LIMIT-1)))
}
