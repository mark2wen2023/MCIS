# Review-only page capabilities — developer evidence

Base `af80e1eaf37716df6e21267d10c4c975407baf24`; branch `candidate/media-demo-lazy-factory`.

Existing image/audio page response closures now pass `tasks_router is not None` / `tasks is not None` to an import-free pure HTML shaper. Only the registration argument determines capability: no request/URL/local-storage flag. Full response returns its HTML unchanged. Limited response emits a fixed false JS constant, hidden+inert task details, and a limited-mode notice. Missing/duplicate template markers raise rather than silently return a wrongly shaped limited page.

Task action assignments are conditional on that constant. Limited pages have no create/query/list/open task callbacks. Existing task fields remain inert hidden DOM nodes to preserve non-request housekeeping. This is UI capability shaping, not an authorization boundary against modified client code. Image task-backed raw/candidate download buttons are omitted, and readOriginal also stops those requests before fetch. PDF/image original controls and non-task registered raw/candidate behavior retain the existing path/guards. Audio has no corresponding task-artifact download buttons.

No factory activated; full default registration, state, storage, routes, guards and dynamic task binding checks remain. Absence of task routes does not imply absence of task-backed verification imports. Source notices still describe the broader candidate; the explicit limited notice defines the actual mode. No identity/same-origin/workspace connection added.

Executed:

```
python tests_acceptance/media-review-capability/check.py
node --test tests_acceptance/image-loaded-context/page.test.cjs tests_acceptance/audio-loaded-context/page.test.cjs
```

Python checks AST of only named modules against fixed base: after removing exactly the renderer import and wrapping call, entire app module AST matches. It extracts mount functions into fake app/path/response dependencies, invokes only fake-backed page callbacks, and proves page capability derives from task registration. It does not import app/FastAPI/ORM or invoke real page file I/O. The pure renderer only accepts supplied HTML strings.

Four Node VM scenarios exercise actual full/limited shaped inline scripts (image/audio), absent/present task callbacks, ordinary import/read, local task confirmation and fake request path, limited task-artifact suppression, and inability of a URL flag to add actions. Real fetch/decode/original loading throws. Query strings do not enable capabilities.

The same checker runs existing image URL 9 and address 21 scenarios, audio URL 7 and address 19 scenarios against limited HTML in disposable temporary source files. All passed. Full-template adjacent task/loaded-context checks passed image 5/audio 4. Counts denote separate limited checks, not overall acceptance. Initial expanded runs stopped for sparse-checkout missing test files; explicitly materializing those tracked test paths allowed the complete checker to pass; no failed product assertion was ignored.

No browser/HTTP/real task/DB/permission/model or original media testing; no broad build unrelated to standalone HTML. Existing startup and archive pause remain. Real DOM inert/hidden behavior, production identity, safe app assembly, same-origin serving and case/run selection still need accepted environment validation. No merge/deployment.
