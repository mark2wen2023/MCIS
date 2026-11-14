import {parse,parseSources,type JournalPort} from './model';
const PROFILE='mcis-issue-host-trial-v1';
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
function isUuid(value:unknown):value is string{return typeof value==='string'&&uuid.test(value)}
function keys(value:any,allowed:string[]){if(!value||typeof value!=='object'||Array.isArray(value)||Object.keys(value).sort().join('|')!==[...allowed].sort().join('|'))throw Error('Invalid trial request')}
/** Host-owned IPC callback, NOT a browser fetch/token transport or login mechanism. */
export function createIssueHostPort(scope:{profile:string,contextId:string,caseId:string,productionLogin:false},send:(message:unknown)=>Promise<unknown>):JournalPort{
 if(scope.profile!==PROFILE||scope.productionLogin!==false||!isUuid(scope.contextId)||typeof scope.caseId!=='string'||!/^[A-Za-z0-9_-]{1,64}$/.test(scope.caseId)||typeof send!=='function')throw Error('Invalid trial scope');
 const frozen={profile:PROFILE,contextId:scope.contextId,caseId:scope.caseId};
 async function call(action:'save'|'read'|'sources',value:any){
  try{
   const input=structuredClone(value);
   keys(input,action==='save'?['caseId','issueId','operationId','expectedRevision','entry']:action==='read'?['caseId','issueId']:['caseId']);
   if(input.caseId!==frozen.caseId||action!=='sources'&&!isUuid(input.issueId))throw Error('Trial scope mismatch');
   if(action==='save'){
    keys(input.entry,['kind','note','sourceIds','outcome','againstJudgment']);
    const e=input.entry;
    if(!['judgment','verification','discussion'].includes(e.kind)||typeof e.note!=='string'||!e.note.trim()||e.note.length>8000||e.note.includes('\0')||!Array.isArray(e.sourceIds)||e.sourceIds.length>20||e.sourceIds.some((v:unknown)=>typeof v!=='string'||!v||v.length>64)||new Set(e.sourceIds).size!==e.sourceIds.length)throw Error('Invalid entry');
    if(e.kind==='judgment'){if(e.outcome!==null||e.againstJudgment!==null)throw Error('Invalid judgment')}else{if(!Number.isInteger(e.againstJudgment)||e.againstJudgment<1||e.againstJudgment>input.expectedRevision)throw Error('Invalid reference');if(e.kind==='verification'?!['supports','refutes','inconclusive'].includes(e.outcome):e.outcome!==null)throw Error('Invalid outcome')}
    if(!isUuid(input.operationId)||!Number.isInteger(input.expectedRevision)||input.expectedRevision<0||input.expectedRevision>=200)throw Error('Invalid command');
   }
   const requestId=crypto.randomUUID();const message=structuredClone({...input,profile:PROFILE,contextId:frozen.contextId,requestId,action});
   if(new TextEncoder().encode(JSON.stringify(message)).length>65536)throw Error('Trial request limit');
   const reply:any=await send(message);
   if(new TextEncoder().encode(JSON.stringify(reply)).length>8*1024*1024)throw Error('Trial response limit');
   if(!reply||reply.profile!==PROFILE||reply.contextId!==frozen.contextId||reply.caseId!==frozen.caseId||reply.productionLogin!==false||reply.requestId!==requestId||reply.ok!==true)throw Error('Trial result unconfirmed');
   if(action==='sources')return {profile:'trial-issue-sources-v1',caseId:frozen.caseId,scope:'current-local-supported-candidates-only',items:parseSources(reply.body,frozen.caseId)};
   const parsed=parse(reply.body,input.caseId,input.issueId);
   if(action==='save'){
    if(parsed.revision<input.expectedRevision+1)throw Error('Missing saved entry');
    const e=parsed.events[input.expectedRevision];
    for(const key of ['kind','note','sourceIds','outcome','againstJudgment'] as const)if(JSON.stringify(e[key])!==JSON.stringify(input.entry[key]))throw Error('Wrong saved entry');
   }
   return {...parsed,events:parsed.events.map(e=>({...e,status:'working_unreviewed'}))};
  }catch{throw Error('Trial result unconfirmed')}
 }
 return {sources:caseId=>call('sources',{caseId}),save:command=>call('save',command),read:(caseId,issueId)=>call('read',{caseId,issueId})};
}
