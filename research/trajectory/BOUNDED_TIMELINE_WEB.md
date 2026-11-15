# Bounded1.4 frontend intake alignment candidate

Parent2cb43812eaa9e43e938748085cb5fed39c22b331. Reuses the two frontend files
from prior unmerged7aa9b9f, with new scoped tests. No backend/permission change.

parsePreview permits1.4 only with working-record-v1 exact fields and existing
bounded integer counts/archived receipt/self-reported identity markers. Working-v2
and any trackReceiptCount field reject for1.4. Optional HFACS summary is validated
by its existing rules; this is not actual HFACS core execution. Unknown versions,
malformed summaries and error responses reject. Receipt must match preview version,
SHA, case, counts and extension values. Version1.0–1.3 checks remain supported.

Visible preview AND receipt summaries state the limited working-record+timeline
scope. General explanation explicitly excludes track-history combinations, conflicts,
safety recommendations, consultation, COLREG and agent drafts; other unsupported
states still require whole-package rejection. Imported flags/roles are historical
claims, not authentication or new human approval. No automatic retry/identity-lock
code was changed; existing request/confirmation/unknown-result flow remains.

The browser does NOT inspect archive members or infer source truth from a summary.
Timeline1–256 row range, source reference closure, no-unsupported-state rule and
transaction validation remain server responsibilities. Frontend count checks do
not replace them. Existing server whole-refusal test rerun for recommendation
state. This is not support for complex demo cases or track-history+timeline.

## Developer results

- New tests:68 constructed/SSR checks plus2 actual synthetic HTTP preview/receipt
  parsing checks =70 passed. Wrong/unknown versions, missing extensions, v2 or
  track field, count0/max and invalid values, mismatched receipt and visible scope.
- bash tests/run-package-intake-w85.sh: passed (existing model/render/transport).
- archive-b-model.test.tsx bundled and executed: passed.
- npm run build: passed; existing >1500kB chunk warning.
- Backend test_bounded_timeline_archive_increment.py:6 passed in3.75s.
- package-hfacs-w186.test.tsx FAILED on PackagePanel's '不是全系统备份' rendering
  assertion. Same failure reproduced on exact parent2cb43812.
- archive-guard-ui.test.tsx FAILED on existing interview-page1.2 wording assertion.
  Same failure reproduced on exact parent2cb43812. Neither test was edited; these
  are retained baseline failures, not reported as a passing frontend full suite.

Real browser was NOT executed. No click/upload/navigation/touch acceptance claim.
No restricted security/history/ECFC tests, SDK install or production deployment.
Original190 not rerun; original known failures and prior safety limits remain.

## Reproduction

From web:
```
./node_modules/.bin/esbuild tests/bounded-timeline-intake.test.tsx --bundle --platform=node --format=cjs --jsx=automatic --outfile=/tmp/bounded-timeline-intake.cjs --loader:.css=empty --log-level=warning
node /tmp/bounded-timeline-intake.cjs
bash tests/run-package-intake-w85.sh
npm run build
```
Without optional argument this runs68 checks. For the extra2, obtain actual JSON
from the parent backend's synthetic fixture via these commands from service:
```
.venv/bin/python - <<'PY'
import tempfile,base64,json
from pathlib import Path
from tests.test_bounded_timeline_archive_increment import populate,exported,commit
from tests.test_working_record_archive import client_at,checked
with tempfile.TemporaryDirectory(prefix='bounded-web-http-') as tmp:
 with client_at(Path(tmp)/'source',True) as source:
  populate(source); raw=exported(source)
 with client_at(Path(tmp)/'restore') as dest:
  preview=checked(dest,'post','/api/v1/packages/intakes:preview',{'contentBase64':base64.b64encode(raw).decode()}).json()
  receipt=commit(dest,raw).json()
  Path('/tmp/bounded-web-http.json').write_text(json.dumps({'preview':preview,'receipt':receipt}))
PY
node /tmp/bounded-timeline-intake.cjs /tmp/bounded-web-http.json
```
Only synthetic local responses; archive/source bytes are not committed. A real
private-case package must not be substituted or uploaded as a testing fixture.
