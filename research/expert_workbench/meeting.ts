import {strictJson} from '../../web/src/reportOutput/strictJson'
import {packet,PACKET_SHA,type Review} from './model'
export const DISPLAY_MAX_BYTES=1024*1024
export type MeetingRole={roleId:string;ticketId:string|null;status:string;modelCalls:number;toolCalls:number;contextDigest:string|null;reviews:Review[]}
export type MeetingDisplay={schema:string;receiptSha256:string;packetSha256:string;meetingId:string;meetingPhase:string;transportMode:'remote'|'remote_mock';realDeepSeekExecuted:boolean;receiptComplete:boolean;hold:true;factActivated:false;consensusComputed:false;authenticityVerified:false;budget:{totalModels:number;totalTools:number;received:number;unknown:number;notDispatched:number;limits:{models:16;tools:32}};rounds:{number:number;roles:MeetingRole[]}[]}
const fail=():never=>{throw Error('会议展示数据不符合冻结来源与只读边界')}
const keys=(v:any,names:string[])=>{if(!v||typeof v!=='object'||Array.isArray(v)||Object.keys(v).length!==names.length||names.some(k=>!Object.hasOwn(v,k)))fail()}
const count=(n:any,max:number)=>Number.isSafeInteger(n)&&n>=0&&n<=max
const hash=(s:any)=>typeof s==='string'&&/^[a-f0-9]{64}$/.test(s)
const roles=['source_attribution','uncertainty_boundary']
export function parseMeeting(bytes:Uint8Array):MeetingDisplay{
 if(bytes.length>DISPLAY_MAX_BYTES)fail()
 const d:any=strictJson(bytes)
 keys(d,['schema','receiptSha256','packetSha256','meetingId','meetingPhase','transportMode','realDeepSeekExecuted','receiptComplete','hold','factActivated','consensusComputed','authenticityVerified','budget','rounds'])
 if(d.schema!=='mcis.expert-meeting-display.v1'||!hash(d.receiptSha256)||d.packetSha256!==PACKET_SHA||typeof d.meetingId!=='string'||!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(d.meetingId))fail()
 if(!['ready','round_open','round_review','completed_unverified','stopped_by_operator','stopped_failed','stopped_unknown','timed_out'].includes(d.meetingPhase)||!['remote','remote_mock'].includes(d.transportMode))fail()
 if(typeof d.realDeepSeekExecuted!=='boolean'||typeof d.receiptComplete!=='boolean'||d.hold!==true||d.factActivated!==false||d.consensusComputed!==false||d.authenticityVerified!==false)fail()
 if(d.transportMode==='remote_mock'&&d.realDeepSeekExecuted)fail()
 keys(d.budget,['totalModels','totalTools','received','unknown','notDispatched','limits']);keys(d.budget.limits,['models','tools'])
 if(d.budget.limits.models!==16||d.budget.limits.tools!==32||!count(d.budget.totalModels,16)||!count(d.budget.totalTools,32))fail()
 for(const k of ['received','unknown','notDispatched'])if(!count(d.budget[k],16))fail()
 if(d.budget.received+d.budget.unknown+d.budget.notDispatched>d.budget.totalModels)fail()
 if(d.realDeepSeekExecuted!==(d.transportMode==='remote'&&d.budget.received>0))fail()
 if(!Array.isArray(d.rounds)||d.rounds.length>2)fail()
 let models=0,tools=0,completed=0,completedModels=0
 for(const [index,round] of d.rounds.entries()){
  keys(round,['number','roles']);if(round.number!==index+1||!Array.isArray(round.roles)||round.roles.length!==2)fail()
  if(index>0&&d.rounds[index-1].roles.some((r:MeetingRole)=>r.status!=='completed_unverified'))fail()
  for(const [ri,role] of round.roles.entries()){
   keys(role,['roleId','ticketId','status','modelCalls','toolCalls','contextDigest','reviews'])
   if(role.roleId!==roles[ri]||!['not_started','unknown','not_accepted','completed_unverified'].includes(role.status)||!count(role.modelCalls,4)||!count(role.toolCalls,8)||!Array.isArray(role.reviews))fail()
   if(role.ticketId!==null&&role.ticketId!==`${d.meetingId}:${index+1}:${role.roleId}`)fail()
   if((role.ticketId===null)!==(role.contextDigest===null)||(role.contextDigest!==null&&!hash(role.contextDigest)))fail()
   if(role.ticketId===null&&(role.status!=='not_started'||role.modelCalls||role.toolCalls))fail()
   if(role.status==='not_started'&&(role.modelCalls||role.toolCalls))fail()
   models+=role.modelCalls;tools+=role.toolCalls
   if(role.status==='completed_unverified'){
    completed++;completedModels+=role.modelCalls;if(role.modelCalls<2||role.toolCalls<2||role.reviews.length!==3||role.ticketId===null)fail()
    const ids=new Set<string>()
    for(const review of role.reviews){
     keys(review,['itemId','label','quote','rationale','uncertainty'])
     if(Object.values(review).some(v=>typeof v!=='string'||!v.trim()||[...v].length>2000))fail()
     const item=packet.items.find(i=>i.itemId===review.itemId)
     if(!item||ids.has(review.itemId)||!['supported','conflicted','insufficient'].includes(review.label)||!item.sourceText.includes(review.quote))fail()
     ids.add(review.itemId)
    }
   }else if(role.reviews.length)fail()
  }
  const issued=round.roles.filter((r:MeetingRole)=>r.contextDigest!==null)
  if(issued.length===2&&issued[0].contextDigest!==issued[1].contextDigest)fail()
 }
 if(models!==d.budget.totalModels||tools!==d.budget.totalTools||d.budget.received<completedModels)fail()
 if(d.meetingPhase==='ready'&&d.rounds.length)fail()
 if(d.meetingPhase==='round_review'&&(d.rounds.length!==1||completed!==2))fail()
 if(d.meetingPhase==='round_open'&&(!d.rounds.length||d.rounds.at(-1).roles.every((r:MeetingRole)=>r.status==='completed_unverified')))fail()
 if(d.meetingPhase==='completed_unverified'&&(completed!==4||d.budget.received!==models||d.budget.unknown||d.budget.notDispatched))fail()
 return d
}

export function compareRoles(r:{roles:{status:string;reviews:Review[]}[]},id:string){
 const reviews=r.roles.map(role=>role.status==='completed_unverified'?role.reviews.find(row=>row.itemId===id):undefined)
 return {reviews,kind:!reviews[0]||!reviews[1]?'missing':reviews[0].label===reviews[1].label?'same':'different'}
}
