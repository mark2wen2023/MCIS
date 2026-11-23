import {createHash} from 'node:crypto';
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

function currentControl(current:any){
 const c=structuredClone(current);
 for(const s of c.sources){
  // Same canonical bytes as Python: UTF-8(join(lines, LF) + final LF), no normalization.
  s.sha256=createHash('sha256').update(Buffer.from(s.lines.join('\n')+'\n','utf8')).digest('hex');
 }
 return c;
}
const rebuilt=currentControl(p.control);
for(const source of rebuilt.sources)assert.equal(source.sha256,p.control.sources.find((s:any)=>s.id===source.id).sha256);
for(const item of p.input.items){
 const row=p.projection.rows.find((r:any)=>r.itemId===item.id&&r.role===item.seat);
 assert.equal(item.sourceSha256,row.source.sha256);
 assert(html.includes(item.sourceSha256));
}
assert.equal(renderToStaticMarkup(<SyntheticDispute input={p.input} control={rebuilt}/>),html);
console.log('PASS full Python UTF-8 digest survives receipt and matches independent Node calculation');
const current=structuredClone(p.control);
current.sources[0].lines[0]+='（相邻行已修订）';
const changed=currentControl(current);
assert.notEqual(changed.sources[0].sha256,p.input.items[0].sourceSha256);
assert.equal(changed.caseId,p.input.caseId);assert.equal(changed.revision,p.input.revision);
assert.equal(changed.sources[0].id,p.input.items[0].sourceId);
assert.equal(changed.sources[0].lines[1],p.input.items[0].quote);
const stale=renderToStaticMarkup(<SyntheticDispute input={p.input} control={changed}/>);
assert(stale.includes('绑定不符'));
for(const i of p.control.items)assert(!stale.includes(i.quote));
assert(!/<(button|input|form|a|select|textarea)\b/.test(stale));
assert.equal(JSON.stringify(p),before);
console.log('PASS same quote and locator but changed neighboring source line rejects old version');

console.log('TOTAL 5 integration checks; full-source version retained; no product binding');
