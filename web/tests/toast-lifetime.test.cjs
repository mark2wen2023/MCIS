// Synthetic React-hook and clock harness, not a browser or HTTP test.
const assert = require('node:assert/strict')
const vm = require('node:vm')
const { buildSync } = require('esbuild')
const code = buildSync({ entryPoints: ['src/components/Toast.tsx'], bundle: true,
  platform: 'node', format: 'cjs', jsx: 'automatic', write: false,
  external: ['react', 'react/jsx-runtime', '../api'] }).outputFiles[0].text
function harness() {
  let state = null
  const timers = []
  const module = { exports: {} }
  const react = { createContext: () => ({ Provider: 'Provider' }),
    useState: () => [state, value => { state = typeof value === 'function' ? value(state) : value }],
    useCallback: fn => fn, useContext: () => {} }
  const jsx = (type, props) => ({ type, props })
  vm.runInNewContext(code, { module, exports: module.exports,
    require: name => name === 'react' ? react : name === 'react/jsx-runtime' ? { jsx, jsxs: jsx } : { ApiError: class extends Error {} },
    window: { setTimeout: (fn, ms) => { assert.equal(ms, 3800); timers.push(fn) } } })
  const show = module.exports.ToastProvider({ children: null }).props.value
  return { show, timers, state: () => state }
}
const scenarios = [
  ['same success twice', '已保存', 'ok', '已保存', 'ok'],
  ['same error twice', '暂时无法保存', 'err', '暂时无法保存', 'err'],
  ['same text different kind', '操作结果', 'ok', '操作结果', 'err'],
  ['different messages', '已保存', 'ok', '暂时无法保存', 'err'],
]
for (const [name, first, firstKind, second, secondKind] of scenarios) {
  const h = harness()
  h.show(first, firstKind)
  h.show(second, secondKind)
  h.timers[0]() // first deadline reached; the newer message must survive
  assert.equal(h.state()?.text, second, name)
  assert.equal(h.state()?.kind, secondKind, name)
  h.timers[1]()
  assert.equal(h.state(), null, name + ' expires at its own deadline')
}
const single = harness()
single.show('单次保存', 'ok')
single.timers[0]()
assert.equal(single.state(), null)
console.log('toast lifetime: 5 synthetic scenarios passed')
