import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import assert from 'node:assert/strict';
import {SyntheticDispute} from '@presenter';
const p=JSON.parse(process.env.CROSS_LANGUAGE_PAYLOAD!);
const before=JSON.stringify(p);
const html=renderToStaticMarkup(<SyntheticDispute input={p.input} control={p.control}/>);
assert.equal(p.projection.rows.length,8);
for(const expected of p.control.items){
 const original=p.projection.rows.find((r:any)=>r.itemId===expected.id&&r.role===expected.seat);
 assert(original);assert.equal(original.quote,expected.quote);assert.equal(original.source.sourceId,expected.sourceId);
 const start=html.indexOf('data-item="'+expected.id+'"');assert(start>=0);
 const card=html.slice(start,html.indexOf('</article>',start));
 assert(card.includes(original.quote)&&card.includes(original.source.sourceId)&&card.includes(original.role));
 assert(card.includes('第 '+original.source.line+'–'+original.source.line+' 行'));
 const other=p.control.items.find((i:any)=>i.id!==expected.id);
 assert(!card.includes(other.quote));
}
console.log('PASS actual Python projection -> two original-source SSR cards');
assert(html.includes('分歧未解决')&&html.includes('待审，未保存')&&!/<(button|input|form|a|select|textarea)\b/.test(html));
assert.equal(p.projection.consensusComputed,false);assert.equal(p.projection.factActivated,false);
console.log('PASS unresolved and no write controls');
const bad=structuredClone(p.input);bad.items[0].sourceId=bad.items[1].sourceId;
const rejected=renderToStaticMarkup(<SyntheticDispute input={bad} control={p.control}/>);
assert(rejected.includes('绑定不符'));for(const i of p.control.items)assert(!rejected.includes(i.quote));
assert.equal(JSON.stringify(p),before);
console.log('PASS source mismatch rejects whole display without mutation');
console.log('TOTAL 3 integration checks; 4 simulated seats; 8 projected rows; 2 predeclared cards; no model');
