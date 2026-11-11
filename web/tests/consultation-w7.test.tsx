import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { renderToStaticMarkup } from 'react-dom/server'
import { access, decisionValid, eligibleParties, RequestGate, sortedRounds } from '../src/consultation/model'
import type { Round } from '../src/consultation/types'
;(globalThis as unknown as { localStorage: unknown }).localStorage = { getItem: () => null }
async function main() {
  const { RoundEditor } = await import('../src/consultation/ConsultationPanel')
  let count = 0
  function check(condition: unknown, label: string) { assert.ok(condition, label); count++ }
  const pageSource=readFileSync('src/pages/RecommendationsPage.tsx','utf8')
  check(pageSource.includes('useSyncExternalStore(onIdentityChange, recommendationsIdentity, recommendationsIdentity)'), 'whole-page identity subscription')
  check(pageSource.includes('key={`${caseId}:${requestedId}:${who}`}'), 'whole-page identity remount clears audit, board and forms')
  const fixture: Round = {
    caseId: 'fictional', roundNo: 2, draftVersion: 'synthetic', openedUtc: '2026-01-01T00:00:00Z', deadlineUtc: '2026-02-01T00:00:00Z',
    isClosed: false, daysRemaining: 0, allReplied: false, partyStatus: [],
    parties: [{partyId:'a',name:'甲（虚构）'},{partyId:'b',name:'乙（虚构）'},{partyId:'c',name:'丙（虚构）'}],
    replies:[{partyId:'a',utc:'2026-01-02T00:00:00Z',text:'已收到回复（虚构）'}],waivers:[{partyId:'b',reason:'无',utc:'2026-01-02T00:00:00Z'}],
    comments:[{commentId:'C1',round:2,partyId:'a',text:'待处理意见',decision:'Pending'}, {commentId:'C2',round:2,partyId:'a',text:'已决定意见',decision:'NotAdopted',feedback:'理由',decidedBy:'调查员（虚构）'}]
  }
  for(const level of ['ReadWrite','ReadOnly','Redacted','Deny','garbage']) {
    const a=access({matrix:{User:{report_draft:level}}},'User')
    check(a.write===(level==='ReadWrite'),`write ${level}`)
    check(a.read===['ReadWrite','ReadOnly','Redacted'].includes(level),`read ${level}`)
  }
  check(!access(null,'User').write,'null failclosed')
  check(!access({matrix:{}},'User').read,'unknown role failclosed')
  check(eligibleParties(fixture).map(x=>x.partyId).join()==='c','exclude replied+waived, allow overdue')
  check(eligibleParties({...fixture,isClosed:true}).length===0,'closed excludes reply')
  check(sortedRounds([{...fixture,roundNo:10},{...fixture,roundNo:2}])[0].roundNo===2,'numeric order')
  check(decisionValid('Adopted',''),'adopted no reason')
  for(const d of ['PartiallyAdopted','NotAdopted'] as const) {
    check(!decisionValid(d,' \n '),'trim reason');check(decisionValid(d,'reason'),'valid reason')
  }
  check(!decisionValid('Pending','reason'),'cannot decide pending')
  const gate=new RequestGate();const t=gate.begin()!;check(t!==null,'first write');check(gate.begin()===null,'doubleclick locked')
  gate.invalidate();check(!gate.current(t),'stale completion ignored');const next=gate.begin()!;gate.finish(t);check(gate.begin()===null,'old finish cannot unlock new request');gate.finish(next);check(gate.begin()!==null,'current finish unlocks')
  const render=(round:Round,writable=true,busy=false)=>renderToStaticMarkup(<RoundEditor round={round} writable={writable} busy={busy} mutate={async()=>{}} />)
  const html=render(fixture)
  check(html.includes('登记回复'),'reply action')
  check(html.includes('乙（虚构）')===false,'waived excluded')
  check(html.includes('仅登记已收到的回复'),'not external sending')
  check(html.includes('待处理意见')&&html.includes('已决定意见'),'all comments present')
  check((html.match(/保存决定/g)||[]).length===1,'only pending editable')
  check(html.includes('反馈：')&&html.includes('理由'),'decision feedback visible')
  const closed=render({...fixture,isClosed:true})
  check(!closed.includes('>登记回复</button>'),'closed no reply')
  check(closed.includes('保存决定'),'closed pending allowed')
  const ro=render(fixture,false)
  check(!ro.includes('<form'),'readonly no forms')
  check(ro.includes('待处理意见'),'readonly content retained')
  check((render(fixture,true,true).match(/disabled=""/g)||[]).length>=5,'busy disables fields')
  check(render({...fixture,replies:[],comments:[]}).includes('暂无意见条目'),'empty comments')
  check(html.includes('已收到回复'),'reply persistence display')
  console.log(`W7.1 ${count} model/static-render checks passed (not browser interaction).`)
}
main().catch(e=>{console.error(e);process.exitCode=1})
