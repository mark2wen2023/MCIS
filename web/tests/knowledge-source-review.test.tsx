import {strict as assert} from 'node:assert'
import {renderToStaticMarkup} from 'react-dom/server'
import {sample} from '../src/knowledge/model'
import {PROFILE,type Suggestion} from '../src/knowledge/suggestionModel'
import {reviewedSuggestion} from '../src/knowledge/sourceReview'
import {SuggestionSourceReview} from '../src/knowledge/SuggestionSourceReview'

const input={kind:sample.kind,source:structuredClone(sample.source)}
const result:Suggestion={profile:PROFILE,provider:'template-stub-v1',modelUsed:false,persisted:false,reviewRequired:true,inputDigest:'a'.repeat(64),content:{...structuredClone(sample),body:sample.source.excerpt,tags:['合成待审']},warnings:['仅模板，不是模型。']}
let checks=0
function check(f:()=>void){f();checks++}
check(()=>assert.equal(reviewedSuggestion(result,input,null),null))
check(()=>assert.equal(reviewedSuggestion(result,input,'b'.repeat(64)),null))
check(()=>assert.deepEqual(reviewedSuggestion(result,input,result.inputDigest),result.content))
check(()=>{const content=reviewedSuggestion(result,input,result.inputDigest)!;content.source.locator='changed';assert.equal(result.content.source.locator,sample.source.locator)})
check(()=>assert.equal(reviewedSuggestion(result,{...input,source:{...input.source,locator:'new'}},result.inputDigest),null))
check(()=>assert.equal(reviewedSuggestion({...result,modelUsed:true} as unknown as Suggestion,input,result.inputDigest),null))
check(()=>assert.equal(reviewedSuggestion({...result,content:{...result.content,body:'different'}},input,result.inputDigest),null))
const html=renderToStaticMarkup(<SuggestionSourceReview source={input.source} checked={false} onChange={()=>{}}/>)
check(()=>assert.match(html,/Synthetic/))
check(()=>assert.match(html,/未核实/))
check(()=>assert.match(html,/不代表批准发布/))
check(()=>assert.doesNotMatch(html,/checked=""/))
check(()=>assert.match(renderToStaticMarkup(<SuggestionSourceReview source={input.source} checked={true} onChange={()=>{}}/>),/checked=""/))
const pub={...input.source,type:'Public' as const,url:'https://example.test/report',title:'<img src=x onerror=alert(1)>'}
const publicHTML=renderToStaticMarkup(<SuggestionSourceReview source={pub} checked={false} onChange={()=>{}}/>)
check(()=>assert.match(publicHTML,/Public/))
check(()=>assert.match(publicHTML,/系统未核实公开状态或使用权/))
check(()=>assert.doesNotMatch(publicHTML,/<img|href=|<script/))
check(()=>assert.match(publicHTML,/&lt;img/))
console.log(`${checks} source review checks passed (local gate and server rendering, not browser interaction)`)
