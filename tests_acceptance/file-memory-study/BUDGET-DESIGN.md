# Proposed delivery budgets — NOT enabled by this candidate

The implemented optimization only rejects files above existing caller limits earlier.
Legacy GET/export still use sys.maxsize; there is no new aggregate/admission policy in code.
Do not present the proposal below as a current guarantee or as production capacity sizing.

## Minimal next contract to evaluate

Use one explicit per-process full-content delivery slot shared by legacy GET, intake/history
content routes and whole-case export. Acquire nonblocking before waiting on WRITE_LOCK;
release only after final ASGI body send, disconnect, or error cleanup, not at function return
or database commit. A disconnect/cancel signal alone is NOT enough: a synchronous worker
may still be reading/building a ZIP after its awaiting task is cancelled. Retain the lease
until worker completion/termination and all owned body buffers are released; uncertain
worker outcome must not return capacity early. Test this explicitly with an in-flight
thread, including disconnect during DB work and preparation. Generic503 DELIVERY_BUSY would mean this request was not admitted:
no DB transaction, body read or successful audit began, so not_committed is known. This
is admission control, NOT the existing SQLite contention error. Do not reclassify unknown
commit/send outcomes or automatically retry. Authorization remains mandatory inside the
unchanged reserved transaction for admitted requests. A busy refusal may precede route
policy checking but must not reveal resource/case existence; this ordering is a NEW contract
requiring tests, not an authorization bypass. Keep ordinary policy operations outside this
slot so revocation can attempt its normal transaction. Never release the writer early to
improve performance. No waiting queue for full-content delivery requests in this policy.

Candidate logical limits for isolated follow-up:64MiB per legacy source,64MiB total retained
raw payload across an export,4MiB serialized metadata,4096 members, and68MiB compressed
output cap. Existing tighter8MiB intake/16MiB history limits stay tighter. These are explicit
engineering proposal values, not measured safe production defaults. Do not silently truncate,
omit a member, relax checks or create a partial backup. File/request budget rejection should
be413 DELIVERY_BYTE_LIMIT or PACKAGE_BYTE_LIMIT with no successful Access/export audit and
confirmed rollback; disclose no path or payload. A database/commit failure with unknown outcome
must stay unknown, not be labelled safe-to-retry. Incoming uploads are a separate budget issue.

To enforce aggregate limits before allocation, all builders must consume a shared byte
accountant (not independent per-file caps), check pinned descriptor size before read, retain
read-time growth checks, account data before storing it in files[], and bound serialization
and ZIP writes. Current eager metadata list_docs/all() cannot support a hard preallocation
claim: bounded iteration/count and incremental bounded serialization or validated staging
is required first. ZIP output needs a bounded sink, not a len() check after getvalue().
Response slot must also cover in-flight body bytes after the DB transaction ends. Failure
must unwind reservations exactly once. This is why a tiny semaphore around read_content()
or fstat alone is NOT a complete concurrent memory fix.

Only logical payload accounting can be promised here. Python object overhead, chunks/join,
ZIP scratch, ASGI buffers, incoming request bodies, other endpoints, DB caching and allocator
retention mean these byte limits are NOT a hard RSS limit. Need independent subprocess
server RSS measurements, slow send/disconnect/error and multi-worker tests before publishing
an RSS envelope. Per-process admission multiplies by worker count; deployment-wide budgets
need a shared coordinator or a verified single-worker constraint, neither exists here.

## Compatibility and minimum acceptance

New64MiB and aggregate limits intentionally refuse some currently accepted legacy files/
backups. Existing API compatibility must be disclosed; do not enable by stealth. No usage
telemetry or stakeholder file-size distribution is available. Stage next changes independently.
Tests must cover exact limits and+1, growth after stat, symlink races, concurrent admission,
revocation ordering, rollback and unknown commit results, metadata/ZIP expansion, byte-identical
allowed response, disconnect/slow send cancellation, and release/leak behavior across workers.
Keep the current complete SQLite transaction and all policy/digest/container gates unchanged.

Lowest-risk current action: retain existing-cap preflight improvement and measured evidence;
do not claim the remaining legacy/aggregate problem solved or enable arbitrary production caps.
