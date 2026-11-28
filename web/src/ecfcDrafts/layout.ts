import {validateDraft,type Draft,type Node} from './model'

/**
 * Local ECFC auto-layout (ARCHITECTURE §4.9.2), display coordinates only.
 * Never mutates or returns a modified draft: case id, nodes, edge endpoints, times,
 * text, evidence and causal content are untouched. Spacing does not encode elapsed time.
 * - Main sequence (lane 0 events): all timed -> existing rule (time, then id);
 *   otherwise topological order of event sequence edges; among simultaneously ready nodes,
 *   untimed nodes keep their input slot and timed nodes fill the remaining slots by time then id
 *   (stable, transitive); untimed tied nodes are reported as pending (time never guessed).
 * - Secondary-lane events align x with the main event they point to.
 * - Conditions sit in their own lane row nearest to the node they point to (greedy free slot).
 * - Supplied manual positions are kept as given and never overwritten.
 * - Invalid or cyclic input is not laid out and is reported, not shown as completed.
 */
export type Point={x:number;y:number}
export type Pending={nodeId:string;reason:string}
export type AutoLayout=
 |{status:'laid-out';positions:Map<string,Point>;pending:Pending[];manualKept:string[]}
 |{status:'invalid';reason:string}
export const COLUMN=290,ROW=170,ORIGIN_X=160,ORIGIN_Y=100

const byTimeThenId=(a:Node,b:Node)=>(a.timeSeconds as number)-(b.timeSeconds as number)||(a.id<b.id?-1:a.id>b.id?1:0)

export function autoLayout(draft:Draft,manual:ReadonlyMap<string,Point>=new Map()):AutoLayout{
 try{validateDraft(structuredClone(draft))}catch{return {status:'invalid',reason:'输入不合法或存在循环，未自动布局；保留原示意布局，不算完成。'}}
 const index=new Map(draft.nodes.map((n,i)=>[n.id,i])),node=new Map(draft.nodes.map(n=>[n.id,n]))
 const lanes=[...new Set(draft.nodes.map(n=>n.lane))].sort((a,b)=>a-b),row=new Map(lanes.map((l,i)=>[l,i]))
 const out=(id:string)=>draft.edges.filter(e=>e.from===id).map(e=>e.to)
 const pending:Pending[]=[],column=new Map<string,number>(),occupied=new Set<string>()
 const take=(id:string,c:number)=>{column.set(id,c);occupied.add(`${node.get(id)!.lane}:${c}`)}
 const free=(id:string,c:number)=>!occupied.has(`${node.get(id)!.lane}:${c}`)
 // Main sequence
 const main=draft.nodes.filter(n=>n.kind==='Event'&&n.lane===0)
 let order:Node[]
 if(main.every(n=>n.timeSeconds!==null))order=[...main].sort(byTimeThenId)
 else{
  const mainIds=new Set(main.map(n=>n.id)),indeg=new Map(main.map(n=>[n.id,0]))
  const seq=draft.edges.filter(e=>mainIds.has(e.from)&&mainIds.has(e.to))
  for(const e of seq)indeg.set(e.to,indeg.get(e.to)!+1)
  const ready=main.filter(n=>indeg.get(n.id)===0),flagged=new Set<string>();order=[]
  // Stable, transitive arrangement of the ready set: keep input slots; timed nodes are
  // re-sorted by time then id among the slots timed nodes occupy; untimed nodes keep their slots.
  const arrange=(set:Node[])=>{const slots=[...set].sort((a,b)=>index.get(a.id)!-index.get(b.id)!);const timedSorted=slots.filter(n=>n.timeSeconds!==null).sort(byTimeThenId);let t=0;return slots.map(n=>n.timeSeconds!==null?timedSorted[t++]!:n)}
  while(ready.length){
   ready.splice(0,ready.length,...arrange(ready))
   if(ready.length>1&&ready.some(n=>n.timeSeconds===null))for(const n of ready)if(n.timeSeconds===null&&!flagged.has(n.id)){flagged.add(n.id);pending.push({nodeId:n.id,reason:'主序列先后无法由连线或时间确定，按输入顺序暂排，待核'})}
   const n=ready.shift()!;order.push(n)
   for(const e of seq)if(e.from===n.id){indeg.set(e.to,indeg.get(e.to)!-1);if(indeg.get(e.to)===0)ready.push(node.get(e.to)!)}
  }
 }
 order.forEach((n,i)=>take(n.id,i))
 const mainColumn=(id:string)=>node.get(id)!.kind==='Event'&&node.get(id)!.lane===0?column.get(id):undefined
 // Secondary-lane events
 const secondary=draft.nodes.filter(n=>n.kind==='Event'&&n.lane!==0).map(n=>{const targets=out(n.id).map(mainColumn).filter((c):c is number=>c!==undefined);return {n,target:targets.length?Math.min(...targets):undefined}})
 secondary.sort((a,b)=>(a.target??Infinity)-(b.target??Infinity)||index.get(a.n.id)!-index.get(b.n.id)!)
 const nextFree=(id:string,from:number)=>{let c=Math.max(0,from);while(!free(id,c))c++;return c}
 const nearestFree=(id:string,c0:number)=>{for(let d=0;;d++){if(free(id,c0+d))return c0+d;if(c0-d>=0&&free(id,c0-d))return c0-d}}
 for(const {n,target} of secondary){
  if(target===undefined){take(n.id,nextFree(n.id,order.length));pending.push({nodeId:n.id,reason:'次序列事件未指向主序列事件，横向位置待核'});continue}
  const c=nextFree(n.id,target);take(n.id,c);if(c!==target)pending.push({nodeId:n.id,reason:'对齐位置已被占用，右移避让，对齐待核'})
 }
 // Conditions near the node they point to
 let rest=draft.nodes.filter(n=>n.kind==='Condition')
 for(let progress=true;rest.length&&progress;){
  progress=false
  for(const n of [...rest]){
   const targets=out(n.id)
   if(!targets.length)continue
   const anchors=targets.map(t=>column.get(t)).filter((c):c is number=>c!==undefined)
   if(anchors.length!==targets.length)continue
   take(n.id,nearestFree(n.id,Math.min(...anchors)));rest=rest.filter(r=>r!==n);progress=true
  }
 }
 for(const n of rest){take(n.id,nextFree(n.id,0));pending.push({nodeId:n.id,reason:'条件未关联到可定位节点，位置待核'})}
 const positions=new Map<string,Point>(),manualKept:string[]=[]
 for(const n of draft.nodes){const m=manual.get(n.id);if(m){positions.set(n.id,{x:m.x,y:m.y});manualKept.push(n.id)}else positions.set(n.id,{x:ORIGIN_X+column.get(n.id)!*COLUMN,y:ORIGIN_Y+row.get(n.lane)!*ROW})}
 return {status:'laid-out',positions,pending,manualKept}
}
