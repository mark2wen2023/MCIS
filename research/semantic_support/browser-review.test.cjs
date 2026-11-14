// Executes the generated page's actual script with a minimal DOM/download adapter.
// Protocol/UI-state tests, not browser-engine or filesystem-save certification.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync(process.argv[2], 'utf8');
const template = JSON.parse(html.match(/<script id="worksheet-template" type="application\/json">(.*?)<\/script>/s)[1]);
const script = html.match(/<script>(.*?)<\/script>/s)[1];
let clicks = 0, removed = 0, failure = false;
const blobs = [], timers = [], revoked = [];
const button = {addEventListener: (name, fn) => button[name] = fn};
const status = {};
const fields = template.items.map(() => {
 const boxes = Array.from({length: 3}, () => ({checked: false}));
 const area = {value: '', focus() { this.focused = true; }};
 return {boxes, area, querySelectorAll: () => boxes, querySelector: () => area};
});
const document = {
 getElementById: id => ({'worksheet-template': {textContent: JSON.stringify(template)}, 'download-notes': button, 'download-status': status}[id]),
 querySelectorAll: () => fields,
 addEventListener: (name, fn) => document[name] = fn,
 body: {appendChild() {}},
 createElement: () => ({click() {if (failure) throw Error('blocked'); clicks++;}, remove() {removed++;}})
};
vm.runInNewContext(script, {document, Blob, URL: {createObjectURL(blob) {blobs.push(blob); return `blob:${blobs.length}`;}, revokeObjectURL(url) {revoked.push(url);}}, setTimeout: fn => timers.push(fn)});
(async () => {
 assert.equal(clicks, 0);
 button.click();
 assert.deepEqual(JSON.parse(await blobs.at(-1).text()), template);
 fields[0].boxes[0].checked = true;
 for (const invalid of ['', ' \n', '\u0085\u001c']) {
  fields[0].area.value = invalid; button.click(); assert.equal(clicks, 1); assert.match(status.textContent, /填写原因/);
 }
 for (const invalid of ['x'.repeat(4001), '\ud800', '\udfff']) {
  fields[0].area.value = invalid; button.click(); assert.equal(clicks, 1); assert.match(status.textContent, /Unicode/);
 }
 fields[0].area.value = '😀'.repeat(4000); button.click(); assert.equal(clicks, 2);
 fields[0].area.value = '\ufeff'; button.click(); assert.equal(clicks, 3); // Python considers BOM nonblank.
 fields[0].area.value = '</textarea><script>alert(1)</script>\n约 3.4  \n海里';
 document.input(); assert.match(status.textContent, /尚未导出/);
 button.click(); const first = await blobs.at(-1).text();
 button.click(); assert.equal(await blobs.at(-1).text(), first); assert.equal(clicks, 5);
 const saved = JSON.parse(first);
 assert.equal(saved.items[0].note, fields[0].area.value);
 assert.equal(saved.items[0].timeAssociationNeedsCheck, true);
 assert.equal(saved.status, 'unverified_research_notes_not_case_facts');
 assert.equal(template.items[0].note, '');
 failure = true; button.click(); assert.equal(clicks, 5); assert.match(status.textContent, /无法发起下载/);
 failure = false; button.click(); assert.equal(clicks, 6); assert.match(status.textContent, /请在浏览器下载列表确认/);
 assert.equal(removed, 7);
 timers.forEach(fn => fn()); assert.equal(revoked.length, blobs.length);
 fs.writeFileSync(process.argv[3], first);
 console.log('browser script checks passed: validation, Unicode, exact notes, repeat, failure/retry, cleanup; no browser engine');
})().catch(e => {console.error(e); process.exitCode=1;});
