'use strict';
const assert = require('node:assert/strict');
const path = require('node:path');
const Module = require('node:module');
const { build } = require('esbuild');

const source = path.resolve(process.argv[2] ?? path.join(__dirname, '../src/interview/InterviewView.tsx'));
const caseId = 'SYN-W3-LOCATOR-001';
const recordId = 'SYN-IR-01';
const base = '2026-02-01T12:01:40';
const utc = base + 'Z';
const turn = (round, utc, answer) => ({
  round, utc, question: '合成问题', answer,
  questionSegments: [{ start: 0, length: 4, text: '合成问题', kinds: [], statementIds: [], contradiction: 'None' }],
  answerSegments: [{ start: 0, length: answer.length, text: answer, kinds: [], statementIds: [], contradiction: 'None' }],
});
const page = {
  caseId, recordId, fictional: true, disclaimer: '仅手造数据',
  record: { recordId, evidenceId: 'SYN-REG-01', sourceSha256: '1'.repeat(64),
    interviewee: { name: '虚构甲', role: '虚构值班员', affiliation: '虚构船' }, startUtc: utc, durationMin: null },
  turns: [turn(1, null, '时间未知的回答'), turn(2, utc, '唯一时间的原有回答'), turn(3, base + '.125Z', '毫秒对应的原有回答')],
  rows: [], summary: { headerText: '合成', pendingCount: 0, staleCount: 0 },
  chart: { points: [], axisStartUtc: null, axisEndUtc: null },
  superseded: [], highlightSuppressed: false, redaction: [],
};
const roster = { caseId, fictional: true, disclaimer: '仅手造数据', records: [] };
global.fetch = () => { throw new Error('unexpected network'); };
function find(tree, pred) {
  if (Array.isArray(tree)) return tree.flatMap(x => find(x, pred));
  if (!tree || typeof tree !== 'object') return [];
  return (pred(tree) ? [tree] : []).concat(find(tree.props?.children, pred));
}
function text(tree) {
  if (Array.isArray(tree)) return tree.map(text).join('');
  if (typeof tree === 'string' || typeof tree === 'number') return String(tree);
  return tree && typeof tree === 'object' ? text(tree.props?.children) : '';
}
function only(nodes, message) { assert.equal(nodes.length, 1, message); return nodes[0]; }

