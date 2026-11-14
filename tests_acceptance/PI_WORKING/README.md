# Pi accepted proposal → working history trial

New explicitly constructed `PiWorkingHost` owns a single `RemoteTranscriptHost`,
source binding and host-observed protocol trace. Only successfully completed
strict final delivery enables `save(operation_id)`. Callers cannot pass source,
session, proposals, trace or provider mode into save. Returned objects are copies.
The model-facing dispatcher has no save or review tool; trusted host calls save.

Existing SQLite working transaction rechecks session/case incarnation, read
policy, unchanged source binding and separate WorkingGrant, validates original
proposal/citations again inside the write transaction, then final authority
recheck. Immutable WorkingProposal and append-only WorkingReview are reused.
Stored providerMode remains remote-deepseek, no fixture/local masquerading.
The trace includes protocol operation/tool names and outcome labels only, not
keys, tokens, model/source payloads or reasoning. It is observed host metadata,
not a cryptographic signature or proof of official Pi runtime identity.

Saved working state is not a verified fact: factActivated=false. Later reads,
list and human review use existing authorized working-store functions; original
proposals remain unchanged. Same host/same operation retry returns saved result;
a new run does not silently reuse an old operation. Source/session revocation
blocks save/read as appropriate. No auto initialization/grants, routes or defaults.

Limits: backend trusted callable only. Existing frontend/provider receipt and
archive formats do not understand Pi result metadata. Export of such a case
currently fails closed; do not claim archive/UI support or production readiness.
A host process lost before save needs a new explicit run; saved proposal IDs may
be discovered through authorized listing, but no automatic remote retry occurs.
Real public-report accepted result is earlier separate read-only evidence; new
persistence tests use simulated provider responses against actual temporary SQLite.

## Verification
Independent reviewer: primary5 + independent10 =15/15 passed, zero skipped,
61.84s. Real temporary SQLite, mocked DeepSeek transport, no external request.
Includes returned-result mutation isolation, idempotent single write, cross-run
operation conflict, revoked session/write grant, changed source, final-transaction
failure rollback, unvalidated final denial, closed-host denial, cross-session
consent-digest rejection and legacy whole-case supplemental export fail-closed.
Related remote/working regression85/85 passed,33.83s; separate working-review,
archive and persistent-RPC regression87/87 passed,157.89s. Counts overlap other
published suites and should not be added as new unique test coverage. Existing
Starlette deprecation only. No CI or real Pi→persistent working-record live test
was performed; earlier real public-report inference remained read-only.
