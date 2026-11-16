# Revision-4 single-seat message adapter — developer evidence

Parent 8bc35418bfc3d55ab0dbd6f90693cb195b6bfa59.
Branch candidate/single-seat-messages-v4. Isolated new adapter only; old host and
message adapter unchanged. No dual write, process, provider, transport or resume.

SingleSeatMessages uses SingleSeatTranscriptLedger exclusively. Context commits
before initialization succeeds. Model requests reserve through that ledger; replies
use the existing assistant normalizer and revision-4 canonical digest. Tool results
are returned from the transaction's recorded result, not recalculated by the adapter.
Response output is read back from the persisted transcript; read failure blocks.
Duplicate results return no historical tool output or new permission. Every exception
blocks this owner; no compensating write or automatic retry. A done message only
blocks with accepted=false/lifecycle_unverified; it does not prove valid completion.

Raw framing remains strict UTF-8 single-line JSON, <=262144 bytes. The normalized
full action envelope must also fit <=4096 ASCII-serialized characters. Chinese
escapes count toward this limit. No truncation or chunking; oversized actions fail
before ledger.apply. Existing normalization is semantic, not raw byte preservation.
Budget remains 2 requests per seat/round and 16 total, <=128 operations; only the
first regulations seat is available. Third request records partial completion.
All outputs prohibit dispatch. Candidate validation never completes a role.

Developer run: 6 passed in 0.15s, no skips. Exact explicit nodes in COMMAND.txt.
All six new nodes were read before execution. Ordinary synthetic messages and
temporary SQLite, with existing public textual packet. Size rejection tests call
pure helpers only. Unknown-result test replaces apply with a pure exception stub;
it attempts no database write and is NOT a real uncertain-commit/crash test.
No paused tests, write-refusal probes, processes, Pi, model, browser or full suite.

Not validated: independent acceptance, real commit failure/crash/concurrent owners,
four-seat orchestration, lifecycle/ownership integration, provider or production.
Old record inspection retains unknown missing transcript; no migration/backfill.
No credentials, media or databases are included. HOLD remains; no push this turn.
