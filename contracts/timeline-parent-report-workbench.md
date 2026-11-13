# Parent-report declaration in registered preview workbench

Optional report association UI appears only when source nature is report_extract.
Select another same-case locally registered Document from current evidence list;
its current SHA is captured visibly, never typed or silently upgraded. List cannot
prove the registered filename is PDF: server checks .pdf/Document and receipt.
Candidate labels therefore say Document candidate, not verified PDF.

Changing source nature away from report_extract clears parent selection. Case,
identity, source metadata, mapping/declaration/parent edits invalidate results and
acknowledgement; pending output is discarded through existing generation guard.
Before dispatch confirm selected parent still present/eligible with captured SHA.
Response parent snapshots must exactly match selected extract/parent IDs and SHA,
carry user_declared_not_verified and bounded byte length. Unsolicited/missing/false
verified links are rejected. Legacy responses may omit empty parent snapshots
only when no parent was requested. No original mutation, upload or auto-download.

Display checked parent bytes separately from relation validity; relation is a
user declaration, not an extraction accuracy, valid-PDF, fact approval or
independent-corroboration claim. No persistent relation or new permissions.

## Recovery acceptance 2026-11-13
Recovered interrupted UI in an isolated directory; original draft preserved.
Missing report.schema.json was restored from the existing same-revision contracts,
not bypassed. TypeScript/Vite build passes (existing large bundle warning).
Primary HappyDOM/control-fetch suite45 checks passes; independent suite48 checks
passes, both include the prior23 checks, so counts must not be summed as unique.
Independent tests cover parent candidate eligibility, frozen SHA request,
response tampering/missing/extra/false verified, parent metadata change cancellation,
late response discard, no silent version upgrade and source-nature reset.
These are synthetic UI/model tests and an old captured HTTP response fixture,
NOT a new browser visual/E2E test, new live backend call, real LLM, CI or full
system approval. Backend parent-report acceptance belongs to commit0a7fb3a.
No merge/deployment, persistent relation or semantic extraction verification.

Reproduce from web:
- npm run build
- bash tests/registered-acceptance/run.sh
- NODE_PATH=tests/registered-acceptance/node_modules node_modules/.bin/esbuild tests/parent-report-review.tsx --bundle --platform=node --format=esm --outfile=tests/.tmp-parent-review.mjs --jsx=automatic --loader:.css=empty --banner:js='import { createRequire } from "node:module"; const require = createRequire(import.meta.url);'
- node tests/.tmp-parent-review.mjs

Frozen implementation SHA256:
- registered.ts: 942a7d88ae08a2d7a89982cf35a26f664fe225adad048003dd2214b2f4c7506a
- RegisteredPreviewPanel.tsx: f245cb037163cd9ecdd8c56ed4ed26694e0594107b1a9733496bdace82c3f208
