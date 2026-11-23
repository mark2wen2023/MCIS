export type Source = {id:string; caseId:string; revision:string; sha256:string; lines:readonly string[]};
export type Item = {id:string; seat:string; claim:string; sourceId:string; sourceSha256:string; start:number; end:number; quote:string};
export type SyntheticDisputeInput = {kind:'developer_synthetic_dispute'; caseId:string; revision:string; question:string; items:readonly Item[]};
export type SyntheticDisputeControl = {caseId:string; revision:string; question:string; sources:readonly Source[]; items:readonly Item[]};
const itemKeys=['id','seat','claim','sourceId','start','end','quote','sourceSha256'] as const;
function shape(v:unknown,keys:readonly string[]): asserts v is Record<string,unknown> {
 if(!v||typeof v!=='object'||Object.getPrototypeOf(v)!==Object.prototype)throw Error();
 const own=Reflect.ownKeys(v);
 if(own.length!==keys.length||own.some(k=>typeof k!=='string'||!keys.includes(k)))throw Error();
 for(const key of keys){const d=Object.getOwnPropertyDescriptor(v,key);if(!d||!('value' in d))throw Error()}
}
function list(v:unknown): asserts v is unknown[] {
 if(!Array.isArray(v)||Object.getPrototypeOf(v)!==Array.prototype)throw Error();
 if(Reflect.ownKeys(v).length!==v.length+1)throw Error();
 for(let i=0;i<v.length;i++){const d=Object.getOwnPropertyDescriptor(v,String(i));if(!d||!('value' in d))throw Error()}
}
function text(v:unknown): asserts v is string {if(typeof v!=='string'||!v.trim())throw Error()}
function digest(v:unknown){if(typeof v!=='string'||! /^[a-f0-9]{64}$/.test(v))throw Error()}
function item(v:Item){shape(v,itemKeys);digest(v.sourceSha256);for(const k of ['id','seat','claim','sourceId','quote'] as const)text(v[k]);if(!Number.isInteger(v.start)||!Number.isInteger(v.end)||v.start<1||v.end<v.start)throw Error()}
// Control is separately frozen by the developer host, not supplied by a model.
// Host computes complete-source SHA-256; this view compares it with the held row.
// Control is trusted ONLY in this isolated fixture, never a client authority protocol.
export function SyntheticDispute({input,control}:{input?:SyntheticDisputeInput;control?:SyntheticDisputeControl}) {
 if(input===undefined && control===undefined)return null;
 let rows:Item[];
 try {
  shape(input,['kind','caseId','revision','question','items']);shape(control,['caseId','revision','question','sources','items']);
  if(input.kind!=='developer_synthetic_dispute')throw Error();
  for(const k of ['caseId','revision','question'] as const){text(input[k]);text(control[k]);if(input[k]!==control[k])throw Error()}
  list(input.items);list(control.items);list(control.sources);
  if(input.items.length!==2||control.items.length!==2||control.sources.length!==2)throw Error();
  for(const s of control.sources){
   shape(s,['id','caseId','revision','lines','sha256']);digest(s.sha256);text(s.id);text(s.caseId);text(s.revision);list(s.lines);
   if(s.caseId!==control.caseId||s.revision!==control.revision||!s.lines.length||s.lines.some(l=>typeof l!=='string'))throw Error();
  }
  control.items.forEach(item);input.items.forEach(item);
  if(new Set(control.sources.map(s=>s.id)).size!==2||new Set(control.items.map(i=>i.id)).size!==2||new Set(control.items.map(i=>i.seat)).size!==2||new Set(control.items.map(i=>i.sourceId)).size!==2)throw Error();
  rows=input.items.map((i,n)=>{
   const expected=control.items[n],s=control.sources.find(s=>s.id===i.sourceId);
   if(itemKeys.some(k=>i[k]!==expected[k])||!s||i.sourceSha256!==s.sha256)throw Error();
   if(i.end>s.lines.length||s.lines.slice(i.start-1,i.end).join('\n')!==i.quote)throw Error();
   return {id:i.id,seat:i.seat,claim:i.claim,sourceId:i.sourceId,sourceSha256:i.sourceSha256,start:i.start,end:i.end,quote:i.quote};
  });
 }catch{return <section className="w203" role="alert">合成待审输入绑定不符，未展示任何主张或原文。</section>}
 return <section className="w203" aria-label="合成争议只读待审">
 <h2>合成争议 · 待人工复核</h2><p>仅开发验证；非真实四席会审、非生产授权。分歧未解决，不进行表决，不确认事实。</p>
 <p>案件 {input!.caseId} · 稿件 {input!.revision}</p><h3>{input!.question}</h3>
 <div className="w203-queue">{rows.map(r=><article key={r.id} data-item={r.id}>
 <h4>{r.seat} · {r.claim}</h4><blockquote>{r.quote}</blockquote>
 <p>来源 {r.sourceId} · 第 {r.start}–{r.end} 行 · 原文逐字对应已核对（非真实性认证）</p>
 <p>合成来源版本 SHA-256：{r.sourceSha256}（测试宿主提供，非认证）</p>
 <p>证据语义支持未评定；因果未评定；待审，未保存。</p></article>)}</div></section>
}
