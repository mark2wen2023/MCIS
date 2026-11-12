import {useCallback,useEffect,useRef,useState} from 'react'
import {ApiError,getOperator,getRole} from '../api'
export const contentIdentity=()=>JSON.stringify([getRole(),getOperator()])
export const CONTENT_ACCESS_NOTICE='当前版本仅支持满足完整原文权限的笔录访问，尚未提供可靠的字段级脱敏笔录视图。默认策略下 Investigator 受限，这是有意的安全边界。请联系授权管理员按单位规则处理；本页不会自动切换角色或放宽策略。本地自报角色不是真实身份认证，生产身份认证尚未完成。'
export function contentError(error:unknown){return error instanceof ApiError&&error.status===403?'当前身份无权访问笔录原文。'+CONTENT_ACCESS_NOTICE:error instanceof Error?error.message:'读取失败，请重新读取。'}
export async function contentRequest<T>(path:string,who:string,body?:unknown,signal?:AbortSignal):Promise<T>{
 const check=()=>{if(who!==contentIdentity()||signal?.aborted)throw new DOMException('读取上下文已变化','AbortError')};check()
 const [role,operator]=JSON.parse(who)
 const response=await fetch('/api/v1'+path,{method:body===undefined?'GET':'POST',cache:'no-store',signal,headers:{'X-MCIS-Role':role,'X-MCIS-Operator':encodeURIComponent(operator),...(body===undefined?{}:{'Content-Type':'application/json'})},body:body===undefined?undefined:JSON.stringify(body)})
 const data=await response.json().catch(error=>{if(!response.ok)return {};throw error});check()
 if(!response.ok)throw new ApiError(response.status,data.code||'HTTP_'+response.status,data.message||response.statusText,data.detail)
 return data as T
}
/** Local hook: hide old content immediately on refresh, without changing shared useLoad. */
export function useContentLoad<T>(loader:(signal:AbortSignal)=>Promise<T>,onDenied:()=>void){
 const [state,setState]=useState<{data:T|null;error:string|null}>({data:null,error:null}),[tick,setTick]=useState(0)
 const generation=useRef(0)
 const reload=useCallback(()=>{generation.current++;setState({data:null,error:null});setTick(n=>n+1)},[])
 useEffect(()=>{let live=true;const mine=++generation.current;const controller=new AbortController()
 loader(controller.signal).then(data=>{if(live&&mine===generation.current)setState({data,error:null})}).catch(error=>{if(!live||mine!==generation.current)return;setState({data:null,error:contentError(error)});if(error instanceof ApiError&&error.status===403)onDenied()})
 return()=>{live=false;controller.abort()}
 },[tick])
 return {...state,reload}
}
