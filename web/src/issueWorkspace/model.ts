export type Kind='judgment'|'verification'|'discussion';
export type Entry={kind:Kind,note:string,sourceIds:string[],outcome:'supports'|'refutes'|'inconclusive'|null,againstJudgment:number|null};
export type VersionState={evidenceId:string,status:'current'|'needs_review'|'unavailable'};
export type Event=Entry&{seq:number,recordedUtc:string,sourceVersionStates?:VersionState[]};
/** Read-time states are not append-only journal content. */
export function immutableEvents(events:Event[]){return events.map(({sourceVersionStates,...event})=>event)}
function parseVersionStates(e:any):VersionState[]|undefined{
 if(!Object.hasOwn(e,'sourceVersionStates'))return undefined;
 const a=e.sourceVersionStates;
 if(!Array.isArray(a)||a.length!==e.sourceIds.length)throw Error('invalid version states');
 const seen=new Set<string>();
 return a.map((x:any)=>{
  if(!x||typeof x!=='object'||Array.isArray(x)||Object.keys(x).sort().join('|')!=='evidenceId|status'||!e.sourceIds.includes(x.evidenceId)||seen.has(x.evidenceId)||!['current','needs_review','unavailable'].includes(x.status))throw Error('invalid version state');
  seen.add(x.evidenceId);return {evidenceId:x.evidenceId,status:x.status};
 });
}
export type History={caseId:string,issueId:string,revision:number,status:'working_unreviewed',events:Event[]};
export type SourcePin={evidenceId:string,sourceIncarnation:string,sourceSha256:string};
export class JournalWriteConflict extends Error{constructor(){super('试验服务明确拒绝本次追加');this.name='JournalWriteConflict'}}
export class SourceSelectionChanged extends Error{constructor(){super("来源版本已变化，请重新读取并选择");this.name="SourceSelectionChanged"}}
export type Command={sourcePins?:SourcePin[],caseId:string,issueId:string,operationId:string,expectedRevision:number,entry:Entry};
/** No URL/credential transport. Implementer must use current server authority, not browser role headers. */
export type SourceCandidate={sourceIncarnation:string,evidenceId:string,sourceSha256:string,mediaKind:"csv"|"pdf",byteLength:number,registeredUtc:string};
export function parseSources(value:any,caseId:string):SourceCandidate[]{
 if(!value||value.profile!=="trial-issue-sources-v1"||value.caseId!==caseId||value.scope!=="current-local-supported-candidates-only"||!Array.isArray(value.items)||value.items.length>100)throw Error("Invalid sources");
 const ids=new Set<string>();return value.items.map((s:any)=>{if(!s||typeof s.evidenceId!=="string"||!s.evidenceId||s.evidenceId.length>64||ids.has(s.evidenceId)||typeof s.sourceIncarnation!=="string"||! /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(s.sourceIncarnation)||typeof s.sourceSha256!=="string"||! /^[0-9a-f]{64}$/.test(s.sourceSha256)||!["csv","pdf"].includes(s.mediaKind)||!Number.isSafeInteger(s.byteLength)||s.byteLength<0||typeof s.registeredUtc!=="string"||!Number.isFinite(Date.parse(s.registeredUtc)))throw Error("Invalid source");ids.add(s.evidenceId);return {sourceIncarnation:s.sourceIncarnation,evidenceId:s.evidenceId,sourceSha256:s.sourceSha256,mediaKind:s.mediaKind,byteLength:s.byteLength,registeredUtc:s.registeredUtc}});
}
export type IssueSummary={issueId:string,revision:number,openingNotePreview:string,lastKind:Kind,status:'working_unreviewed'};
export function parseIssueList(value:any,caseId:string):IssueSummary[]{
 if(!value||value.profile!=='trial-issue-list-v1'||value.caseId!==caseId||!Array.isArray(value.items)||value.items.length>100)throw Error('Invalid issue list');
 const ids=new Set<string>();return value.items.map((x:any)=>{if(!x||typeof x.issueId!=='string'||!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(x.issueId)||ids.has(x.issueId)||!Number.isInteger(x.revision)||x.revision<1||x.revision>200||typeof x.openingNotePreview!=='string'||x.openingNotePreview.length>200||!['judgment','verification','discussion'].includes(x.lastKind)||x.status!=='working_unreviewed')throw Error('Invalid issue summary');ids.add(x.issueId);return {issueId:x.issueId,revision:x.revision,openingNotePreview:x.openingNotePreview,lastKind:x.lastKind,status:'working_unreviewed'}});
}
export interface JournalPort{list?(caseId:string):Promise<unknown>;sources?(caseId:string):Promise<unknown>;save(command:Command):Promise<unknown>;read(caseId:string,issueId:string):Promise<unknown>}
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
  const states=parseVersionStates(e);
  return {...(states===undefined?{}:{sourceVersionStates:states}),seq:e.seq,kind:e.kind,note:e.note,recordedUtc:e.recordedUtc,sourceIds:[...e.sourceIds],outcome:e.outcome,againstJudgment:e.againstJudgment} as Event;
 });return {caseId,issueId,revision:x.revision,status:'working_unreviewed',events};
}
export function createRehearsalPort():JournalPort{
 const histories=new Map<string,History>();const operations=new Map<string,string>();
 return {async save(command){
  const c=structuredClone(command);if(c.caseId!=='CASE-ISSUE-FICTIONAL')throw Error('fictional only');
  const history=histories.get(c.issueId);const wire=JSON.stringify(c);const prior=operations.get(c.operationId);
  if(prior){if(prior!==wire)throw Error('conflict');return structuredClone(history&&{...history,events:history.events.map(e=>({...e,status:'working_unreviewed'}))})}
  if(c.expectedRevision!==(history?.revision??0)||history&&history.issueId!==c.issueId)throw Error('conflict');
  const next={caseId:c.caseId,issueId:c.issueId,status:'working_unreviewed',revision:c.expectedRevision+1,events:[...(history?.events.map(e=>({...e,status:'working_unreviewed'}))??[]),{...c.entry,status:'working_unreviewed',seq:c.expectedRevision+1,recordedUtc:new Date().toISOString()}]};
  const saved=parse(next,c.caseId,c.issueId);histories.set(c.issueId,saved);operations.set(c.operationId,wire);return structuredClone({...saved,events:saved.events.map(e=>({...e,status:'working_unreviewed'}))});
 },async list(caseId){if(caseId!=='CASE-ISSUE-FICTIONAL')throw Error('fictional only');return {profile:'trial-issue-list-v1',caseId,items:[...histories.values()].map(h=>({issueId:h.issueId,revision:h.revision,openingNotePreview:h.events[0].note.slice(0,200),lastKind:h.events.at(-1)!.kind,status:'working_unreviewed'}))}},async read(caseId,issueId){const history=histories.get(issueId);if(!history||history.caseId!==caseId||history.issueId!==issueId)throw Error('missing');return structuredClone(history&&{...history,events:history.events.map(e=>({...e,status:'working_unreviewed'}))})}};
}
