import {canonicalInput,parsePreview,validateInput,type Input,type Model,type Preview,type Source} from './model'

// Set only after the existing async hash + parsePreview check succeeds.
export type ReviewedPreview = Preview & {reviewedInput:string;reviewedIdentity:string}
export interface PathWitness {side:'prevention'|'mitigation';endpointId:string;nodes:{id:string;label:string}[]}
const order=(a:string,b:string)=>a<b?-1:a>b?1:0

/** Bounded witnesses in a core-validated graph, NOT another structure validator.
 * Remove barriers, then follow only relevant existing directed edges. Each
 * endpoint gets one shortest, ID-ordered witness; protected alternatives do not
 * erase it. No interpolation, inference of real controls or effectiveness.
 */
function witnesses(model:Model):PathWitness[]{
 const nodes=new Map([{...model.topEvent,kind:'TopEvent'},...model.nodes].map(n=>[n.id,n]))
 if(nodes.size!==model.nodes.length+1)throw Error('ambiguous node identity')
 const adjacency=new Map<string,string[]>()
 for(const edge of model.edges){
  const from=nodes.get(edge.fromId),to=nodes.get(edge.toId)
  if(!from||!to)throw Error('unknown endpoint')
  if((from.kind==='Threat'&&(to.kind==='Threat'||to.kind==='TopEvent'))||(from.kind==='TopEvent'&&to.kind==='Consequence')){
   adjacency.set(from.id,[...(adjacency.get(from.id)||[]),to.id])
  }
 }
 for(const [id,next] of adjacency)adjacency.set(id,[...new Set(next)].sort(order))
 const path=(start:string,end:string):string[]|null=>{
  const queue:string[][]=[[start]],seen=new Set([start])
  for(let cursor=0;cursor<queue.length;cursor++){
   const current=queue[cursor]!,last=current[current.length-1]!
   if(last===end)return current
   for(const next of adjacency.get(last)||[])if(!seen.has(next)){seen.add(next);queue.push([...current,next])}
  }
  return null
 }
 const out:PathWitness[]=[]
 for(const side of ['prevention','mitigation'] as const){
  const endpoints=model.nodes.filter(n=>n.kind===(side==='prevention'?'Threat':'Consequence')).sort((a,b)=>order(a.id,b.id))
  for(const endpoint of endpoints){
   const ids=side==='prevention'?path(endpoint.id,model.topEvent.id):path(model.topEvent.id,endpoint.id)
   if(ids)out.push({side,endpointId:endpoint.id,nodes:ids.map(id=>({id,label:nodes.get(id)!.label}))})
  }
 }
 return out
}

/** null means unreviewed/stale/invalid, not "no unprotected paths". */
export function currentPathWitnesses(input:Input,result:ReviewedPreview|null,caseId:string,who:string,sources:Source[],stale=false):PathWitness[]|null{
 try{
  if(!result||stale||result.reviewedIdentity!==who||!result.result.structureValid)return null
  validateInput(input)
  const selected=sources.filter(s=>input.sourceEvidenceIds.includes(s.evidenceId))
  if(result.reviewedInput!==canonicalInput(caseId,input.model,selected))return null
  parsePreview(result,caseId,who,input,result.inputSha256,selected)
  return witnesses(input.model)
 }catch{return null}
}
