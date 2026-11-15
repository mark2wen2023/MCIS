# Request-level durable budget candidate (offline)

Separate SQLite schema; never open an existing worker/old ledger DB as this schema.
No transport/worker/credential/API is invoked. Only packet pin, canonical meeting
and ticket UUIDs, four role IDs, round1/2, context SHA256, request IDs and receipt
SHA256 declarations are stored. No source text, opinion, prompt or credentials.
A ticket binds immutably to meeting/role/round/context; one ticket per role/round.
Request IDs use historical Bridge's ticket:model:N form, sequential N starting1.
Each NEW request consumes one reservation, not each worker or expert turn.

Keep existing per-role/round2 and meeting16 limits; no hidden increase to4/32.
Exhaustion persists partial_budget_exhausted, rejects new reservations, retains
accepted unverified receipts and counts. It never says the meeting completed.
Second round requires each first-round role to have a received declaration;
this remains only a necessary ledger condition, not protocol/opinion completion.
No earlier-round request after later-round reservations. One pending request per
meeting. The future trusted controller must separately enforce completed opinions.

BEGIN IMMEDIATE and SQLite COMMIT precede newReservation=true. This is internal
accounting metadata, NOT an execution permit; dispatchAuthorized stays false.
Exact duplicate returns existing_no_redispatch/newReservation=false, including
on reopen. A reserved row after restart is pendingOutcomeUnknown and blocks new
requests; no resume or retry authority is issued. Ticket/context/cross-meeting
receipt mismatches reject. Exact receipt repeats are read-like; changed receipts
reject. Receipt digest is caller-declared, not provider authenticity/execution proof.
Unknown/not_dispatched stops the session without refunds; stop makes pending
unknown and rejects late success. No token/cost/cross-meeting allowance introduced.

SQL errors conservatively block mutation in the same instance. Commit errors are
uncertain, never a safe automatic retry signal. Read-only-purpose snapshot can
inspect recorded rows, but it does use a SQLite transaction. Reopening is not a
trusted dispatch ownership capability and must not be wired as one. Missing rows
after an unknown result do not authorize an automatic retry by the future caller.
Local trusted DB/host assumed; no adversarial local tamper/identity guarantee.

Still missing before real wiring: authenticated intent/config binding; an actual
Pi Bridge adapter mapping issued ticket and every canonical model request to this
ledger before transport; non-replayable dispatch owner; trusted response digest
production; coupling reply to opinion validation and owned worker cleanup; durable
cross-process reconciliation. Do not mark existing simulated FourChair tickets as
real requests or bypass raw-key/managed HOLD. Budget2 may intentionally stop a Pi
turn needing3–4 calls; no complete-meeting feasibility claim.
