import type {StoredUnreviewedResult} from './result'
export type Phase='disconnected'|'ready'|'saving'|'outcome-unknown'|'saved'|'reading'|'read'|'denied'|'stale'
export type State={phase:Phase;epoch:number;operationId?:string;runId?:string;result?:StoredUnreviewedResult}
export const initial:State={phase:'disconnected',epoch:0}
export type Action={type:'invalidate'}|{type:'ready'}|{type:'save';operationId:string}|{type:'unknown';epoch:number}|{type:'saved';epoch:number;runId:string}|{type:'read'}|{type:'result';epoch:number;result:StoredUnreviewedResult}|{type:'error';epoch:number;kind:'denied'|'stale'|'retry'}
const id=(s:string)=>/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(s)
/** Pure rehearsal reducer. No network, token, role headers or storage. */
export function transition(s:State,a:Action):State{
  if(a.type==='invalidate')return {phase:'disconnected',epoch:s.epoch+1}
  if('epoch' in a&&a.epoch!==s.epoch)return s
  switch(a.type){
    case 'ready':return s.phase==='disconnected'?{phase:'ready',epoch:s.epoch}:s
    case 'save':return (s.phase==='ready'||s.phase==='outcome-unknown')&&id(a.operationId)&&(!s.operationId||s.operationId===a.operationId)?{...s,epoch:s.epoch+1,phase:'saving',operationId:a.operationId}:s
    case 'unknown':return s.phase==='saving'?{...s,phase:'outcome-unknown'}:s
    case 'saved':return s.phase==='saving'&&id(a.runId)?{...s,phase:'saved',runId:a.runId}:s
    case 'read':return (s.phase==='saved'||s.phase==='read')?{...s,epoch:s.epoch+1,phase:'reading',result:undefined}:s
    case 'result':return s.phase==='reading'&&a.result.runId===s.runId?{...s,phase:'read',result:a.result}:s
    case 'error':return s.phase==='reading'?{...s,phase:a.kind==='retry'?'saved':a.kind,result:undefined}:s.phase==='saving'?{...s,phase:a.kind==='retry'?'outcome-unknown':a.kind,result:undefined}:s
  }
}
