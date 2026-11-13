# Registered evidence CSV timeline preview

## Scope
POST /api/v1/cases/{case_id}/timeline/registered-align-preview
is a real service integration of existing local evidence-intake validation and
existing W2 CSV alignment. It is read-only: no timeline/agent draft/source edit,
no local admission receipt, no new table or archive whitelist change.

Request: sources (1–4), each evidenceId and csvMapping (timeColumn plus selected
Heading/CourseOverGround/SpeedOverGround columns). No inline text, paths, source
hashes or approval flags accepted. Source labels are the server-resolved IDs.

## Source and access boundary
Only current locally registered evidence-intake records with their original
receipt and a .csv fileName are supported. Existing intake authorization checks
investigation role, evidence_meta/testimony level and restricted-evidence policy;
timeline read permission is additionally required. Case-scoped evidence lookup
and fixed raw/evidence-intakes/<64hex>/source.bin paths prevent caller path input.
Existing receipt validation recomputes actual file SHA/request binding, compares
registry identity and custody Register line, and rejects Change/inconsistency.
Archived imports remain history-only under the existing receipt lookup gate.
Legacy arbitrary raw paths are not silently upgraded to trusted local intake.

Before computation and after computation, resolve again in fresh SQLite
transactions, including permissions, evidence bytes, registration and review
state. Compare byte snapshots and the initial/final/core case epoch. Changed
bytes, denied permissions, missing sources or review flags suppress the result.
Reads are bounded by existing intake8MiB cap; preview rejects individual files
above256KiB and total decoded text above1MiB. Input lists are at most4.

UTF-8 or UTF-8 BOM only. Hash covers exact original bytes, while BOM is removed
only in the in-memory CSV parsing view. Require unique headers/mapped columns,
matching row shape, explicit timezone, finite selected numeric values, angles
0–360 and nonnegative speed. Formula strings in mapped numeric columns reject;
no spreadsheet engine runs. Extra unselected columns are not executed. Invalid
rows are not silently skipped and called a successful no-conflict result.
Caller mapping remains an interpretation requiring human validation, not a
server-certified choice of sensor, ship, clock or measurement semantics.

## Output and nonclaims
Existing preview response plus sourceSnapshots containing evidenceId,
sourceSha256, registrationDigest, byteLength and registeredUtc;
sourceBinding='transient-local-intake-bytes'; observationApproval='not_assessed'.
Snapshots describe exactly the bytes/registration checked, not a transferable
receipt or permission. No-store route. No source bytes returned in snapshots.
Unverified custody status alone is allowed because this route checks actual
bytes; NeedsReview or Mismatch reject. Hash agreement is not factual accuracy,
independent evidence, original sensor telemetry or investigator approval.

This does not replace durable binding and review-state/version design, support
restoring active receipts, produce a human-approved finding or add a UI/LLM.
Original signature/status and source bytes remain unchanged. Reuses existing
intake reader path checks and leaf O_NOFOLLOW; not a new defense against a local
actor able to race parent directory replacement. No atomic authorization lease:
last-check-to-response race and transient change/revert are outside guarantees.
HTTP role headers are existing local-development identities, not production
authentication. Core subprocess limits remain the existing implementation.

## Verification
Native implementation and separate native reviewer. Fictional CSV fixtures,
actual evidence-intake preview/commit and SQLite. Most failure probes stub the
core; actual compiled W2 is used for explicit5-degree conflict checks. A local
loopback uvicorn+httpx test exercises the real HTTP port and actual W2, not only
TestClient. No public deployment, real LLM, production-auth or real-incident
accuracy claim. Exact final counts recorded after independent review.

Independent testing found Python float accepted `1_0` while W2 diagnosed an
invalid CSV number. Fixed before publication: selected values now require ASCII
decimal/scientific notation before finite/range checks, and any core import
Error suppresses a successful result. Explicit ISO timestamps are restricted
to DateTimeOffset-compatible timezone range±14h. Probe inputs containing
underscore/Unicode numerals and Error diagnostics are separate regression cases.

Final verification after fixes: independent30/30 passed, zero skips (18 primary
including2 actual W2 tests, one via real loopback HTTP;12 independent core-double
probes). Final selected regression195/195 passed, zero skips,72.56s, including
previous align-preview/W4, agents/W20, permission, package and binding-boundary
suites. This is the selected cloud test set, NOT the entire repository test suite
or CI. Existing Starlette/httpx deprecation warning remains.
