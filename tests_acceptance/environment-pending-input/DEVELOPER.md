# Environment pending input — development evidence

Base 44bbccde5dc713b1a2ee1f7ff5ee6f92ce5a1af1; remote fix/environment-explicit-origin checked unchanged. Separate candidate fix/environment-pending-input.

Reviewed test uses actual panel callbacks with synthetic hooks/JSX and controlled memory POST Promise. fetch throws. No browser, HTTP, backend, cases, models, paused/refusal/write-probe tests. Before fix normal success control completed; retained origin callback changed form after dispatch and before busy rerender; successful response hid this changed form, assertion failed. This synthetic sequence is not proof real React/browser dispatches that event order.

Minimal editForm gate uses existing synchronous busy/alive/identity plus rendered pending/saved state for all fields. Existing fieldset-disabled semantics, server contract, payload snapshot validation, unknown verification and old records unchanged. This is not a universal stale callback guarantee after finish clears busy or across React concurrency; those windows are not covered.

Commands in web:
```
node tests/environment-pending-input.cjs
node tests/environment-explicit-origin.cjs
node_modules/.bin/tsc -b --force
node_modules/.bin/vite build
```
Four new synthetic sequences passed: no pending edit, retained source, numeric, all inputs; each checks pending fieldset, preserved submitted snapshot, success view and Continue New editable empty-origin reset. Existing three-origin synthetic test passed separately. TypeScript and Vite passed (767 modules, existing >1500 kB chunk warning). Existing copied dependencies reused; no installation. Hook effects are doubles: no real React scheduling/unmount, browser, HTTP, production identity, CI or independent verification claimed. No merge/deploy.
