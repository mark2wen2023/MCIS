'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const Module = require('node:module');
const { build } = require('esbuild');

// Exercise the actual RoundLifecycle event callbacks, with an isolated synchronous hook
// stub and a recording mutation port. No app server, HTTP, browser, DB or case seeds.
const source = path.resolve(process.argv[2] ?? path.join(__dirname, '../src/consultation/RoundLifecycle.tsx'));
const caseId = 'SYN-W7-AGREED-001';
global.fetch = () => { throw new Error('Network is forbidden in this synthetic check'); };
function stateSlot(initial) {
  const { state } = global.__w7;
  const i = state.index++;
  if (!(i in state.values)) state.values[i] = initial;
  return [state.values[i], next => {
    state.values[i] = typeof next === 'function' ? next(state.values[i]) : next;
  }];
}
function findAll(tree, predicate) {
  if (Array.isArray(tree)) return tree.flatMap(x => findAll(x, predicate));
  if (!tree || typeof tree !== 'object') return [];
  return (predicate(tree) ? [tree] : []).concat(findAll(tree.props?.children, predicate));
}
function textOf(tree) {
  if (Array.isArray(tree)) return tree.map(textOf).join('');
  if (typeof tree === 'string' || typeof tree === 'number') return String(tree);
  return tree && typeof tree === 'object' ? textOf(tree.props?.children) : '';
}
function only(nodes, name) {
  assert.equal(nodes.length, 1, name);
  return nodes[0];
}
const event = { preventDefault() {} };
const round = {
  caseId, roundNo: 1, draftVersion: 'v0', openedUtc: '2026-02-01T00:00:00Z',
  deadlineUtc: '2026-03-03T00:00:00Z', isClosed: false, daysRemaining: 30,
  allReplied: false, parties: [], partyStatus: [], replies: [], comments: [],
};
(async () => {
  const result = await build({
    entryPoints: [source], bundle: true, platform: 'node', format: 'cjs', jsx: 'automatic',
    write: false, logLevel: 'warning', external: ['react/jsx-runtime'],
    plugins: [{ name: 'local-hook-stub', setup(b) {
      b.onResolve({filter: /^react$/}, () => ({path: 'react', namespace: 'w7-test'}));
      b.onLoad({filter: /^react$/, namespace: 'w7-test'}, () => ({
        contents: 'exports.useState = initial => global.__w7.useState(initial)',
      }));
    }}],
  });
  const loaded = new Module(__filename, module);
  loaded.filename = __filename;
  loaded.paths = module.paths;
  loaded._compile(result.outputFiles[0].text, __filename);
  const { RoundLifecycle } = loaded.exports;
  function session({ rounds = [], current, writable = true, busy = false } = {}) {
    const state = { index: 0, values: [] };
    const calls = [];
    const props = {rounds, current, writable, busy, mutate: async (...args) => { calls.push(args); }};
    const render = () => {
      state.index = 0;
      global.__w7 = { useState: stateSlot, state };
      return RoundLifecycle(props);
    };
    const query = predicate => findAll(render(), predicate);
    const label = name => only(query(x => x.type === 'label' && textOf(x) === name), name);
    const input = name => only(findAll(label(name), x => x.type === 'input'), name + ' input');
    const type = (name, value) => input(name).props.onChange({target: {value}});
    const toggle = checked => input('登记已商定期限').props.onChange({target: {checked}});
    const click = name => only(query(x => x.type === 'button' && textOf(x) === name), name).props.onClick();
    const submit = () => only(query(x => x.type === 'form'), 'round form').props.onSubmit(event);
    const texts = () => textOf(render());
    const fill = () => {type('草案版本', ' synth-v1 '); type('相关方编号', ' F1 '); type('相关方名称', ' 虚构方 ');};
    return {render, query, input, type, toggle, click, submit, fill, texts, calls, props};
  }
  const declared = (days, isAgreedDeadline) => [
    ['/consultation/rounds', {
      draftVersion: 'synth-v1', parties: [{partyId: 'F1', name: '虚构方'}], draftSha256: '',
      days, isAgreedDeadline,
    }, false],
  ];

  let s = session(); s.fill();
  assert.equal(s.input('登记已商定期限').props.checked, false);
  assert.doesNotMatch(s.texts(), /已商定期限（天）/);
  s.submit(); assert.equal(s.calls.length, 0);
  assert.match(s.texts(), /默认期限：服务登记时间起 30 天/);
  s.click('确认登记'); assert.deepEqual(s.calls, declared(30, false));

  s = session(); s.fill(); s.toggle(true); s.type('已商定期限（天）', '45');
  assert.match(s.texts(), /系统不核验是否已经商定/);
  s.submit(); assert.equal(s.calls.length, 0);
  assert.match(s.texts(), /申报已商定期限：服务登记时间起 45 天/);
  assert.match(s.texts(), /不会向相关方发送消息/);
  s.click('返回修改'); assert.equal(s.calls.length, 0);
  assert.equal(s.input('已商定期限（天）').props.value, '45');
  s.type('已商定期限（天）', ' 30 '); s.submit();
  assert.match(s.texts(), /申报已商定期限：服务登记时间起 30 天/);
  s.click('确认登记'); assert.deepEqual(s.calls, declared(30, true));

  s = session(); s.fill(); s.toggle(true); s.type('已商定期限（天）', '45');
  s.submit(); s.click('确认登记'); assert.deepEqual(s.calls, declared(45, true));

  s = session(); s.fill(); s.toggle(true); s.type('已商定期限（天）', '45');
  s.toggle(false); s.submit(); s.click('确认登记');
  assert.deepEqual(s.calls, declared(30, false), 'a hidden custom value does not affect default mode');

  for (const days of ['1', '180']) {
    s = session(); s.fill(); s.toggle(true); s.type('已商定期限（天）', days);
    s.submit(); s.click('确认登记'); assert.deepEqual(s.calls, declared(Number(days), true));
  }
  for (const days of ['', ' ', '0', '181', '-1', '1.5', '1e2', '３０']) {
    s = session(); s.fill(); s.toggle(true); s.type('已商定期限（天）', days); s.submit();
    assert.match(s.texts(), /已商定期限须为 1 至 180 的整数天数/);
    assert.doesNotMatch(s.texts(), /确认新建轮次/); assert.equal(s.calls.length, 0);
  }

  s = session({rounds: [round]});
  assert.match(s.texts(), /已有未关闭轮次，不能新建/); assert.doesNotMatch(s.texts(), /登记已商定期限/);
  assert.equal(session({writable: false}).render(), null);
  s = session(); s.fill(); s.toggle(true); s.type('已商定期限（天）', '45');
  s.props.busy = true;
  assert.equal(s.input('登记已商定期限').props.disabled, true);
  assert.equal(s.input('已商定期限（天）').props.disabled, true);
  s.submit(); assert.equal(s.calls.length, 0);
  assert.doesNotMatch(s.texts(), /确认新建轮次/);
  console.log('W7 agreed deadline 17 synthetic form scenarios passed (fixed case, callback stub, not browser or HTTP).');
})().catch(error => { console.error(error); process.exitCode = 1; });
