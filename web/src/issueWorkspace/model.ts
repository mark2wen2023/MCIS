export type Kind='judgment'|'verification'|'discussion';
export type Entry={kind:Kind,note:string,sourceIds:string[],outcome:'supports'|'refutes'|'inconclusive'|null,againstJudgment:number|null};
export type Event=Entry&{seq:number,recordedUtc:string};
export type History={caseId:string,issueId:string,revision:number,status:'working_unreviewed',events:Event[]};
export type Command={caseId:string,issueId:string,operationId:string,expectedRevision:number,entry:Entry};
/** No URL/credential transport. Implementer must use current server authority, not browser role headers. */
export interface JournalPort{save(command:Command):Promise<unknown>;read(caseId:string,issueId:string):Promise<unknown>}
export function latest(history?:History){return history?.events.filter(e=>e.kind==='judgment').at(-1)?.seq??0}
export function canDiscuss(history?:History){const n=latest(history);return !!n&&!!history?.events.some(e=>e.kind==='verification'&&e.againstJudgment===n)}
export function parse(value:unknown,caseId:string,issueId:string):History{
 const x=value as any;
 if(!x||x.caseId!==caseId||x.issueId!==issueId||x.status!=='working_unreviewed'||!Array.isArray(x.events)||x.events.length<1||x.events.length>200||x.revision!==x.events.length)throw Error('invalid');
 let judgment=0,verified=false;
 const events=x.events.map((e:any,i:number)=>{
  if(!e||e.status!=='working_unreviewed'||e.seq!==i+1||!['judgment','verification','discussion'].includes(e.kind)||typeof e.note!=='string'||!e.note.trim()||e.note.length>8000||typeof e.recordedUtc!=='string'||!Number.isFinite(Date.parse(e.recordedUtc))||!Array.isArray(e.sourceIds)||e.sourceIds.length>20||e.sourceIds.some((s:unknown)=>typeof s!=='string'||!s||s.length>64)||new Set(e.sourceIds).size!==e.sourceIds.length)throw Error('invalid');
  if(e.kind==='judgment'){if(e.againstJudgment!==null||e.outcome!==null)throw Error('invalid');judgment=e.seq;verified=false}
  else{if(!judgment||e.againstJudgment!==judgment)throw Error('invalid');if(e.kind==='verification'){if(!['supports','refutes','inconclusive'].includes(e.outcome))throw Error('invalid');verified=true}else if(!verified||e.outcome!==null)throw Error('invalid')}
  return {seq:e.seq,kind:e.kind,note:e.note,recordedUtc:e.recordedUtc,sourceIds:[...e.sourceIds],outcome:e.outcome,againstJudgment:e.againstJudgment} as Event;
 });return {caseId,issueId,revision:x.revision,status:'working_unreviewed',events};
}
export function createRehearsalPort():JournalPort{
 let history:History|undefined;const operations=new Map<string,string>();
 return {async save(command){
  const c=structuredClone(command);if(c.caseId!=='CASE-ISSUE-FICTIONAL')throw Error('fictional only');
  const wire=JSON.stringify(c);const prior=operations.get(c.operationId);
  if(prior){if(prior!==wire)throw Error('conflict');return structuredClone(history&&{...history,events:history.events.map(e=>({...e,status:'working_unreviewed'}))})}
  if(c.expectedRevision!==(history?.revision??0)||history&&history.issueId!==c.issueId)throw Error('conflict');
  const next={caseId:c.caseId,issueId:c.issueId,status:'working_unreviewed',revision:c.expectedRevision+1,events:[...(history?.events.map(e=>({...e,status:'working_unreviewed'}))??[]),{...c.entry,status:'working_unreviewed',seq:c.expectedRevision+1,recordedUtc:new Date().toISOString()}]};
  history=parse(next,c.caseId,c.issueId);operations.set(c.operationId,wire);return structuredClone(history&&{...history,events:history.events.map(e=>({...e,status:'working_unreviewed'}))});
 },async read(caseId,issueId){if(!history||history.caseId!==caseId||history.issueId!==issueId)throw Error('missing');return structuredClone(history&&{...history,events:history.events.map(e=>({...e,status:'working_unreviewed'}))})}};
}
