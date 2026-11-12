import { parseSnapshot, validUtc, type TrackPoint, type TrackCase, type TrackVessel } from '../tracks/model'
export interface Row {timeSec:number;utc:string;own:TrackPoint;target:TrackPoint;currentDistanceNm:number;dcpaNm:number;tcpaMin:number|null;isDegenerate:boolean;isDiverging:boolean}
export interface Result extends TrackCase {profile:'MCIS-CURRENT-CPA-1';origin:{latDeg:number;lonDeg:number};vessels:TrackVessel[];window:{fromSec:number|null;toSec:number|null};inputDigest:string;coreVersion:string|null;counts:{own:number;target:number;matched:number;unmatchedOwn:number;unmatchedTarget:number};rows:Row[]}
export const ASSUMPTIONS='【推算】按已存 SOG/COG 假定两船瞬时匀速直线，WGS84 点位转案件原点 ENU 水平面。不代表实际未来航迹；位置参考点未知，不是船中心距、船体净距或天线改正结果。'
export const COVERAGE='只配对完全相同的相对秒，核对 UTC 与案件纪元；不生成插值、不外推、不补端点。匹配不等于真实同时采样，来源标签不等于真实性认证。未匹配点和未采样时段不在结果内，不能据此认定整段航程最小距离。'
function object(v:unknown):Record<string,unknown>{if(!v||typeof v!=='object'||Array.isArray(v))throw Error('计算响应格式不符，未显示结果。');return v as Record<string,unknown>}
function numeric(v:unknown):v is number{return typeof v==='number'&&Number.isFinite(v)}
function fail():never{throw Error('计算响应与本案、船舶、时间窗或输入口径不符，未显示结果。')}
export function parseMetadata(caseId:string,c:unknown,v:unknown){return parseSnapshot(caseId,c,v,{caseId,tracks:[]})}
export function parseResult(raw:unknown,caseId:string,own:string,target:string,from:number|null,to:number|null):Result {
 const d=object(raw),w=object(d.window),c=object(d.counts),origin=object(d.origin)
 if(d.profile!=='MCIS-CURRENT-CPA-1'||d.caseId!==caseId||!Array.isArray(d.rows)||d.rows.length>5000||!Array.isArray(d.vessels)||d.vessels.length!==2||w.fromSec!==from||w.toSec!==to||typeof d.inputDigest!=='string'||!/^[a-f0-9]{64}$/.test(d.inputDigest))fail()
 if(!numeric(origin.latDeg)||Math.abs(origin.latDeg)>85||!numeric(origin.lonDeg)||Math.abs(origin.lonDeg)>180)fail()
 const vessels:Record<string,unknown>[]=d.vessels.map(v=>({...object(v),caseId}))
 if(vessels[0]?.vesselId!==own||vessels[1]?.vesselId!==target)fail()
 const rows=d.rows.map(object)
 const snapshot=parseSnapshot(caseId,d,vessels,{caseId,tracks:[{vesselId:own,points:rows.map(r=>r.own)},{vesselId:target,points:rows.map(r=>r.target)}]})
 for(const key of ['own','target','matched','unmatchedOwn','unmatchedTarget'])if(!Number.isSafeInteger(c[key])||(c[key] as number)<0||(c[key] as number)>5000)fail()
 if(c.matched!==rows.length||Number(c.own)!==rows.length+Number(c.unmatchedOwn)||Number(c.target)!==rows.length+Number(c.unmatchedTarget))fail()
 if(rows.length?(typeof d.coreVersion!=='string'||!d.coreVersion):(d.coreVersion!==null))fail()
 let previous=-Infinity
 rows.forEach((r,i)=>{
  const a=snapshot.tracks[0]!.points[i]!,b=snapshot.tracks[1]!.points[i]!
  if(!numeric(r.timeSec)||r.timeSec<=previous||!validUtc(r.utc)||r.timeSec!==a.timeSec||r.timeSec!==b.timeSec||Date.parse(r.utc)!==Date.parse(a.utc)||Date.parse(r.utc)!==Date.parse(b.utc)||Math.abs((Date.parse(r.utc)-Date.parse(snapshot.case.caseEpochUtc))/1000-r.timeSec)>1e-6)fail()
  if((from!==null&&r.timeSec<from)||(to!==null&&r.timeSec>to))fail()
  previous=r.timeSec
  for(const k of ['currentDistanceNm','dcpaNm'])if(!numeric(r[k])||r[k]<0)fail()
  if(typeof r.isDegenerate!=='boolean'||typeof r.isDiverging!=='boolean')fail()
  if(r.isDegenerate?(r.tcpaMin!==null||r.isDiverging):(!numeric(r.tcpaMin)||(r.tcpaMin!==0&&r.isDiverging!==(r.tcpaMin<0))))fail()
 })
 return d as unknown as Result
}
