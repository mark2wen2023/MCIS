import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
const {Window}=await import(process.env.MCIS_HAPPY_DOM_PATH!);const window=new Window({url:'http://localhost/#/knowledge'});
for(const key of ['window','document','navigator','HTMLElement','HTMLInputElement','HTMLAnchorElement','Element','Event','MouseEvent'])Object.defineProperty(globalThis,key,{value:(window as any)[key]??window,writable:true,configurable:true});
Object.defineProperty(globalThis,'localStorage',{value:{getItem:(k:string)=>k==='mcis.role'?'Public':null,setItem:()=>{throw Error('no storage writes')}},configurable:true});
Object.defineProperty(globalThis,'sessionStorage',{value:{getItem:()=>null,setItem:()=>{throw Error('no storage writes')}},configurable:true});
(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true;
const React=require('react'),{act}=React,{createRoot}=require('react-dom/client');
const {KnowledgePage,KnowledgeCard}=require('../../web/src/pages/KnowledgePage');
const {sample}=require('../../web/src/knowledge/model');
const fixture=require('../../research/w19_case_ranking/version_binding/fixture.json');
function canonical(x:any):string{return Array.isArray(x)?'['+x.map(canonical).join(',')+']':x&&typeof x==='object'?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}':JSON.stringify(x)}
const cards=[fixture.cards[1],fixture.cards[0]].map((f:any)=>{const content={...structuredClone(sample),title:f.content.title,body:f.content.body,source:{...structuredClone(sample.source),title:f.content.title,locator:f.content.source.locator,excerpt:f.content.source.excerpt}};return {cardId:'KC-'+'a'.repeat(32),status:'Published',content,contentDigest:createHash('sha256').update(canonical(content)).digest('hex'),createdUtc:'2030-06-04T00:00:00Z'}});
const ctx={status:'Published',kind:'',q:'告警',tag:''};const container=document.createElement('div');document.body.append(container);const root=createRoot(container);let count=0;
function check(x:any){assert(x);count++}
function reason(){return container.querySelector('details[aria-label="本次返回原因"]') as HTMLDetailsElement|null}
function body(){return container.querySelector('article>details') as HTMLDetailsElement|null}
async function renderCard(card:any,context:any=ctx){await act(async()=>root.render(<KnowledgeCard card={card} searchContext={context} canReview={false} onReview={()=>{throw Error('no reviews')}}/>))}
let requests:{url:string,resolve:(x:any)=>void}[]=[];let total=0;
(globalThis as any).fetch=(url:any,init:any)=>{assert.equal(init.method,'GET');assert(String(url).startsWith('/api/v1/knowledge/cards?'));total++;return new Promise(resolve=>requests.push({url:String(url),resolve}))};
async function settle(items:any[],ok=true){const req=requests.shift();assert(req);await act(async()=>{req.resolve({ok,status:ok?200:403,json:async()=>ok?{items,total:items.length,limit:20,offset:0}:{code:'FORBIDDEN',message:'synthetic denial'}});await new Promise(r=>setTimeout(r,0))})}
async function click(label:string){await act(async()=>{[...container.querySelectorAll('button')].find(b=>b.textContent===label)!.dispatchEvent(new window.MouseEvent('click',{bubbles:true}));await new Promise(r=>setTimeout(r,0))})}
async function query(text:string){await act(async()=>{const el=container.querySelector('form.w19-search input')!;Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value')!.set!.call(el,text);el.dispatchEvent(new window.Event('input',{bubbles:true}))})}
try{
 await renderCard(cards[0]);reason()!.open=true;body()!.open=true;
 await renderCard(cards[1]);check(!reason()!.open);check(!body()!.open);check(!container.textContent!.includes(cards[0].content.source.excerpt));
 reason()!.open=true;await renderCard({...cards[1],cardId:'KC-'+'b'.repeat(32)});check(!reason()!.open);
 reason()!.open=true;await renderCard({...cards[1],cardId:'KC-'+'b'.repeat(32)},{...ctx,q:'不同条件'});check(!reason()!.open);check(reason()!.textContent!.includes('不同条件'));
 await renderCard({...cards[1],status:'Withdrawn'});check(!reason());check(container.textContent!.includes('已撤回'));
 await renderCard({...cards[1],status:'Withdrawn'},{...ctx,status:'Withdrawn'});check(!reason()!.open);check(reason()!.textContent!.includes('已撤回'));
 check(total===0); // Expanding/replacing already loaded cards causes no source request.
 await act(async()=>root.render(<KnowledgePage/>));await settle([cards[0]]);check(container.querySelectorAll('article.w19-card').length===1);
 reason()!.open=true;body()!.open=true;await query('未提交条件');check(container.querySelectorAll('article.w19-card').length===1);check(!reason()!.textContent!.includes('未提交条件'));check(total===1);
 await act(async()=>container.querySelector('form.w19-search')!.dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true})));check(!reason());check(!body());await settle([cards[1]]);check(reason()!.textContent!.includes('未提交条件'));check(!body()!.open);check(!container.textContent!.includes(cards[0].content.source.excerpt));
 await click('重新读取');check(!reason());check(!container.querySelector('article.w19-card'));await settle([],false);check(!reason());check(!body());check(!!container.querySelector('[role="alert"]'));
 await click('重新读取');await settle([cards[1]]);check(!!reason());check(!reason()!.open);
 // Published search after withdrawal returns no accessible card; then reopening/re-read stays empty.
 await click('重新读取');await settle([]);check(!container.querySelector('article.w19-card'));check(!reason());await click('重新读取');await settle([]);check(!body());
 await click('重新读取');await settle([{...cards[1],status:'Withdrawn'}]);check(!container.querySelector('article.w19-card'));check(!!container.querySelector('[role="alert"]'));
 // A stale transport reply after page unmount must not restore an old card.
 await click('重新读取');await act(async()=>root.render(<p>已离开资料库</p>));await settle([cards[0]]);check(!container.querySelector('article'));check(!reason());
 check(requests.length===0);console.log('PASS '+count+' actual KnowledgeCard/KnowledgePage React+API-parser assertions; synthetic GET transport only, no backend withdrawal performed, no browser/model/storage/review writes.');
}finally{await act(async()=>root.unmount());await window.happyDOM.abort();window.close()}
process.exit(0);
