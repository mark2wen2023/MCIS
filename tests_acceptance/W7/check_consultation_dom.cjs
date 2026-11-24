'use strict';

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const { createRequire, Module } = require('node:module');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const [sourceArg, webModulesArg, happyDomArg] = process.argv.slice(2);
assert.ok([sourceArg, webModulesArg, happyDomArg].every(p => p && path.isAbsolute(p)),
  'usage: node check_consultation_dom.cjs ABS_SOURCE_ROOT ABS_WEB_NODE_MODULES ABS_HAPPY_DOM_INDEX');
const source = fs.realpathSync(sourceArg);
const webModules = fs.realpathSync(webModulesArg);
const happyDom = fs.realpathSync(happyDomArg);
const manifest = fs.readFileSync(path.join(__dirname, 'consultation_dom_sources.sha1'), 'utf8')
  .trim().split('\n').map(line => line.split(' '));
const expected = new Map(manifest.map(([hash, name]) => [name, hash]));
assert.equal(expected.size, 8);
function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
    const child = path.join(dir, entry.name);
    assert.ok(entry.isFile() || entry.isDirectory(), 'plain snapshot entries only');
    return entry.isDirectory() ? walk(child) : [path.relative(source, child)];
  });
}
assert.deepEqual(walk(source).sort(), [...expected.keys()].sort());
for (const [name, sha] of expected) {
  const bytes = fs.readFileSync(path.join(source, name));
  const gitBlob = crypto.createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex');
  assert.equal(gitBlob, sha, name);
}

const load = createRequire(path.join(webModules, '../package.json'));
const { build } = load('esbuild');
const caseA = 'SYN-W7-DOM-A';
const caseB = 'SYN-W7-DOM-B';
const policy = { matrix: { LeadInvestigator: { report_draft: 'ReadWrite' } } };
const endpoint = (caseId, name) => `/api/v1/cases/${caseId}/${name}`;
const requests = [];
const unexpected = [];
let changes = 0;
const stub = (url, init) => {
  const permitted = [caseA, caseB].some(id => ['access-policy', 'consultation/rounds'].some(n => url === endpoint(id, n)));
  if (!permitted || init?.method !== 'GET' || init.body !== undefined ||
      init.headers?.['X-MCIS-Role'] !== 'LeadInvestigator' ||
      init.headers?.['X-MCIS-Operator'] !== 'Synthetic%20DOM') {
    unexpected.push({url, method: init?.method});
    throw new Error('Only whitelisted synthetic GET calls are allowed; no network fallback');
  }
  const request = {url, method: init.method, done: false};
  requests.push(request);
  return new Promise((resolve, reject) => {
    request.deliver = data => { request.done = true; resolve({ok: true, text: async () => JSON.stringify(data)}); };
    request.fail = () => { request.done = true; reject(new Error('STALE-SYNTHETIC-FAILURE')); };
  });
};
function round(caseId, roundNo, draftVersion) {
  return {
    caseId, roundNo, draftVersion, openedUtc: '2026-02-01T08:00:00Z', deadlineUtc: '2026-03-18T08:00:00Z',
    isAgreedDeadline: true, isClosed: true, daysRemaining: 0, allReplied: true, partyStatus: [],
    parties: [{partyId: 'F1', name: '虚构方'}], replies: [], waivers: [],
    comments: [{commentId: 'SYN-C-' + roundNo, partyId: 'F1', decision: 'Pending', text: draftVersion + '-comment'}],
  };
}

