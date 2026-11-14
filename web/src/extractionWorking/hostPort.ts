export const PROFILE='mcis-extraction-review-persistent-trial-v1';
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
export type Scope={profile:typeof PROFILE,contextId:string,caseId:string,recordId:string,productionLogin:false};
export type Decision={index:number,decision:'adopted_working'|'rejected'|'needs_verification',note:string};
export type Command=({action:'list'}|{action:'read',proposalId:string}|{action:'generate',operationId:string}|{action:'review',operationId:string,proposalId:string,expectedRevision:number,decisions:Decision[]})&{requestId:string};
export type Item={proposalId:string,recordId:string,revision:number};
export type ProviderMode='fixture'|'local'|'remote-deepseek';
export type ReviewOrigin='user_submission_unverified'|'scripted_test'|'legacy_unspecified';
export type PiTrace={op:'model_start'|'model_request'|'model_end'|'tool'|'final',tool?:string,outcome?:string};
export type Review={revision:number,authorRef:string,recordedUtc:string,decisions:Decision[],reviewOrigin:ReviewOrigin};
export type View={status:'working_unreviewed',proposalId:string,recordId:string,revision:number,fixture:boolean,providerMode:ProviderMode,configuredModel:string|null,completionMode?:'exact'|'validated-reference',execution?:{runId:string,trace:PiTrace[]},fingerprint:string,bindingDigest:string,sourceScope:string,proposals:{summary:string,claim:Record<string,unknown>,quote:string,span:{round:number,field:string,start:number,length:number}}[],reviews:Review[]};
export type Result=View|{status:'not_connected'}|{status:'list',items:Item[]};
export type WorkingPort={scope:Scope,execute(command:Command):Promise<Result>};
function obj(v:any){if(!v||typeof v!=='object'||Array.isArray(v))throw Error();return v}
function exact(v:any,ks:string[]){obj(v);if(Object.keys(v).sort().join('|')!==ks.sort().join('|'))throw Error()}
function str(v:any,max:number){if(typeof v!=='string'||!v.trim()||v.length>max||v.includes('\0'))throw Error();return v}
function id(v:any){if(typeof v!=='string'||!uuid.test(v))throw Error();return v}
function decisions(v:any):Decision[]{if(!Array.isArray(v)||!v.length||v.length>20)throw Error();const seen=new Set();return v.map(d=>{exact(d,['index','decision','note']);if(!Number.isInteger(d.index)||d.index<1||d.index>20||seen.has(d.index)||!['adopted_working','rejected','needs_verification'].includes(d.decision))throw Error();seen.add(d.index);return {index:d.index,decision:d.decision,note:str(d.note,1000)}})}
function receipt(v:any,review=false){obj(v);for(const k of ['bindingDigest','promptDigest','outputDigest','runChecksum',...(review?['reviewChecksum']:[])])if(typeof v[k]!=='string'||! /^[0-9a-f]{64}$/.test(v[k]))throw Error();if(v.persistentAudit!==false||v.signature!==false)throw Error();return v}
function claim(v:any){obj(v);if(Object.keys(v).some(k=>!['valueType','time','scalar','unit','position','occurred'].includes(k))||!['EventTime','Scalar','Position','Occurrence'].includes(v.valueType))throw Error();for(const k of ['time','unit'])if(v[k]!=null)str(v[k],200);if(v.scalar!=null&&(typeof v.scalar!=='number'||!Number.isFinite(v.scalar)))throw Error();if(v.occurred!=null&&typeof v.occurred!=='boolean')throw Error();if(v.position!=null){obj(v.position);if(typeof v.position.lonDeg!=='number'||typeof v.position.latDeg!=='number'||Math.abs(v.position.lonDeg)>180||Math.abs(v.position.latDeg)>90)throw Error();for(const [k,n] of Object.entries(v.position))if(!['latDeg','lonDeg','heightM'].includes(k)||typeof n!=='number'||!Number.isFinite(n))throw Error()};return structuredClone(v)}

