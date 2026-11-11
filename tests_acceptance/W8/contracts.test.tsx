import { readFileSync } from 'node:fs'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { parseCases } from '../../web/src/cases/model'
import { navigationForCase,caseForLocation } from '../../web/src/caseContext'
let n=0; function check(x:unknown,m:string){if(!x)throw Error(m);n++}
async function main(){
Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null,setItem:()=>{}}})
const {LobbyContent}=await import('../../web/src/pages/LobbyPage')
const cases=[{caseId:'甲/乙?x=1#frag',title:'<img src=x onerror=alert(1)>',isFictionalDemo:false},{caseId:'demo',title:'虚构',isFictionalDemo:true}]
const html=renderToStaticMarkup(<MemoryRouter><LobbyContent state={{status:'ready',cases:parseCases(cases)}} retry={()=>{}}/></MemoryRouter>)
check(!html.includes('<img'),'untrusted title escaped')
check(html.includes(encodeURIComponent(cases[0].caseId)),'case delimiter encoded')
check(html.includes('非虚构案件'),'nonfiction label does not invent provenance')
check(html.includes('虚构演示'),'fictional label')
for(const p of ['evidence','analysis','report','colreg','recs']) {
const nav=navigationForCase(p,cases[0].caseId,'demo');check(caseForLocation('/'+p,nav.split('?')[1],'demo')===cases[0].caseId,p+' roundtrip')
}
check(parseCases([]).length===0,'empty accepted')
for(const bad of [[...cases,cases[0]],{cases},[{caseId:'x',title:'x',isFictionalDemo:0}],null]){let failed=false;try{parseCases(bad)}catch{failed=true};check(failed,'invalid rejected')}
const error=renderToStaticMarkup(<MemoryRouter><LobbyContent state={{status:'error'}} retry={()=>{}}/></MemoryRouter>);check(error.includes('role="alert"')&&!error.includes('进入案件 →'),'error no stale entry')
check(readFileSync('web/src/Layout.tsx','utf8').includes('Outlet key={`${caseId}:${role}`}'),'keyed case and role boundary')
console.log(`Independent W8 contract/SSR: ${n} passed; not browser coverage`)
}main().catch(e=>{console.error(e);process.exitCode=1})
