import {strictJson} from './strictJson'
import {exact,preview,type Attempt} from './model'
const prefix='mcis.report-output.unknown.v1:'
function key(who:string,caseId:string,reportId:string){return prefix+encodeURIComponent(JSON.stringify([who,caseId,reportId]))}
function parse(raw:string,who:string,caseId:string,reportId:string):Attempt{if(raw.length>16384)throw Error('待核记录超限');const v:any=strictJson(new TextEncoder().encode(raw));exact(v,['who','preview','format','lang']);if(v.who!==who||!['pdf','docx'].includes(v.format)||!['zh','en','bilingual'].includes(v.lang))throw Error('待核记录身份或选项不符');preview(v.preview,caseId,reportId);return v}
export function readLock(who:string,caseId:string,reportId:string):Attempt|null{const raw=sessionStorage.getItem(key(who,caseId,reportId));return raw===null?null:parse(raw,who,caseId,reportId)}
export function saveLock(a:Attempt){const k=key(a.who,a.preview.caseId,a.preview.reportId),raw=JSON.stringify(a);parse(raw,a.who,a.preview.caseId,a.preview.reportId);sessionStorage.setItem(k,raw);if(sessionStorage.getItem(k)!==raw)throw Error('不能可靠保留待核元数据，未发送生成请求')}
export function clearLock(a:Attempt){const k=key(a.who,a.preview.caseId,a.preview.reportId);const stored=sessionStorage.getItem(k);if(stored!==null){const v=parse(stored,a.who,a.preview.caseId,a.preview.reportId);if(JSON.stringify(v)!==JSON.stringify(a))throw Error('待核请求已变化');sessionStorage.removeItem(k);if(sessionStorage.getItem(k)!==null)throw Error('待核元数据未能清除')}}
/** Explicit user abandonment only; never called as automatic error recovery. */
export function discardScope(who:string,caseId:string,reportId:string){const k=key(who,caseId,reportId);sessionStorage.removeItem(k);if(sessionStorage.getItem(k)!==null)throw Error('本地待核元数据未能清除')}
export function checkStorage(who:string,caseId:string,reportId:string){const current=readLock(who,caseId,reportId),probe=key(who,caseId,reportId)+':probe';try{sessionStorage.setItem(probe,'storage-check');if(sessionStorage.getItem(probe)!=='storage-check')throw Error('存储检查失败')}finally{sessionStorage.removeItem(probe)}if(sessionStorage.getItem(probe)!==null)throw Error('存储检查失败');return current}
