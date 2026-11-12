import {sha,uuid,type SaveBody} from './model'
export interface Lock{requestId:string;expectedDigest:string|null}
export const pending=new Map<string,SaveBody>()
export const lockKey=(caseId:string,who:string)=>'mcis.ecfc.pending.v1:'+encodeURIComponent(JSON.stringify([caseId,who]))
export function readLock(key:string):Lock|null{const raw=sessionStorage.getItem(key);if(raw===null)return null;const x=JSON.parse(raw);if(!x||typeof x!=='object'||Object.keys(x).length!==2||!uuid(x.requestId)||!(x.expectedDigest===null||sha(x.expectedDigest)))throw Error('待核标记无效');return x}
export function placeLock(key:string,body:SaveBody){if(readLock(key))throw Error('已有待核请求');const value={requestId:body.requestId,expectedDigest:body.expectedDigest};sessionStorage.setItem(key,JSON.stringify(value));if(JSON.stringify(readLock(key))!==JSON.stringify(value))throw Error('无法验证待核标记');pending.set(key,body)}
export function clearLock(key:string,requestId:string){const saved=readLock(key);if(!saved||saved.requestId!==requestId)throw Error('待核请求已变化');sessionStorage.removeItem(key);if(readLock(key)!==null)throw Error('待核标记未清除');pending.delete(key)}
