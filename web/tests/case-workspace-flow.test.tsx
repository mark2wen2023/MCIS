import assert from 'node:assert/strict'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { CaseWorkspaceFlow } from '../src/caseFlow/CaseWorkspaceFlow'
import { caseFlow } from '../src/caseFlow/model'
const id='SYN /?&=船', search='?case='+encodeURIComponent(id)
const render=(path:string,query=search)=>renderToStaticMarkup(<MemoryRouter initialEntries={[path+query]}><CaseWorkspaceFlow pathname={path} search={query}/></MemoryRouter>)
const flow=caseFlow('/interview',search)!
assert.equal(flow.caseId,id);assert.equal(flow.stage,2)
assert.equal(flow.steps[0].href,'/case?case='+encodeURIComponent(id))
assert.equal(flow.steps[3].href,'/colreg?case='+encodeURIComponent(id))
assert.equal(flow.steps[6].href,null)
for(const [page,stage] of [['case',0],['ships',1],['env',1],['track',1],['evidence',1],['interview',2],['analysis',3],['colreg',3],['whatif',3],['hf',3],['systemic',3],['report',4],['recs',5]] as const){
 assert.equal(caseFlow('/'+page,search)!.stage,stage)
 const html=render('/'+page)
 assert.equal((html.match(/aria-current="step"/g)||[]).length,1)
 assert.ok(html.includes('仅导航 · 完成状态未评估'))
 assert.ok(!html.includes('已完成')&&!html.includes('100%'))
 assert.ok(html.includes('可随时返回前面阶段补证'))
}
const html=render('/interview')
assert.ok(html.includes('aria-label="案件流程导航"')&&html.includes('建议前往：'))
assert.ok(html.includes('/colreg?case='+encodeURIComponent(id)))
assert.ok(html.includes('/case?case='+encodeURIComponent(id)))
assert.ok(!html.includes('/knowledge')&&html.includes('沉淀（后续）'))
for(const path of ['/lobby','/knowledge','/access','/agents','/sim','/ecfc','/unknown']){
 assert.equal(caseFlow(path,search),null)
 const cleared=render(path)
 assert.ok(!cleared.includes('当前案号')&&!cleared.includes(encodeURIComponent(id)))
 assert.ok(cleared.includes('href="/lobby"'))
}
for(const q of ['', '?case=', '?case=%20','?case=A&case=B','?report=R-SYN']){
 assert.equal(caseFlow('/report',q),null)
 assert.ok(!render('/report',q).includes('当前案号'))
}
const other=render('/report','?case=SYN-B&report=R-SYN')
assert.ok(other.includes('SYN-B')&&!other.includes(encodeURIComponent(id)))
assert.equal(caseFlow('/report','?case=SYN-B&report=R-SYN')!.steps[0].href,'/case?case=SYN-B')
assert.ok(render('/recs').includes('不自动入库'))
assert.equal(render('/interview'),html)
assert.ok(!render('/report','').includes('SYN-B'))
console.log('PASS case flow: route mapping, explicit context/encoding, back/next, global/no-case clearing and actual component SSR')
