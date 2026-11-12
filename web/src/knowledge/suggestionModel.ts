import type {Content,Kind} from './model'
export const PROFILE='MCIS-KNOWLEDGE-SUGGESTION-1'
export type SuggestionInput={kind:Kind;source:Content['source']}
export interface Suggestion {profile:typeof PROFILE;provider:'template-stub-v1';modelUsed:false;persisted:false;reviewRequired:true;inputDigest:string;content:Content;warnings:string[]}
const obj=(v:unknown):v is Record<string,unknown>=>!!v&&typeof v==='object'&&!Array.isArray(v)
export function parseSuggestion(v:unknown,input:SuggestionInput):Suggestion {
 if(!obj(v)||v.profile!==PROFILE||v.provider!=='template-stub-v1'||v.modelUsed!==false||v.persisted!==false||v.reviewRequired!==true||typeof v.inputDigest!=='string'||! /^[a-f0-9]{64}$/.test(v.inputDigest)||!obj(v.content)||!Array.isArray(v.warnings)||!v.warnings.length||!v.warnings.every(w=>typeof w==='string'&&!!w.trim()))throw Error('模板预览响应异常')
 const c=v.content,s=c.source
 if(c.kind!==input.kind||!obj(s)||Object.keys(s).length!==Object.keys(input.source).length||Object.entries(input.source).some(([k,val])=>s[k]!==val)||c.body!==input.source.excerpt||!['title','summary','applicability'].every(k=>typeof c[k]==='string'&&!!(c[k] as string).trim())||!Array.isArray(c.tags)||c.tags.length!==1||c.tags[0]!== (input.source.type==='Synthetic'?'合成待审':'公开待审'))throw Error('模板预览来源绑定不一致')
 if(Array.from(c.title as string).length>160||Array.from(c.summary as string).length>600)throw Error('模板预览超出长度')
 return v as unknown as Suggestion
}
