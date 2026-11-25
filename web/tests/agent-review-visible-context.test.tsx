import assert from 'node:assert/strict'
import { Window } from 'happy-dom'
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import type { Draft } from '../src/agents/model'
import type { IcTurn } from '../src/interview/types'

async function main() {
  const window = new Window()
  Object.assign(globalThis, {
    window, document: window.document, localStorage: window.localStorage,
    Event: window.Event, IS_REACT_ACT_ENVIRONMENT: true,
  })
  const { DraftReview } = await import('../src/agents/AgentReviewPanel')
  const container = document.createElement('div')
  document.body.append(container)
  const root = createRoot(container)
  const turns: IcTurn[] = [{ round: 1, question: 'Synthetic question', answer: 'SYNTHETIC source quote', utc: null, questionSegments: [], answerSegments: [] }]
  const draft: Draft = {
    caseId: 'SYN-W20-CONTEXT', draftId: 'AD-001', agent: 'people_ops', kind: 'statement_extraction', targetEntityType: 'interviewStatements', targetEntityId: 'IR-90',
    payload: { recordId: 'IR-90', sourceDigest: 'a'.repeat(64), statements: [{ kind: 'Operation', subject: 'synthetic', summary: 'Synthetic candidate only', claim: {}, quote: 'source quote', round: 1, field: 'Answer' }] },
    citations: [{ recordId: 'IR-90', round: 1, quote: 'source quote' }], model: 'synthetic-no-inference', status: 'PendingReview',
  }
  let changes = 0
  const render = (input: IcTurn[]) => act(() => root.render(<DraftReview draft={draft} turns={input} canReview onDecide={decision => { assert.equal(decision, 'Confirmed'); changes++ }} />))
  const check = () => container.querySelector<HTMLInputElement>('input[type=checkbox]')!
  const confirm = () => [...container.querySelectorAll('button')].find(button => button.textContent === '确认以上陈述并写回')!
  try {
    await render(turns)
    assert(confirm().disabled)
    await act(() => check().click())
    assert(!confirm().disabled)
    await render(turns.map(it => ({...it})))
    assert(!confirm().disabled, 'Same visible context keeps acknowledgment')
    await render([])
    assert(check().disabled)
    assert(confirm().disabled, 'Missing context must disable confirmation even after previously checking')
    await act(() => confirm().click())
    assert.equal(changes, 0)
    await render(turns)
    assert(!check().checked && confirm().disabled, 'Restored source requires fresh review')
    await act(() => check().click())
    await render(turns.map(it => ({...it, question: 'Changed question, identical answer'})))
    assert(!check().checked && confirm().disabled, 'Changed question invalidates semantic acknowledgment')
    await render(turns.map(it => ({...it, answer: 'source quote and source quote'})))
    assert(check().disabled && confirm().disabled, 'Ambiguous quote cannot confirm')
    await render([...turns, ...turns])
    assert(check().disabled && confirm().disabled, 'Ambiguous round cannot confirm')
    await render(turns)
    await act(() => check().click())
    await act(() => confirm().click())
    assert.equal(changes, 1)
    console.log('W20 current-context mounted React: 7 phases PASS')
  } finally {
    await act(() => root.unmount())
    await window.happyDOM.close()
  }
}
void main().then(()=>process.exit(0),e=>{console.error(e);process.exit(1)})