(async () => {
  const { Window } = await import(pathToFileURL(happyDom));
  const window = new Window({
    url: 'https://mcis-synthetic.invalid/',
    settings: { enableJavaScriptEvaluation: false, disableJavaScriptFileLoading: true, enableCSSFileLoading: false,
      enableImageFileLoading: false, enableIframePageLoading: false },
  });
  Object.assign(globalThis, {
    window, document: window.document, localStorage: window.localStorage, HTMLElement: window.HTMLElement,
    fetch: stub, IS_REACT_ACT_ENVIRONMENT: true,
  });
  window.fetch = stub;
  window.localStorage.setItem('mcis.role', 'LeadInvestigator');
  window.localStorage.setItem('mcis.operator', 'Synthetic DOM');
  const { createElement, act } = load('react');
  const { createRoot } = load('react-dom/client');
  const flags = await build({
    entryPoints: [path.join(source, 'web/src/consultation/ConsultationPanel.tsx')],
    bundle: true, platform: 'node', format: 'cjs', jsx: 'automatic',
    loader: { '.css': 'empty' }, external: ['react', 'react/jsx-runtime'], write: false,
  });
  const loaded = new Module('consultation-dom.cjs', module);
  loaded.filename = path.join(source, 'consultation-dom.cjs');
  loaded.paths = [webModules];
  loaded._compile(flags.outputFiles[0].text, loaded.filename);
  const { ConsultationPanel } = loaded.exports;
  const mount = document.createElement('main');
  document.body.appendChild(mount);
  const root = createRoot(mount);
  let mounted = true;
  const renderCase = id => act(async () => root.render(createElement(ConsultationPanel, {
    caseId: id,
    renderMatrix: rounds => createElement('div', {id: 'matrix'}, rounds.map(r => r.draftVersion).join('|')),
    onChanged: () => { changes++; },
  })));
  const one = (selector, parent = mount) => {
    const nodes = parent.querySelectorAll(selector);
    assert.equal(nodes.length, 1, selector);
    return nodes[0];
  };
  const button = caption => {
    const buttons = [...mount.querySelectorAll('button')].filter(b => b.textContent.trim() === caption);
    assert.equal(buttons.length, 1, caption);
    return buttons[0];
  };
  const click = btn => act(async () => btn.click());
  const nth = (url, i) => {
    const request = requests.filter(r => r.url === url)[i];
    assert.ok(request && !request.done, url + '#' + i);
    return request;
  };
  const resolve = (request, payload) => act(async () => { request.deliver(payload); });
  const select = (element, value) => act(async () => {
    element.value = value;
    element.dispatchEvent(new window.Event('change', { bubbles: true }));
  });
  const type = (element, value) => act(async () => {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(element, value);
    element.dispatchEvent(new window.Event('input', { bubbles: true }));
  });
  const roundSelect = () => one('select[aria-label="选择轮次"]');
  const decision = () => one('.w7-editor select');
  const agreed = () => one('.w7-lifecycle input[type="checkbox"]');
  const duration = () => one('input[inputmode="numeric"]');
  const matrix = () => one('#matrix').textContent;

  try {
    // One React root, A -> B -> A. Retain both old round GET requests.
    await renderCase(caseA);
    await resolve(nth(endpoint(caseA, 'access-policy'), 0), policy);
    const oldA = nth(endpoint(caseA, 'consultation/rounds'), 0);
    await renderCase(caseB);
    await resolve(nth(endpoint(caseB, 'access-policy'), 0), policy);
    const oldB = nth(endpoint(caseB, 'consultation/rounds'), 0);
    await renderCase(caseA);
    await resolve(nth(endpoint(caseA, 'access-policy'), 1), policy);
    await resolve(nth(endpoint(caseA, 'consultation/rounds'), 1),
      [round(caseA, 1, 'A-old-round'), round(caseA, 2, 'A-current')]);
    assert.equal(roundSelect().value, '2');
    assert.match(mount.textContent, /A-current-comment/);

    // Both a real checkbox/text change in RoundLifecycle and a decision selection in RoundEditor.
    await click(agreed());
    assert.equal(agreed().checked, true);
    await type(duration(), '45');
    assert.equal(duration().value, '45');
    await click(agreed());
    assert.equal(mount.querySelector('input[inputmode="numeric"]'), null);
    await click(agreed());
    assert.equal(duration().value, '45', 'React captured the input event, rather than merely changing a DOM property');
    assert.equal(button('保存决定').disabled, false);
    await select(decision(), 'NotAdopted');
    assert.equal(decision().value, 'NotAdopted');
    assert.equal(button('保存决定').disabled, true, 'React captured the decision change and requires a reason');
    await select(roundSelect(), '1');
    assert.equal(roundSelect().value, '1');
    assert.match(mount.textContent, /A-old-round-comment/);
    assert.doesNotMatch(mount.textContent, /A-current-comment/);
    assert.equal(agreed().checked, false);
    assert.equal(mount.querySelector('input[inputmode="numeric"]'), null);
    assert.equal(decision().value, 'Adopted');
    assert.equal(button('保存决定').disabled, false);
    await click(agreed());
    assert.equal(duration().value, '', 'switch remounted the form, not merely hidden');
    await type(duration(), '77');
    await select(decision(), 'PartiallyAdopted');

    // Refresh invalidates stale forms while reading; latest response has only a new round.
    await click(button('重新读取'));
    assert.equal(button('重新读取').disabled, true, 'no overlapping same-session manual reload button');
    assert.match(mount.textContent, /正在读取轮次与权限/);
    assert.equal(mount.querySelector('select'), null);
    assert.equal(mount.querySelector('#matrix'), null);
    await resolve(nth(endpoint(caseA, 'access-policy'), 2), policy);
    const aRefreshed = nth(endpoint(caseA, 'consultation/rounds'), 2);
    await resolve(aRefreshed, [round(caseA, 3, 'A-new-after-refresh')]);
    assert.equal(roundSelect().value, '3', 'former round 1 disappeared; new round selected');
    assert.equal(agreed().checked, false);
    assert.equal(decision().value, 'Adopted');
    assert.doesNotMatch(mount.textContent, /A-old-round-comment|A-current-comment/);
    await click(agreed());
    assert.equal(duration().value, '', 'refresh discarded 77, not just the opt-in box');
    await type(duration(), '61');
    await select(decision(), 'NotAdopted');

    // Old same-case GET completes last; a stale other-case GET fails after the new form is already used.
    await resolve(oldA, [round(caseA, 9, 'STALE-A-MUST-NOT-SHOW')]);
    await act(async () => { oldB.fail(); });
    assert.equal(matrix(), 'A-new-after-refresh');
    assert.equal(roundSelect().value, '3');
    assert.match(mount.textContent, /A-new-after-refresh-comment/);
    assert.doesNotMatch(mount.textContent, /STALE-A|STALE-SYNTHETIC-FAILURE/);
    assert.equal(mount.querySelector('[role="alert"]'), null);
    assert.equal(agreed().checked, true);
    assert.equal(duration().value, '61');
    assert.equal(decision().value, 'NotAdopted');
    assert.equal(button('保存决定').disabled, true);
    await click(agreed());
    await click(agreed());
    assert.equal(duration().value, '61', 'new duration remains in React state after both late completions');

    assert.equal(requests.length, 8);
    assert.ok(requests.every(r => r.method === 'GET' && r.done));
    assert.deepEqual(unexpected, [], 'no mutation or off-fixture request');
    assert.equal(changes, 0, 'no product mutation reconciliation callback');
    assert.equal(mount.querySelector('a'), null, 'no external link in this scoped panel');
    await act(async () => root.unmount());
    mounted = false;
    assert.equal(mount.textContent, '');
    console.log(JSON.stringify({syntheticGet: requests.length, attemptedMutationOrExternal: unexpected.length,
      changedCallbacks: changes, sameRootCaseABA: true, selectedRoundAfterRefresh: 3, staleSuccessAndFailureIgnored: true,
      roundSwitchAndRefreshClearDrafts: true, latestDraftPreserved: true, scope: 'ReactDOM + Happy DOM only'}));
  } finally {
    if (mounted) await act(async () => root.unmount());
    await window.happyDOM.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
