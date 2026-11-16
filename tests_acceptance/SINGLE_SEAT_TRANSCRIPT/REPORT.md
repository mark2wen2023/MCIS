# Single-seat transcript — developer evidence, not independent acceptance

Parent: 420284ab5fd44c94b737f8c1cf51bc0ef09aea29.
Branch: candidate/single-seat-transcript. No push authorized in this turn.

Revision 4 shares the existing new-file-only SQLite transaction implementation:
operation, audit and current state commit together. Context, normalized synthetic
assistant body, receipt digest, ordered calls/results and unverified candidate
are retained in that source. No second ledger. Normalization uses the existing
assistant validator; non-normalized bodies are rejected rather than silently dropped.
Read-only replay regenerates tool results using the pinned public packet and
compares recorded state/audit. It requires that packet to remain available.
Hashes are consistency checks, not independent authenticity or human-read proof.

Limits: existing 4096 ASCII-serialized characters per action, 128 operations,
2 model requests per seat/round, 16 overall retained; this candidate permits only
first-round regulations. Tool count <=8; output <=262144 bytes including newline;
review fields <=2000 characters; candidate <=4096 serialized characters. No chunking.
Large otherwise valid responses can be refused by the stricter action limit.
No completion operation: candidate validation does not complete a role.
Third request preserves candidate and records partial_budget_exhausted.
Duplicate operation results never grant dispatch. Pending/unknown blocks; read-only
reopen always prohibits dispatch/resume. Versions 2/3 retain their reducers and
report transcriptCoverage=unknown_legacy; no backfill/migration.

Shared ledger change: configurable revision/reducer and revision-4 read-only
replay; GroupError during packet validation is reported as blocked_unverified.
Existing Pi message adapter/host are not switched to this ledger yet.

Final developer run: 7 passed in 0.13s, zero skips. Earlier runs 5 + 2 passed;
these overlap the final seven and must not be added. Only the explicit nodes in
COMMAND.txt were run. All new nodes were read before execution. Synthetic messages,
temporary SQLite and existing pinned public textual packet only; no recordings,
model, credentials, process, browser, write-refusal probes or paused tests.
Pure rejection checks call only the in-memory reducer, not a database write attempt.

Not verified: real crash/uncertain SQLite commit, concurrent owners, old-version
full regression, Pi/provider, process ownership integration, four-seat progress,
real model, browser or production identity. No product change/merge/deployment.
