# Native read-only media inventory and revision/audit preflight

Base `3f6445ff01092e9c3a82cce233708f7a5a5095e7`; separate branch `research/media-archive-preflight`.

## Implemented research scope

`preflight.scan(sqlite_connection, case_id)` requires an already-open explicit SQLite transaction. Tests use a **mode=ro** connection to a temporary native candidate database. The function performs SELECT and read-only table_info inspection only. It has no product route, role parameter, authorization grant, original-file reader, exporter, file publisher, active receipt writer or task dispatcher. Never invoke it against a private/production store as a substitute for existing authorization.

It inventories **every case_id-scoped table** found in sqlite_master, preserves all native columns and JSON/line text for the requested case (not only latest revisions), and returns the names of unscoped tables as explicitly unassessed. Other cases' rows are not returned. Limits are10000 rows per scoped table and32MiB estimated serialized row content; over-budget rejects, not truncates. It does not certify all global/unscoped data or unknown business modules as recoverable. Future nonempty audio_/image_ tables reject until understood. Other case-scoped business rows remain in the inventory but have no restoration approval.

Both revision/task tables for each media kind must exist together or both be absent. Required case, evidence, custody and audit tables must exist; an absent/ambiguous case rejects. All media revisions are grouped by native case/run and must contain revision0 and contiguous versions. Task identity, success/run reciprocal binding, original imported/task bindings and required registration rows must be present. Evidence registration matching is **registry-only**: original intake path identifier, evidence key, Register detail case/digest, and recorded SHA equality are checked; source bytes and full native intake receipt reconstruction are NOT checked. bytes_verified=false remains unconditional.

Audit rows must agree with their stored full line and contiguous case sequence/hash chain. For each revision, match action, command/run or task ID, entity ID, recorded operator/role, and (for human revisions) exact native after-summary revision plus segmentId/lineIndex. Exactly one match is required. Parsed after is the existing bounded Python-literal dictionary representation, never eval or execution. Do not require revision.utc == audit.utc: the existing code uses two clock reads. Missing, ambiguous, unparsed/truncated, or unrepresented media audit events reject. Artifact-access events are retained as access events and require an existing task; they do not count as revisions. These checks establish uniqueness **within the supplied native snapshot**, not authenticated actor identity or historical truth.

Tasks retain recorded status. succeeded must have a matching published revision0; failed/interrupted_unknown require the recorded failure audit; running_or_unknown stays unknown with its start event. No task is resumed or converted into success. Native ASR uses **asr.task.incomplete**, whereas OCR uses ocr.task.failed/unknown. The prior offline contract prototype mistakenly enumerated ASR failed/unknown; this candidate corrects that enumeration and adds two ordinary regression cases. No native task behavior changes.

## Ordinary developer validation

Exact command (repository root):
```
PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q research/media_archive/test_contract.py service/tests/test_media_archive_preflight_research.py --tb=short
```
Final: **57 passed in4.63s**, zero failures/skips:42 offline contract tests (prior40 plus2 native-action examples) and15 native-inventory tests. Earlier12/54 runs are subsets, not additive coverage. This is developer validation, not independent acceptance.

Native audio fixtures use the actual optional app's HTTP intake, machine-draft attachment and revision calls on generated tone data. They are not ASR or human speech accuracy tests. Task fixtures use an explicitly fabricated executor result or injected ordinary pre-publication exception/timeout; no actual model/worker timeout/crash is exercised. Successful, failed and interrupted_unknown task actions were actually produced by that candidate API. Two same-actor runs with the same revision numbers remain distinct.

Missing/ambiguous examples are rebuilt into **new bare in-memory SQLite fixtures** from synthetic inventories; product append-only triggers are neither removed nor bypassed in the source store. They cover absent initial/revision/audit/registration/evidence/table, duplicate matching event, unknown media table and other-case/transaction prerequisites. Image shape is a fabricated fixture adapted to the read native image source contract; it is NOT execution of image91962113 or OCR. The scanner's successful calls change no database rows; one temporary read-only connection check confirms writes are refused.

## Still blocked / not claimed

Output is always restore_ready=false, export_allowed=false, bytes_verified=false. Complete member extraction is not wired to the previous index validator. Source files/custody-line semantics, full machine artifacts/segment binding, unique complete registration history, file snapshot consistency, global-table inventory, file publication/DB commit and all product access entrances remain unvalidated prerequisites. v2 audio without raw recognizer output can be inventoried but still cannot satisfy the proposed complete media archive. No permission equivalence proof or production identity claim is made. Nothing converts this row inventory into an authorized downloadable archive.

No browser, actual model, real-media original reading, production database, vulnerability reproduction, restricted historical security/ECFC suite, PR body update, merge or deployment. Previous freeze for contract.py/test_contract.py is superseded only by this candidate's new freeze; original40-test report remains the historical record for its original commit.