(async () => {
  const result = await build({
    entryPoints: [source], bundle: true, platform: 'node', format: 'cjs', jsx: 'automatic', write: false,
    external: ['react/jsx-runtime'], logLevel: 'warning',
    plugins: [{ name: 'react-hook-stub', setup(b) {
      b.onResolve({filter: /^react$/}, () => ({path: 'react', namespace: 'w3-test'}));
      b.onLoad({filter: /^react$/, namespace: 'w3-test'}, () => ({
        contents: ['useState','useRef','useEffect'].map(name =>
          'exports.'+name+'=(...args)=>global.__w3.'+name+'(...args)').join(';'),
      }));
    }}],
  });
  const loaded = new Module(__filename, module);
  loaded.filename = __filename;
  loaded.paths = module.paths;
  loaded._compile(result.outputFiles[0].text, __filename);
  function session(p = page, r = roster, selectedRecordId = recordId) {
    const focus = [];
    const slots = [], callbacks = [];
    let cursor = 0;
    const props = { roster: r, page: p, selectedRecordId, selectedRowId: null,
      onSelectRecord: () => assert.fail('locator must not select another record'),
      onSelectRow: () => assert.fail('locator must not select or write a statement') };
    const render = (wholeView = false) => {
      cursor = 0;
      global.__w3 = {
        useState(initial) {
          const i = cursor++;
          if (!(i in slots)) slots[i] = initial;
          return [slots[i], next => { slots[i] = next; }];
        },
        useRef(initial) {
          const i = cursor++;
          return slots[i] ?? (slots[i] = { current: initial });
        },
        useEffect(callback, deps) {
          const i = cursor++;
          if (!slots[i] || deps.some((d, j) => !Object.is(d, slots[i][j]))) callbacks.push(callback);
          slots[i] = deps;
        },
      };
      const view = loaded.exports.InterviewView(props);
      const components = find(view, x => typeof x.type === 'function' && x.type.name === 'Transcript');
      if (wholeView) return view;
      if (!props.page) { assert.equal(components.length, 0); return view; }
      const component = only(components, 'actual InterviewView must mount its transcript');
      const rendered = component.type(component.props);
      const located = find(rendered, x => x.props?.['aria-current'] === 'location');
      for (const item of located) {
        assert.equal(item.props.tabIndex, -1);
        assert.ok(item.props.ref);
        item.props.ref.current = { focus: () => focus.push(item.props['data-round']) };
      }
      callbacks.splice(0).forEach(callback => callback());
      return rendered;
    };
    const marker = () => find(render(), x => x.props?.['aria-current'] === 'location');
    const edit = value => only(find(render(), x => x.type === 'input'), 'locator input').props.onChange({target: {value}});
    const submit = () => only(find(render(), x => x.type === 'form'), 'locator form').props.onSubmit({preventDefault() {}});
    const lookup = value => { edit(value); submit(); return render(); };
    const compareButtons = () => find(render(true), x => x.type === 'button' && text(x).includes('定位所选比对条目的原文问答'));
    return {render, marker, edit, submit, lookup, focus, props, compareButtons};
  }

  let s = session();
  assert.equal(s.marker().length, 0);
  assert.match(text(s.render()), /定位问答/);
  assert.match(text(s.render()), /供人工核对.*不生成引文/);
  let rendered = s.lookup(utc);
  assert.match(text(rendered), /已定位到第 2 轮/);
  let marker = only(s.marker(), 'unique exact turn');
  assert.match(text(marker), /唯一时间的原有回答/);
  assert.doesNotMatch(text(marker), /时间未知|毫秒对应/);
  assert.deepEqual(s.focus, [2]);
  s.edit(base + '.12Z');
  assert.equal(s.marker().length, 0, 'editing clears old marker');
  s.submit(); assert.match(text(s.render()), /没有这个已登记的问答时间/);
  assert.equal(s.marker().length, 0, 'Two-place fraction normalized to 120ms, not 125ms');
  s.lookup(base + '.125Z');
  assert.equal(only(s.marker(), 'millisecond').props['data-round'], 3);
  s.lookup(base + '.000Z');
  assert.equal(only(s.marker(), 'zero milliseconds is the exact whole second').props['data-round'], 2);
  assert.deepEqual(s.focus, [2, 3, 2]);
  assert.equal(find(s.render(), x => x.type === 'a').length, 0, 'no citation or link created');
  for (const bad of ['', '2026-02-30T12:01:40Z', base + '+00:00', base + '.1251Z']) {
    assert.match(text(s.lookup(bad)), /请输入有效的 UTC 时间/);
    assert.equal(s.marker().length, 0);
  }
  s = session({ ...page, turns: [...page.turns, turn(4, base + '.000Z', '第二个同秒回答')] });
  assert.match(text(s.lookup(utc)), /有多轮使用同一时间/);
  assert.equal(s.marker().length, 0);
  for (const turns of [[{ ...page.turns[1], highlightSuppressed: true }],
    [page.turns[1], turn(2, null, '重复轮次')]]) {
    s = session({ ...page, turns });
    assert.match(text(s.lookup(utc)), /来源或轮次标识不足/);
    assert.equal(s.marker().length, 0);
  }
  s = session({ ...page, turns: [page.turns[0]] });
  assert.match(text(s.lookup(utc)), /没有这个已登记的问答时间/);
  assert.equal(s.marker().length, 0);

  for (const p of [{ ...page, caseId: 'different-case' }, { ...page, recordId: 'different-record' },
    { ...page, record: { ...page.record, recordId: 'different-record' } },
    { ...page, record: { ...page.record, evidenceId: null } },
    { ...page, record: { ...page.record, sourceSha256: '' } },
    { ...page, record: { ...page.record, sourceSha256: 'malformed' } }, { ...page, highlightSuppressed: true }]) {
    s = session(p); rendered = s.render();
    assert.match(text(rendered), /缺少可用来源绑定/);
    assert.equal(find(rendered, x => x.type === 'form').length, 0);
    assert.equal(s.marker().length, 0);
  }
  s = session(page, roster, 'another-selected-record');
  assert.doesNotMatch(text(s.render()), /定位问答/);
  assert.equal(s.marker().length, 0);
  s = session(null);
  assert.doesNotMatch(text(s.render()), /定位问答|唯一时间的原有回答/);
  console.log('W3 exact registered transcript locator: 18 synthetic scenarios passed (component callbacks, not browser or HTTP).');

  const statementId = 'SYN-ST-2';
  const reviewed = { statementId, reviewStatus: 'Confirmed', state: 'Confirmed', isStale: false,
    statementMissing: false, statementRevision: 2, statementVersion: 2, outcome: 'Consistent',
    summary: '虚构事故时刻：另一个时间', citation: '不应从显示文案推测：第 3 问' };
  const bridged = { ...page.turns[1],
    answerSegments: [{ ...page.turns[1].answerSegments[0], statementIds: [statementId] }] };
  const comparePage = { ...page, rows: [reviewed], turns: [page.turns[0], bridged, page.turns[2]],
    chart: { ...page.chart, points: [{ statementId, statementUtc: base + '.125Z',
      observedUtc: base + '.125Z', summary: '有意不同的事故与数据时点' }] }};

  s = session(comparePage);
  let action = only(s.compareButtons(), 'actual comparison entry');
  assert.equal(s.marker().length, 0, 'no navigation before explicit click');
  action.props.onClick();
  assert.equal(only(s.marker(), 'linked response').props['data-round'], 2, 'only the containing turn, not chart or display citation');
  assert.deepEqual(s.focus, [2]);
  assert.equal(s.compareButtons().length, 1, 'success keeps entry');
  s.edit(base + '.125Z');
  assert.equal(s.marker().length, 0, 'typing clears comparison marker');
  s.submit();
  assert.equal(only(s.marker(), 'manual locator remains independent').props['data-round'], 3);
  s.props.page = { ...comparePage };
  assert.equal(s.marker().length, 0, 'same record with refreshed response is not auto-located');
  action.props.onClick();
  assert.equal(s.marker().length, 0, 'stale callback cannot jump in the refreshed response');
  only(s.compareButtons(), 'refreshed comparison entry').props.onClick();
  assert.equal(only(s.marker(), 'fresh deliberate navigation').props['data-round'], 2);

  for (const row of [
    { ...reviewed, reviewStatus: 'Draft' }, { ...reviewed, state: 'PendingConfirmation' },
    { ...reviewed, isStale: true }, { ...reviewed, statementMissing: true },
    { ...reviewed, statementVersion: 1 }, { ...reviewed, statementVersion: null },
  ]) assert.equal(session({ ...comparePage, rows: [row] }).compareButtons().length, 0);
  assert.equal(session({ ...comparePage, rows: [reviewed, reviewed] }).compareButtons().length, 0);

  const secondField = { ...bridged, questionSegments: bridged.answerSegments };
  const secondRound = { ...page.turns[2], questionSegments: bridged.answerSegments };
  for (const turns of [
    page.turns, // accident/observed timestamps are still in the chart, but no structured span
    [{ ...bridged, utc: null }, page.turns[2]], // registered transcript time remains unknown
    [{ ...bridged, utc: 'not-a-time' }, page.turns[2]],
    [secondField], [bridged, secondRound], [bridged, { ...page.turns[2], utc }],
    [{ ...bridged, highlightSuppressed: true }],
  ]) assert.equal(session({ ...comparePage, turns }).compareButtons().length, 0);
  assert.equal(session({ ...comparePage, caseId: 'unselected-case' }).compareButtons().length, 0);
  assert.equal(session(comparePage, roster, 'unselected-record').compareButtons().length, 0);
  assert.equal(session({ ...comparePage, record: { ...comparePage.record, evidenceId: null } }).compareButtons().length, 0);
  s = session(comparePage);
  s.props.selectedRowId = 'unlinked-row';
  s.props.page = { ...comparePage, rows: [reviewed, { ...reviewed, statementId: 'unlinked-row' }] };
  assert.equal(s.compareButtons().length, 0, 'selected row never falls back to another linked row');
  s.props.page = comparePage;
  assert.equal(s.compareButtons().length, 0, 'disappeared selected row never falls back to first row');
  console.log('W3 comparison-to-transcript entry: 20 synthetic scenarios passed (actual click callback, not browser or HTTP).');
})().catch(error => { console.error(error); process.exitCode = 1; });
