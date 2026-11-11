import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { parseCases } from '../src/cases/model'
import { navigationForCase } from '../src/caseContext'
let n=0
function check(v:unknown,m:string){if(!v)throw Error(m);n++}
async function run(){
Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null,setItem:()=>{}}})
const {LobbyContent}=await import('../src/pages/LobbyPage')
const item={caseId:'A / &?#',title:'<script>安全</script>',isFictionalDemo:false}
check(parseCases([item])[0].caseId===item.caseId,'identity retained')
for(const bad of [null,{},[null],[{}],[{...item,isFictionalDemo:'false'}],[{...item,caseId:''}],[{...item,title:''}],[item,item],[{...item,placeName:12}]]){
let failed=false;try{parseCases(bad)}catch{failed=true};check(failed,'reject malformed list')
}
const render=(state:any)=>renderToStaticMarkup(<MemoryRouter><LobbyContent state={state} retry={()=>{}}/></MemoryRouter>)
check(render({status:'loading'}).includes('正在加载'),'loading')
check(render({status:'error'}).includes('role="alert"'),'error accessible')
check(render({status:'ready',cases:[]}).includes('暂无案件'),'empty')
const html=render({status:'ready',cases:[item]})
check(html.includes('/evidence?case=A%20%2F%20%26%3F%23'),'encoded entry')
check(!html.includes('<script>'),'title escaped')
check(html.includes('非虚构案件')&&!html.includes('真实案例（公开报告）'),'no invented public provenance')
check(render({status:'ready',cases:[{...item,isFictionalDemo:true}]}).includes('虚构演示'),'fictional marked')
for(const path of ['evidence','recs','report','analysis','colreg'])check(navigationForCase(path,item.caseId,'demo').includes(encodeURIComponent(item.caseId)),path+' context retained')
console.log(`W8.1 ${n} assertions passed`)
}
run().catch(e=>{console.error(e);process.exitCode=1})
