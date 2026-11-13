import {strict as assert} from 'node:assert'
import {sample} from '../src/knowledge/model'
import {previewSessionKey} from '../src/knowledge/previewSession'

const input={kind:sample.kind,source:structuredClone(sample.source)}
let who=JSON.stringify(['Investigator','investigator-a'])
Object.defineProperty(globalThis,'localStorage',{value:{getItem:(k:string)=>k==='mcis.role'?'Investigator':'investigator-a',setItem:()=>{}},configurable:true})
async function main(){
const {SuggestionPreview}=await import('../src/knowledge/SuggestionPreview')
const {setIdentity}=await import('../src/api')
const key=previewSessionKey(input,who)
let n=0
function check(f:()=>void){f();n++}
check(()=>assert.equal(previewSessionKey(structuredClone(input),who),key))
check(()=>assert.equal(previewSessionKey({...input,source:Object.fromEntries(Object.entries(input.source).reverse()) as typeof input.source},who),key))
for(const field of Object.keys(input.source))check(()=>assert.notEqual(previewSessionKey({...input,source:{...input.source,[field]:'changed'}},who),key))
check(()=>assert.notEqual(previewSessionKey({...input,kind:'Case'},who),key))
check(()=>assert.notEqual(previewSessionKey(input,'investigator-b'),key))
const apply=()=>{}
const a=SuggestionPreview({input,onApply:apply})
check(()=>assert.equal(a.key,key))
check(()=>assert.equal(a.props.onApply,apply))
check(()=>assert.equal(a.props.input,input))
check(()=>assert.notEqual(SuggestionPreview({input:{...input,source:{...input.source,locator:'new'}},onApply:apply}).key,a.key))
setIdentity('Investigator','investigator-b')
check(()=>assert.notEqual(SuggestionPreview({input,onApply:apply}).key,a.key))
console.log(n+' session identity checks passed; not browser interaction tests')

}
void main()
