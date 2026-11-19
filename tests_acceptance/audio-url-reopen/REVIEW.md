# Audio current-record URL reopen — developer verification

Base: `ec3e2927e2c46e2d2b0b6ec7c489b8d2126fecec`, branch `candidate/media-demo-lazy-factory`.

In an otherwise authorized, separately accepted deployment, the existing standalone page accepts `/audio-review-lab?case=<encoded-case-id>&run=<AR-32-lowercase-hex>` and invokes its existing detail reader. This is **current review record** reopening, not frozen report revision selection. No automatic attachment, save, original download, playback or model task. No parameters retain manual entry. Query context requires exactly one case and run, no other keys; invalid links clear both inputs and do not read. Manual correction is possible. Existing server guard is unchanged; this change supplies no identity or permission.

Static source check: `audio_review/app.py` `get` uses `authorize`, exact `rows(case_id, run_id)` and `check` before returning `caseId`/`runId`. This is not proof that those checks execute safely in this environment. Case syntax follows `evidence_intake/parser.py` SAFE_ID; run syntax follows the server-generated AR + uuid4 hex. Existing read handler checks response identity. Stale read success/error after target change is now ignored, preserving current feedback and existing drafts/loaded-context labeling.

Executed (no application imports, network, media, database or browser):

```
node --test tests_acceptance/audio-url-reopen/page.test.cjs
node --test tests_acceptance/audio-loaded-context/page.test.cjs
web/node_modules/.bin/tsc -b web/tsconfig.json --force
web/node_modules/.bin/vite build web
```

New 7 named synthetic cases passed (invalid-link case contains multiple inputs); adjacent 4 loaded-context/draft cases passed. Node VM executes the production inline script with handmade DOM and memory promises replacing `json`; real fetch throws. No Save or authorization test. Baseline source supplied through `AUDIO_PAGE_SOURCE` fails the explicit URL case (0 requests instead of 1); candidate passes. These counts are separate scoped checks, not full acceptance.

TypeScript passed; Vite 8.3.8 built 766 modules with existing >1500 kB chunk warning. Reused existing offline dependencies; no install. Web build does not bundle this standalone HTML, which is exercised by the Node tests. True DOM/browser navigation, actual HTTP, authentication/authorization, server response checks, original audio and playback remain unverified. Backend startup and archive testing remain paused; no startup permission follows from this change. Image URL reopening and workspace links remain unconnected. No branch merge or deployment.
