import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import { DraftReview } from './src/agents/AgentReviewPanel'
import type { Draft } from './src/agents/model'
import type { IcTurn } from './src/interview/types'

const quote = 'SYNTHETIC current-source phrase'
const turn: IcTurn = { round: 1, question: 'Synthetic original question', answer: quote, utc: null, questionSegments: [], answerSegments: [] }
const turns: Record<string, IcTurn[]> = {
  baseline: [turn],
  same: [{ ...turn }],
  missing: [],
  changed: [{ ...turn, question: 'Synthetic changed question' }],
  ambiguousQuote: [{ ...turn, answer: quote + ' / ' + quote }],
  ambiguousRound: [turn, { ...turn }],
}
const draft: Draft = {
  caseId: 'SYN-W20-CONTEXT', draftId: 'AD-SYN-COMPONENT', agent: 'people_ops', kind: 'statement_extraction',
  targetEntityType: 'interviewStatements', targetEntityId: 'IR-SYN-ONLY',
  payload: { recordId: 'IR-SYN-ONLY', sourceDigest: 'a'.repeat(64), statements: [{ kind: 'Operation', subject: 'synthetic', summary: 'Synthetic candidate only', claim: {}, quote, round: 1, field: 'Answer' }] },
  citations: [{ recordId: 'IR-SYN-ONLY', round: 1, quote }], model: 'synthetic-no-inference', status: 'PendingReview',
}

function Fixture() {
  const [state, setState] = useState('baseline')
  const [decisions, setDecisions] = useState(0)
  return <>
    <h1>Synthetic prop scenarios (no service writes)</h1>
    {Object.keys(turns).map(key => <button key={key} onClick={() => setState(key)}>{key}</button>)}
    <output data-testid="scenario">{state}</output>
    <output data-testid="local-decisions">{decisions}</output>
    <DraftReview draft={draft} turns={turns[state]} canReview onDecide={d => {
      if (d !== 'Confirmed') throw Error('Unexpected synthetic decision')
      setDecisions(n => n + 1)
    }} />
  </>
}

createRoot(document.getElementById('root')!).render(<Fixture />)
