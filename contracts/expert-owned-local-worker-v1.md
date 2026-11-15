# Owned fixed local worker / ledger research contract

Actual local Python fixture processes, not model/Pi execution. Fresh exclusive
SQLite recording, existing Ledger four role/per-round/total counters reused only
for local fixture attempts. Never mix this ledger with live model reservations.
One active run per instance; no auto-retry, resume, file deletion or cross-meeting
quota. No arbitrary executable, payload, environment or working directory inputs.
Only pinned fixture modes ok/fail/wait, isolated Python -I, minimal LANG environment,
DEVNULL input/stderr and bounded stdout. This is not an OS/network security sandbox:
the fixed fixture has no network code, but a compromised host is out of scope.
Source checkout/interpreter and exclusive host ownership are trusted prerequisites;
the fixture hash is not an atomic immutable executable guarantee against local edits.

Existing ownership.py from498f807 is copied byte-for-byte with complete standard
library dependencies. It requires POSIX waitid/WNOWAIT, stable SIGCHLD=SIG_DFL and
an exclusive reaper throughout the check/kill interval. Host cannot enforce other
threads never reap the child. No poll/wait/communicate competes with waitid.
No changes to signals/security configuration; unsupported hosts fail closed.

Reservation commits before Popen. Absolute monotonic deadline precedes spawn;
expiry/stop checks are cooperative, not real-time. Cleanup uses original bounded
5s reap path; total elapsed can exceed requested timeout. Actual PID, exit and
leader-reap observations recorded; never claim all descendants terminated.
Cancellation returns only a stop request. Result token plus zero exit and completed
cleanup is required for completed_local_fixture. Late/failed/unknown results stop
and consume budget. SQL exception blocks without another write/retry; actual commit
may have happened. A cancellation arriving during successful settlement yields
stopped_after_local_completion, retains that completed ledger declaration and blocks
new work. Cancellation after returned completion cannot undo a finished run.
Unknown cleanup retains the Popen reference and does not signal/reap again automatically.
Process cleanup after crash/interpreter exit is not guaranteed. Receipts are volatile,
not authenticated crash-recovery evidence. Ledger persists attempt metadata only.

No real provider, credential, public case transmission, model response validation,
Pi integration, hard cancellation guarantee, identity or money/token budget.
Real four-expert execution remains HOLD. No production interface or permission change.
