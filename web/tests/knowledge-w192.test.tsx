import {strict as assert} from 'node:assert'
import {parseSuggestion,PROFILE} from '../src/knowledge/suggestionModel'
import {sample} from '../src/knowledge/model'
const input={kind:sample.kind,source:sample.source}
const result={profile:PROFILE,provider:'template-stub-v1',modelUsed:false,persisted:false,reviewRequired:true,inputDigest:'a'.repeat(64),content:{...sample,body:sample.source.excerpt,tags:['合成待审']},warnings:['仅模板，不是模型。']}
assert.equal(parseSuggestion(result,input).persisted,false)
for(const patch of [{profile:'wrong'},{provider:'llm'},{modelUsed:true},{persisted:true},{reviewRequired:false},{inputDigest:'bad'},{warnings:[]},{content:{...result.content,body:'invented'}},{content:{...result.content,source:{...sample.source,locator:'other'}}},{content:{...result.content,tags:['judgment']}}])assert.throws(()=>parseSuggestion({...result,...patch},input))
console.log('W19.2 preview format/binding/no-model/no-save guards passed')
