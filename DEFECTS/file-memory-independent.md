# Independent review — file-memory study and existing-budget early rejection

2026-11-14. Isolated /workspace/mcis-file-memory-budget, base390fd59.
Reviewer inspected study scripts/current product paths and added independent tests/report.
No product edits, commit, push, merge or deployment. The two TCP/response experiments and
budget tests ran with frozen safe_files.py SHA256
75adb58fa18ecba04f164558b4b1dee180e14051fe98e74f5fdd83f8de48e4c7.
This includes the implementer's existing-budget preflight optimization; it is not a claim
that these tests ran before that patch. Frozen hash verified after final execution.

## Actual independent execution

From service/:

```sh
.venv/bin/python -m pytest -q --import-mode=importlib \
 ../tests_acceptance/file-memory-independent/test_tcp_queue.py \
 ../tests_acceptance/file-memory-independent/test_budget.py \
 tests/test_safe_read_budget_preflight.py
```

**19 passed in1.79s**, no skips:2 independent TCP/response experiments,5 independent budget
cases,12 implementation cases. final-results.txt is authoritative. Earlier1-case TCP and
17-case budget runs overlap and must not be added to19. Separate implementer235passed/
1.NETskip result was not rerun by reviewer.

### Four real TCP requests queue; no admission rejection

Temporary uvicorn127.0.0.1 listener with actual http.client requests. A controlled read hook
pauses the first GET. ASGI wrapper observes ALL FOUR requests arrived (not merely submitted
by a client executor). None completes before release; only one enters read_content.
While the reader holds the SQLite writer, actual policy PUT returns503 POLICY_WRITE_BUSY,
not_committed/retryable=true, with no policy.update audit. After release all four requests
return200 with exact synthetic bytes and max_active_reads=1. Later policy PUT200 persists
revocation; next GET403 does not open content. Server thread/socket are closed afterward.

This shows current serialization/queueing, not a concurrent delivery rejection or capacity
policy. Test-only100ms SQLite busy_timeout does not change production defaults. Synthetic
pause is not natural storage performance; elapsed pytest time is not a throughput benchmark.

### Response bytes can outlive read/database locks

Second real TCP test uses an EXPLICIT CONTROLLED ASGI send stall before body transmission.
First response retains a synthetic body in the send chain after its read and Access commit.
During that stall another connection acquires BEGIN IMMEDIATE, another GET completes200,
and policy PUT commits200. First already-authorized response still completes200 when send
is released; subsequent GET403. No retroactive revocation guarantee is claimed.

This is NOT measurement of actual slow-client buffering or RSS. It proves only that full
read serialization is not a bound on simultaneously live response bodies: WRITE_LOCK and
SQLite reservation end before ASGI send finishes. It models a backpressure boundary with
an instrumented send, not a production TCP congestion distribution.

### Existing bounded-reader optimization

Independent tests confirm:
-128MiB sparse regular file with1KiB caller limit raises ReadBudgetExceeded before ANY body
  read and closes the source fd.
-Growth after fstat with repeated1-byte short reads consumes exactly limit+1 then rejects
  and closes fd; initial stat is not trusted as an immutable-size guarantee.
-Directory input remains a regular-file error, not misclassified budget exhaustion.
-Actual intake oversized stored blob (>8MiB) retains409 INTAKE_INTEGRITY; actual restored
  historical blob (>16MiB) retains413 ARCHIVE_BUDGET. Target body reads are forbidden by
  instrumentation and neither failure adds successful audit/custody rows.

Implementation rerun covers zero/exact allowed boundaries and invalid limit inputs.
Conservative early refusal if a local file shrinks after initial stat is documented and
acceptable for existing-cap checking. No security or permission lock is shortened.

## Measurement audit

measure.py/run.sh use fresh processes per mode and report RSS before/after and process
high-water mark plus tracemalloc peak. The script records setup high-water mark separately;
ru_maxrss is NOT reset for the measured function. Imports, app initialization and prior
allocations may dominate it. tracemalloc does not cover all native/kernel/ASGI allocations.

API mode includes TestClient's in-process client capture/copies, unlike an independent
server-process RSS benchmark. Function results explicitly retain sizes/statuses rather than
Response objects. python_current/rss_after therefore are not a controlled steady-state
count of intentionally held response bytes: transient references, TestClient internals,
cycles, allocator retention and absence of post-operation GC can all affect them. Peak
records are useful observations, not a proven production memory envelope.

Study fixture repeats a generated1MiB block and bypasses registration to seed trusted test
metadata; it measures read/export behavior, not upload decoding/custody acquisition. Data
are synthetic. One trial per mode/size is not performance statistics or deployment sizing.

Reviewed parent-produced baseline.jsonl and preflight-after.jsonl:32MiB file under8MiB cap
has recorded Python peak16,778,700 bytes before and1,724 after, in those isolated samples.
Reviewer did not independently rerun the9 mode memory benchmark. This observation supports
reduced allocation on THAT already-over-budget path only; it does not show improved legal
large legacy GET/export memory or establish production-safe thresholds.

## Current budget boundaries and design prerequisites

legacy evidence.safe_content still passes sys.maxsize: no practical per-file cap. <=1MiB
read chunks do not bound accumulated chunks plus join/result. Whole package retains member
bytes, metadata and ZIP output; no aggregate accounting or admission limit exists. Responses
may remain live after read locks release, as independent send experiment shows.

The only product change rejects above EXISTING caller limits before reading and rejects
runtime overflow before append/join. It does not implement proposed64MiB legacy caps,
aggregate case limits, serialized metadata/member/output limits or a delivery slot.
BUDGET-DESIGN.md is a proposal, not enabled policy, and its numbers are not production data.

Any future slot must span read/build AND response lifetime. On disconnect/cancellation,
release must wait until synchronous worker/read/ZIP work truly terminates or finishes;
merely cancelling the awaiting task can leave a background thread consuming memory after
admission is reopened. Per-process admission also multiplies across workers. Bounded ZIP
sink/metadata iteration, accounting before allocation, precise rollback/unknown-commit
semantics and disconnect cleanup need separate implementation and tests. Preserve current
permission/digest/container gates and transaction ordering; do not equate memory control
with releasing authorization locks early.

## Bounded conclusion

No blocker found in the narrow existing-budget early-rejection optimization. The broader
legacy/aggregate/concurrent response memory problem remains open and explicitly unimplemented.
Header roles remain unverified identity; no SSO/source authenticity is claimed. No production
RSS, full-system, browser, .NET, multi-worker load or deployment acceptance established here.