function hash(v:any){if(typeof v!=='string'||! /^[0-9a-f]{64}$/.test(v))throw Error();return v as string}
function piExecution(b:any){
 const x=b.execution;exact(x,['profile','runId','completionMode','trace','outputDigest','traceMeaning','runtimeIdentityVerified']);
 if(x.profile!=='pi-working-trial-v1'||x.completionMode!==b.completionMode||!['exact','validated-reference'].includes(x.completionMode)||x.traceMeaning!=='trusted_host_protocol_metadata_not_signed_audit'||x.runtimeIdentityVerified!==false)throw Error();
 id(x.runId);hash(x.outputDigest);
 if(!Array.isArray(x.trace)||!x.trace.length||x.trace.length>32)throw Error();
 let state='idle',models=0,tools=0,read=false,validated=false;
 const trace:PiTrace[]=x.trace.map((e:any,i:number)=>{
  if(e.op==='tool'){
   exact(e,['op','tool','outcome']);if(state!=='ended'||!['read_transcript_excerpt','find_transcript_passages','validate_extraction_proposal'].includes(e.tool))throw Error();
   if(e.tool==='validate_extraction_proposal'){if(!['validated','invalid'].includes(e.outcome))throw Error();validated=e.outcome==='validated'}else{if(e.outcome!=='read')throw Error();read=true}tools++;
   return {op:'tool',tool:e.tool,outcome:e.outcome};
  }
  exact(e,['op']);
  if(e.op==='model_start'){if(!['idle','ended'].includes(state))throw Error();state='started';models++}
  else if(e.op==='model_request'){if(state!=='started')throw Error();state='requested'}
  else if(e.op==='model_end'){if(state!=='requested')throw Error();state='ended'}
  else if(e.op==='final'){if(i!==x.trace.length-1||state!=='ended'||x.trace[i-1]?.op!=='model_end'||!read||!validated)throw Error();state='final'}
  else throw Error();return {op:e.op};
 });
 if(state!=='final'||models!==b.modelCalls||tools!==b.toolCalls||!Number.isInteger(models)||models<1||models>4||tools<1||tools>8)throw Error();
 return {runId:x.runId as string,trace};
}
export function frozenProposal(b:any,recordId:string){
 obj(b);const pi=b.providerMode==='remote-deepseek';let providerMode:ProviderMode,configuredModel:string|null,completionMode:'exact'|'validated-reference'|undefined,execution:{runId:string,trace:PiTrace[]}|undefined,sourceScope:string,bindingDigest:string,fingerprint:string;
 if(pi){
  exact(b,['status','proposals','citations','saved','factVerified','persistentAudit','bindingDigest','citationMeaning','sourceScope','modelCalls','toolCalls','completionMode','providerMode','configuredModel','modelIdentityVerified','humanApprovalVerified','inferencePerformed','fixture','execution']);
  if(b.fixture!==false||b.inferencePerformed!==true||b.factVerified!==false||b.persistentAudit!==false||b.modelIdentityVerified!==false||b.humanApprovalVerified!==false||!Number.isInteger(b.modelCalls)||!Number.isInteger(b.toolCalls))throw Error();
  providerMode='remote-deepseek';configuredModel=str(b.configuredModel,200);if(/[\x00-\x1f\x7f]/.test(configuredModel))throw Error();execution=piExecution(b);completionMode=b.completionMode;bindingDigest=hash(b.bindingDigest);sourceScope=b.sourceScope;
  fingerprint=JSON.stringify([bindingDigest,b.providerMode,configuredModel,b.completionMode,b.execution,b.modelCalls,b.toolCalls]);
 }else{
  if(Object.hasOwn(b,'providerMode')||Object.hasOwn(b,'execution')||Object.hasOwn(b,'completionMode'))throw Error();
  if(typeof b.fixture!=='boolean'||b.inferencePerformed!==!b.fixture||b.receipt?.providerMode!==(b.fixture?'fixture':'local')||b.receipt?.modelIdentityVerified!==false)throw Error();
  const rc=receipt(b.receipt);providerMode=b.fixture?'fixture':'local';configuredModel=b.fixture?null:(rc.configuredModel==null?null:str(rc.configuredModel,200));bindingDigest=rc.bindingDigest;sourceScope=rc.sourceScope;
  fingerprint=JSON.stringify([rc.bindingDigest,rc.promptDigest,rc.outputDigest,rc.runChecksum,providerMode,configuredModel]);
 }
 if(b.status!=='PendingReview'||b.saved!==false||b.citationMeaning!=='exact_quote_match_only_not_fact_verification'||!['registered_original_bytes','interview_document_only'].includes(sourceScope)||!Array.isArray(b.proposals)||!b.proposals.length||b.proposals.length>20)throw Error();
 if(!Array.isArray(b.citations)||b.citations.length!==b.proposals.length)throw Error();b.proposals.forEach((p:any,i:number)=>{const ci=obj(b.citations[i]);if(pi)exact(ci,['recordId','round','quote']);if(ci.recordId!==recordId||ci.round!==p.span?.round||ci.quote!==p.quote)throw Error()});
 const quoteKeys=new Set<string>();
 const proposals=b.proposals.map((p:any)=>{obj(p);const sp=obj(p.span);if(pi){exact(p,['kind','subject','summary','claim','quote','recordId','statementId','span','reviewStatus','revision','extractedBy']);exact(sp,['round','field','start','length']);if(!['Time','Position','Operation','Observation'].includes(p.kind))throw Error();str(p.subject,200);if(Object.hasOwn(p.claim,'unit')&&typeof p.claim.unit!=='string')throw Error();const quoteKey=JSON.stringify([sp.round,sp.field,p.quote]);if(quoteKeys.has(quoteKey))throw Error();quoteKeys.add(quoteKey);if(p.statementId!=='pending'||p.revision!==1||p.extractedBy!=='Agent')throw Error()};if(p.recordId!==recordId||p.reviewStatus!=='Draft'||!Number.isInteger(sp.round)||sp.round<1||!['Question','Answer'].includes(sp.field)||!Number.isInteger(sp.start)||sp.start<0||!Number.isInteger(sp.length)||sp.length<1||sp.length!==p.quote?.length)throw Error();return {summary:str(p.summary,8000),claim:claim(p.claim),quote:str(p.quote,24000),span:{round:sp.round,field:sp.field,start:sp.start,length:sp.length}}});
 return {fingerprint,bindingDigest,fixture:b.fixture as boolean,providerMode,configuredModel,completionMode,execution,sourceScope,proposals};
}
function revision(v:any){if(!Number.isInteger(v)||v<0||v>100)throw Error();return v as number}
function parseView(b:any,s:Scope):View{
 exact(b,['proposalId','recordId','revision','status','saved','persistence','factActivated','proposal','reviews',...(Object.hasOwn(b,'replayed')?['replayed']:[])]);if(b.recordId!==s.recordId||b.status!=='working_unreviewed'||b.saved!==true||b.persistence!=='working_record_only'||b.factActivated!==false)throw Error();
 exact(b.proposal,['result','bindingDigest','storedUtc']);const rev=revision(b.revision),f=frozenProposal(obj(b.proposal).result,s.recordId);if(b.proposal.bindingDigest!==f.bindingDigest)throw Error();
 if(!Array.isArray(b.reviews)||b.reviews.length!==rev)throw Error();
 const reviews=b.reviews.map((r:any,i:number)=>{exact(r,['revision','authorRef','recordedUtc','decisions','reviewedAsWorkingOnly','factVerified',...(Object.hasOwn(r,'reviewOrigin')?['reviewOrigin']:[])]);const reviewOrigin:ReviewOrigin=Object.hasOwn(r,'reviewOrigin')?r.reviewOrigin:'legacy_unspecified';if(!['user_submission_unverified','scripted_test','legacy_unspecified'].includes(reviewOrigin)||(Object.hasOwn(r,'reviewOrigin')&&reviewOrigin==='legacy_unspecified'))throw Error();if(r.revision!==i+1||r.reviewedAsWorkingOnly!==true||r.factVerified!==false)throw Error();const ds=decisions(r.decisions).sort((a,b)=>a.index-b.index);if(ds.length!==f.proposals.length||ds.some((d,j)=>d.index!==j+1))throw Error();return {reviewOrigin,revision:i+1,authorRef:id(r.authorRef),recordedUtc:str(r.recordedUtc,64),decisions:ds}});
 return {status:'working_unreviewed',proposalId:id(b.proposalId),recordId:s.recordId,revision:rev,...f,reviews};
}
export function createExtractionWorkingPort(scope:Scope,send:(value:unknown)=>Promise<unknown>,expectedProvider?:ProviderMode):WorkingPort{
 if(expectedProvider!==undefined&&!['fixture','local','remote-deepseek'].includes(expectedProvider))throw Error('Invalid provider expectation');const s=structuredClone(scope);if(s.profile!==PROFILE||s.productionLogin!==false||typeof send!=='function')throw Error('Invalid trial scope');id(s.contextId);str(s.caseId,64);str(s.recordId,128);
 const frozen:Scope=Object.freeze({profile:PROFILE,contextId:s.contextId,caseId:s.caseId,recordId:s.recordId,productionLogin:false});const known=new Map<string,View>();
 return {scope:frozen,async execute(command){try{
  const c=structuredClone(command);const fields={list:['action','requestId'],read:['action','requestId','proposalId'],generate:['action','requestId','operationId'],review:['action','requestId','operationId','proposalId','expectedRevision','decisions']};if(!Object.hasOwn(fields,c.action))throw Error();exact(c,fields[c.action]);id(c.requestId);
  if(c.action==='read'||c.action==='review')id(c.proposalId);if(c.action==='generate'||c.action==='review')id(c.operationId);if(c.action==='review'){if(revision(c.expectedRevision)>=100)throw Error();c.decisions=decisions(c.decisions)}
  const {productionLogin,...binding}=frozen;const m={...binding,...c};if(new TextEncoder().encode(JSON.stringify(m)).length>60000)throw Error();const r:any=await send(structuredClone(m));if(new TextEncoder().encode(JSON.stringify(r)).length>4*1024*1024)throw Error();obj(r);for(const k of ['profile','contextId','caseId','recordId','productionLogin'] as const)if(r[k]!==frozen[k])throw Error();if(r.requestId!==c.requestId||r.ok!==true)throw Error();exact(r,['profile','contextId','caseId','recordId','productionLogin','requestId','ok','body']);const b=obj(r.body);
  if(c.action==='list'){exact(b,['caseId','persistence','factActivated','items']);if(b.caseId!==s.caseId||b.persistence!=='working_record_only'||b.factActivated!==false||!Array.isArray(b.items)||b.items.length>50)throw Error();const seen=new Set();const items=b.items.map((x:any)=>{exact(x,['proposalId','recordId','revision','status']);id(x.proposalId);if(seen.has(x.proposalId)||x.recordId!==s.recordId||x.status!=='working_unreviewed')throw Error();seen.add(x.proposalId);return {proposalId:x.proposalId,recordId:s.recordId,revision:revision(x.revision)}});return {status:'list',items}}
  if(c.action==='generate'&&b.status==='not_connected'){if(b.inferencePerformed!==false||!Array.isArray(b.proposals)||b.proposals.length)throw Error();return {status:'not_connected'}}
  const view=parseView(b,frozen);if(expectedProvider&&view.providerMode!==expectedProvider)throw Error();if((c.action==='read'||c.action==='review')&&view.proposalId!==c.proposalId)throw Error();
  const old=known.get(view.proposalId);if(old&&(view.revision<old.revision||JSON.stringify(view.proposals)!==JSON.stringify(old.proposals)||view.fingerprint!==old.fingerprint||view.fixture!==old.fixture||view.sourceScope!==old.sourceScope||JSON.stringify(view.reviews.slice(0,old.revision))!==JSON.stringify(old.reviews)))throw Error();
  if(c.action==='review'&&(view.revision<c.expectedRevision+1||JSON.stringify(view.reviews[c.expectedRevision]?.decisions)!==JSON.stringify([...c.decisions].sort((a,b)=>a.index-b.index))))throw Error();
  if(known.size>=50&&!known.has(view.proposalId))throw Error();known.set(view.proposalId,structuredClone(view));return view;
 }catch{throw Error('工作复核结果未确认')}}};
}
