# First-round four-seat ledger — developer synthetic evidence

Parent: 82d168938500ab6bb4cb5d58acc77dc1b4d25df0.
New revision 5, fresh files only, shared transaction/audit/operation implementation.
Per-ticket transcripts isolate context, requests, response bodies, tool identifiers,
read flags, candidates and seal records. Reuses unchanged revision-4 reducer for
active-ticket message validation via a single-ticket projection; prior tickets are
preserved, not converted into completed_declared. Context contains fixed public
packet digest and explicit role scope; no same-round opinions or second round.

Seal is an explicit synthetic operation with candidateDigest, empty pending tools,
all requests received_unverified. It records sealed_simulated_unverified and
expertCompleted=false; never infers process exit or expert completion. The final
fourth seal records round_one_sealed_simulated_unverified, not a completed meeting.
Every result/reopen remains non-dispatchable. No adapter/host/runner is connected.

Limits retained: each seat <=2 requests; global ceiling16 explicitly checked.
Only four first-round seats are possible, so the actual maximum is8; reaching16
is not claimed tested. Third request stops with partial_budget_exhausted; prior
sealed records remain and unissued roles stay absent/not started. Actions <=4096
ASCII JSON characters, candidates <=4096, tool outputs <=262144 bytes with newline,
<=8 tools per seat, <=128 operations. No segmentation/limit increases.
Revision2/3/4 reducers unchanged; new fourSeatCoverage unknown_legacy for old files.
No migration/backfill. Read-only replay requires the pinned packet still available.

Developer result: 4 passed in0.26s, no skips; explicit nodes in COMMAND.txt.
Nodes read before running. Synthetic reviews with existing public textual packet;
temporary SQLite only. Rejection assertions call pure reducer, not DB write probes.
No paused/security/write-refusal/process/Pi/model/browser tests or broad suites.
Not independent acceptance, real crash/unknown commit/concurrency, real model,
identity or production validation. No second round, no resume authority, HOLD.
