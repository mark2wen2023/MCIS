import { strictJson } from '../../web/src/reportOutput/strictJson'
import packet from '../expert_group/public-packet.json'
export { packet }
export const PACKET_SHA = '1dc5f6ccd93da013863abfd399b8e3f8682d2532e62d335eaa23cd5e18d8790e'
const MANIFEST_SHA = '71cd8de0fdf4a9e9137db32e7a299b125f7ad107b1c9d8073c34c31ee70c4052'
export const MAX_BYTES = 1024 * 1024
export const ROLE_NAMES = ['来源与对象归属', '限定词与推断边界']
export type Review = {itemId:string;label:'supported'|'conflicted'|'insufficient';quote:string;rationale:string;uncertainty:string}
export type Role = {roleId:string;runId:string;status:string;reviews:Review[];modelCalls:number;toolCalls:number}
export type Result = {runId:string;status:string;outcome:string;transportMocked:boolean;realModel:boolean;realPi:boolean;providerRequests:number;roles:Role[];errorCode?:string}
const fail = ():never => {throw Error('结果结构、来源绑定或未核实边界不符合 a686c85；未载入。')}
const obj = (v:any) => v && typeof v === 'object' && !Array.isArray(v)
function keys(v:any, fields:string[], optional:string[] = []) {if (!obj(v) || fields.some(k=>!Object.hasOwn(v,k)) || Object.keys(v).some(k=>!fields.includes(k)&&!optional.includes(k))) fail()}
const count = (v:any,max:number) => Number.isSafeInteger(v)&&v>=0&&v<=max
const uuid = (v:any) => typeof v==='string'&&/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(v)
export function parseResult(bytes:Uint8Array):Result {
  if(bytes.length>MAX_BYTES) throw Error('仅接受不超过 1 MiB 的结果 JSON；不会读取原PDF或上传。')
  const r:any = strictJson(bytes)
  keys(r,['runId','status','outcome','packetSha256','manifestDigest','transportMocked','realPi','realModel','provider','configuredModel','piVersion','modelIdentityVerified','sourceLocatorVerified','factActivated','consensusComputed','providerRequests','roles','artifactPolicy'],['errorCode'])
  if(r.packetSha256!==PACKET_SHA||r.manifestDigest!==MANIFEST_SHA||r.provider!=='deepseek'||r.configuredModel!=='deepseek-v4-pro'||r.piVersion!=='1.5.2'||r.artifactPolicy!=='incomplete_without_valid_completion_manifest') fail()
  if(!uuid(r.runId)||!['completed_unverified','not_accepted'].includes(r.status)||!['completed','failed','unknown','cancelled'].includes(r.outcome)) fail()
  for(const k of ['modelIdentityVerified','sourceLocatorVerified','factActivated','consensusComputed']) if(r[k]!==false) fail()
  for(const k of ['transportMocked','realModel','realPi']) if(typeof r[k]!=='boolean') fail()
  if(!count(r.providerRequests,8)||!Array.isArray(r.roles)||r.roles.length!==2) fail()
  if(r.errorCode!==undefined&&(typeof r.errorCode!=='string'||!/^[-a-z_]{1,80}$/.test(r.errorCode))) fail()
  r.roles.forEach((role:any,index:number)=>{
    keys(role,['roleId','runId','status','reviews','modelCalls','toolCalls'])
    if(role.roleId!==['source_attribution','uncertainty_boundary'][index]||!uuid(role.runId)||!['completed_unverified','not_started','not_accepted'].includes(role.status)||!count(role.modelCalls,4)||!count(role.toolCalls,8)||!Array.isArray(role.reviews)) fail()
    if(role.status==='not_started'&&(role.modelCalls!==0||role.toolCalls!==0)) fail()
    if(role.status==='completed_unverified') {
      if(role.modelCalls<2||role.toolCalls<2) fail()
      if(role.reviews.length!==packet.items.length||!r.realPi) fail()
      const seen=new Set<string>()
      for(const row of role.reviews){
        keys(row,['itemId','label','quote','rationale','uncertainty'])
        if(Object.values(row).some(v=>typeof v!=='string'||!v.trim()||[...v].length>12000)) fail()
        const item=packet.items.find(i=>i.itemId===row.itemId)
        if(!item||seen.has(row.itemId)||!['supported','conflicted','insufficient'].includes(row.label)||!item.sourceText.includes(row.quote)) fail()
        seen.add(row.itemId)
      }
    } else if(role.reviews.length!==0) fail()
  })
  if(new Set([r.runId,...r.roles.map((role:Role)=>role.runId)]).size!==3) fail()
  if(r.providerRequests>r.roles.reduce((n:number,role:Role)=>n+role.modelCalls,0)) fail()
  if(r.transportMocked&&(r.realModel||r.providerRequests!==0)) fail()
  if(r.realModel&&r.providerRequests===0) fail()
  if(r.status==='completed_unverified') {
    if(!r.transportMocked&&r.providerRequests!==r.roles.reduce((n:number,role:Role)=>n+role.modelCalls,0)) fail()
    if(r.outcome!=='completed'||r.roles.some((role:Role)=>role.status!=='completed_unverified')||(!r.transportMocked&&!r.realModel)||r.errorCode!==undefined) fail()
  } else if(r.outcome==='completed') fail()
  return r
}
export function mode(r:Result) {
  if(r.transportMocked) return '脚本模拟提供方 · 非真实模型验收'
  return r.realModel ? '声明收到真实提供方响应 · 身份及能力未认证' : '真实提供方模式声明 · 未声明收到模型响应'
}
export function comparison(r:Result,id:string) {
  const reviews=r.roles.map(role=>role.status==='completed_unverified'?role.reviews.find(row=>row.itemId===id):undefined)
  return {reviews,kind:!reviews[0]||!reviews[1]?'missing':reviews[0].label===reviews[1].label?'same':'different'}
}
