# Actual local request handshake into RequestBudget (isolated)

Chain: pinned request_fixture.py child stdout REQUEST N → RequestWorker parses
strict bounded IPC → RequestBudget.reserve COMMIT → host stdin GRANT N → child
RESPONSE N → ticket/context/request-bound receipt digest settlement → DONE plus
actual zero exit and owned leader reap. No grant before committed new reservation;
duplicate/no reservation/unknown commit never grant. One worker startup is not one
model request. Fixed fixture has no network, model, source access or credentials.

Uses unchanged request ledger limits2 per role/round,16 total. Demonstrates only
first round/four roles, fixed two-request completion. A three-request fixture
stops partial_budget_exhausted, preserving earlier completed local roles and explicit
unfinished roles. Roles are complete only after DONE, zero exit, cleanup, no trailing
partial bytes and no elapsed deadline/stop. Settled request receipts alone do not
complete a role. Both role summary and process observations are volatile; SQLite
stores request declarations only. No restart/resume/history recovery guarantee.

Existing ownership.py is reused directly, not replaced by caller declarations.
Exclusive reaper/stable SIGCHLD prerequisites, bounded5s cleanup, PID race assumptions
and lack of whole-descendant termination proof remain. New supervisor accepts only
fixed modes/two-way protocol; old no-input LocalWorker cannot be directly reused as
a Pi/IPC runner. No arbitrary executable or input accepted; interpreter/checkout
trusted, hash check not an atomic hostile-local-filesystem defense. No OS sandbox
or hard-time guarantee; timeout is checked cooperatively around small bounded IO.

Request failure/unknown blocks subsequent roles. Pending requests become unknown
on ordinary stop; budget-exhausted state remains partial. SQL operation uncertainty
blocks without another write or retry. Persisted reservation with lost acknowledgement
can remain reserved/unknown, and is not permission to resend. Cancellation only
requests stopping; result observes leader cleanup, not external provider cancellation.

Actual implemented link is local fixed IPC→existing RequestBudget→SQLite and
existing ownership observer. Pi Bridge, real provider, FourChair opinions and
second-round protocol are NOT connected. Receipt hashes identify fixed synthetic
response bytes, not actual provider identity. No authentic human authorization,
credential binding, billing/token budget or model execution. HOLD remains.
