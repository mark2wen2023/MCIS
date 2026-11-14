/** Local recovery journal: metadata only, never model/source/key text. Not an audit signature. */
import {mkdirSync,openSync,writeSync,fsyncSync,closeSync,constants} from 'node:fs';
import {join} from 'node:path';
import {randomUUID} from 'node:crypto';
const errors=new Set(['MCIS_KEY_TIMEOUT','MCIS_KEY_INVALID','MCIS_FINAL_UNVALIDATED_NO_VALIDATION','MCIS_FINAL_UNVALIDATED_FORMATTING','MCIS_FINAL_UNVALIDATED_CHANGED','MCIS_FINAL_INVALID','MCIS_RUN_FAILED','MCIS_TIMEOUT','MCIS_HOST_REJECTED','MCIS_PROBE_FAILED']);
const phases=new Set(['model_result_verified','ui_review_verified','archive_roundtrip_verified','cleanup_verified','working_review_verified','started','host_ready','model_request_started','model_request_returned','tool_returned','accepted_pending_review','not_accepted']);
export function createRunReceipt(root){
 const id=randomUUID(), dir=join(root,`pi-run-${id}`);
 mkdirSync(dir,{mode:0o700});
 const fd=openSync(join(dir,'receipt.jsonl'),constants.O_WRONLY|constants.O_CREAT|constants.O_EXCL|constants.O_NOFOLLOW,0o600);
 let sequence=0,closed=false,terminal=false;
 const append=(phase,counts={},errorCode=null)=>{
  if(closed||terminal||!phases.has(phase)||(errorCode!==null&&(!errors.has(errorCode)||phase!=='not_accepted')))throw new Error('MCIS_RECEIPT_INVALID');
  if(!counts||typeof counts!=='object'||Array.isArray(counts)||Object.keys(counts).some(k=>!['models','tools','proposals','citations'].includes(k)))throw new Error('MCIS_RECEIPT_INVALID');
  for(const [k,v] of Object.entries(counts))if(!Number.isInteger(v)||v<0||v>(k==='models'?4:k==='tools'?8:1000))throw new Error('MCIS_RECEIPT_INVALID');
  const record={version:1,runId:id,sequence:sequence+1,at:new Date().toISOString(),phase,...counts,errorCode,saved:false};
  const data=Buffer.from(JSON.stringify(record)+'\n');let offset=0;
  while(offset<data.length){const n=writeSync(fd,data,offset,data.length-offset);if(n<=0)throw new Error('MCIS_RECEIPT_IO');offset+=n;}
  fsyncSync(fd);sequence++;terminal=['accepted_pending_review','not_accepted'].includes(phase);
 };
 append('started');
 return {id,path:join(dir,'receipt.jsonl'),append,close(){if(!closed){closed=true;closeSync(fd);}}};
}
