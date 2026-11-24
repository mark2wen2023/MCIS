import React from 'react'
import {createRoot} from 'react-dom/client'
import {KnowledgePage} from '../../web/src/pages/KnowledgePage'
import {sample} from '../../web/src/knowledge/model'
import fixture from '../../research/w19_case_ranking/version_binding/fixture.json'
// Existing visible synthetic v1/v2 text only. This is a transport fixture, not a database.
;(window as any).__reviewFixture = [fixture.cards[1],fixture.cards[0]].map((c,i)=>({
 cardId:'KC-'+'a'.repeat(32),status:'Candidate',createdUtc:'2030-06-04T00:00:00Z',
 content:{...structuredClone(sample),title:c.content.title,body:c.content.body,
 source:{...structuredClone(sample.source),title:c.content.title,locator:c.content.source.locator,excerpt:c.content.source.excerpt}},
 version:i+1
}))
createRoot(document.getElementById('root')!).render(<KnowledgePage/>)
