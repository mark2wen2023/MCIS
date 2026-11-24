# Same mounted root, fixed T124 input lifecycle
Base 5052c885fab13c558f51157ebea2328010d3aac7. Only this new test directory.
Actual unchanged SingleSeatCard and exact prior result.json are verified by Git blob hash.
No copies of those dependencies are committed. ReactDOM client renderer is reused.

Run from candidate checkout with existing installed dependencies:
node research/single_seat_lifecycle/run.cjs /existing/web/node_modules /existing/happy-dom/lib/index.js

Actual Linux command (exit 0):
node w20-seat-lifecycle-20261124/research/single_seat_lifecycle/run.cjs mcis-work/web/node_modules w19-react-1600/node_modules/happy-dom/lib/index.js

One createRoot; seven committed renders under React act:
valid clone -> null -> independently parsed valid clone -> unsupported changed timestamp
-> valid clone -> undefined -> valid clone. The fixture has no independent revision field;
changed timestamp is a rejected input version, NOT an admitted second receipt version.
Each invalid phase asserts prior pointer and summary nodes are disconnected and absent from
the current container, old evidence ID/pointer absent from text, alert present, and detached
nodes cannot become document.activeElement when programmatically focused.
Each restoration checks pointer exists as a new node, pending/no-turn limitation and no
write/link controls. Original fixture is unchanged. Final root.unmount and DOM close awaited.

Observed: 1 root, 7 phases PASS, exit 0. happy-dom 21.0.4 and installed React/esbuild only.
Initial run assertions passed but Node remained alive; interrupted exit 130. Runner now
exits explicitly only after awaited main cleanup; rerun exit 0. No failures suppressed.
Network and storage mutations throw. No service, browser, model or install.

Limits: DOM simulation only. Programmatic focus checks do not establish browser tab order,
accessibility or a real revocation event. Null/undefined are supplied by the test host.
No product route or permission logic is added; host-driven clearing remains unconnected.
Next real dependency: a separately authorized trusted host must clear the displayed receipt
on source/version/case invalidation; after that, same-root browser lifecycle can be tested.
Do not infer T100 integration, real source authenticity, human review or withdrawal enforcement.
