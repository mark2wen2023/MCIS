# Synthetic file-memory and concurrency study, plus minimal existing-limit optimization

Base390fd59dce1bf816c52b0edc6c26bf7f381afd80, local/file-memory-budget at
/workspace/mcis-file-memory-budget. No commit, push, deployment or merge. No private case,
production system or model call. This is not production performance/capacity validation.

## Method and actual baseline observations

run.sh launches fresh Python processes for each mode; measure.py uses deterministic synthetic
bytes, temporary files/SQLite and real application routes via TestClient. Direct-reader modes
isolate descriptor reading; API modes include in-process TestClient response capture/copies.
tracemalloc peak measures Python allocations during the operation, not whole process memory.
Linux ru_maxrss is process high-water RSS, affected by earlier imports/setup: rss_peak_before
and rss_before are included. Function-local response/raw references are released by function
return; TestClient/loop references may still retain some allocations and no post-operation
GC is forced. python_current/rss_after are NOT a steady-state retained-body measure. No latency
percentile, cold cache or repeatability distribution is claimed (one sample per configuration).
Temporary source bytes are generated before measurement, no large Base64 request confound.
Linux cgroup ceiling observed16GiB with other shared processes; not a per-service budget.

Raw records:baseline.jsonl, stderr warnings:baseline-stderr.txt, derived table:summary.csv.
- Direct64MiB read:Python allocation peak128.008MiB; process RSS peak142.141MiB.
- Actual GET64MiB via in-process TestClient:200; Python peak128.564MiB; RSS91.211MiB before,
  220.746MiB process peak. This is not isolated production server RSS.
- Export4x16MiB synthetic largely incompressible sources:200, ZIP67,135,433 bytes;
  Python peak167.198MiB; RSS277.008MiB process peak. No current aggregate refusal observed.
- Four concurrent16MiB GETs:all200,0 completed while first reader held, no admission refusal;
  Python peak82.418MiB during combined capture. Deliberate hold/fault hooks make timings
  unsuitable as normal latency benchmarks. Policy PUT while reserved reader held returns
  503/not_committed, then after release PUT200 and next GET403. No lock shortening.
- Existing8MiB bounded reader on32MiB source rejects, but allocated16,778,700 Python bytes
  before rejection (chunks plus join). This motivates only the narrow optimization below.

Source inspection:legacy evidence.safe_content passes sys.maxsize, so no practical file
budget. Chunk size1MiB is not a total-memory cap. Whole legacy export retains each file in
files[] then ZIP/response bytes. Intake8MiB and history16MiB are per-reader limits, not shared
aggregate or server-wide caps. WRITE_LOCK serializes body preparation, not full response
lifetime or global worker memory; lack of admission limit must not be claimed safe.

## Implemented narrow optimization

common/safe_files.py now checks pinned descriptor fstat regular-file size against the existing
caller limit before body reading. It retains bounded reads/growth detection and rejects
limit+1 overflow before join. FDs still close on all paths, no following symlinks, no locks or
permission gates changed. A concurrently shrinking oversized file may now be conservatively
rejected earlier; stat does not prove bytes immutable and recorded digest checks remain.
No new endpoint file limit, aggregate budget, semaphore, streaming or low-lock change.

Reproduced baseline new regression:1 failed,11 passed; oversized test proves prior code read
body before rejection. Same32MiB source/8MiB limit after patch:ReadBudgetExceeded with Python
peak1724 bytes,0.0002s; before16,778,700 bytes/0.0095s. One isolated sample, not an SLA.
preflight-after.jsonl retains all metrics. Accepted-read allocation behavior is unchanged.

Actual focused regression:235 passed,1 existing missing-.NET skip in39.00s (regression.txt).
Includes early refusal/FD close, growth after stat, empty/exact limits, invalid budget types,
parent replacement, descriptor safety, digest mutation, policy/concurrent revocation and
container guards. Previous full622passed/5baselinefail/2.NETskip is historical, not rerun
by this narrower235-case set and not implied repaired. New product hash is frozen.

Existing error mappings remain:history reader413 ARCHIVE_BUDGET; intake receipt oversized
local original409 INTAKE_INTEGRITY; unsupported descriptor platform503. This patch does
not change these codes or claim a new legacy413 route. No successful delivery/Access is
introduced on failure. Future admission-only503 must be distinct from uncertain commit errors.

## Explicit remaining budget design

BUDGET-DESIGN.md proposes (not implements) one nonblocking full-delivery slot held through
ASGI send/disconnect, explicit per-file/aggregate/metadata/member/output limits and pre-write
failure semantics. New caps may reject formerly valid legacy files; require explicit
compatibility contract and independent tests. Eager metadata/ZIP construction and worker-wide
accounting must be resolved before promising aggregate memory limits. Payload budgets cannot
be equated to hard RSS bounds. Never release the authorization writer early for performance.

Real authentication/SSO, spoofable role headers, source authenticity, full write locks and
aggregate memory remain unresolved. Offline future-revocation and missing-digest policies
are unchanged. This is limited safety/performance research and an error-path improvement.

## Independent final evidence

19 passed in1.79s:2 TCP/controlled-response experiments,5 independent budget tests and12
implementation tests (overlap, not additive to235). Real loopback four-request probe confirms
all four reach ASGI, first held reader admits no other body read (max_active_reads=1), all
four eventually200, concurrent policy reservation503 without policy.update audit, then
successful revoke and next GET403. This is queueing, not concurrency rejection.
Controlled ASGI send pause separately proves committed authorized response body can remain
live after read transaction releases: another GET and SQLite writer/policy update succeed;
the already-authorized response eventually sends200, later new request403. This documents
current read/authorization linearization before subsequent revocation, not unauthorized
post-revoke new read. It is NOT a real slow-client RSS benchmark, nor proof all active
response memory is bounded by WRITE_LOCK. Keep the same authorization ordering.
Independent tests verify existing HTTP error mappings and no successful audit/body read for
oversized existing-cap paths. See tests_acceptance/file-memory-independent and independent
DEFECTS report for exact probes and frozen hash check.
