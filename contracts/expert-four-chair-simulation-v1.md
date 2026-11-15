# Four-seat offline chair simulation v1 (research only)

Separate from the existing two-role protocol; no replay/schema/permission changes.
FourChair uses the existing four-role Ledger, packet pin and two-round role order:
regulations (法规), navigation (通航), investigation (事故调查), vessel (船舶).
海青君 is a software chair protocol name, not an authenticated human or model.
Each ticket includes its role scope, fixed public packet, UUID and context digest.
First-round tickets contain no other opinions. Second-round tickets contain all
four first-round opinions and none of the current round. The caller explicitly
supplies simulated reviews, validated for schema, coverage and literal quote match.
This does not verify semantic correctness, independence of actual people/models,
or whether a simulator really read the context. Opinions retain rationale,
uncertainty, quotation and role; summary indexes labels and missing roles, never
votes facts true or suppresses disagreement. No additional arbitrary source input.

Ledger reservation commits before ticket return, settlement before in-memory
acceptance. One active turn, eight accepted opinions maximum, one reservation
per issued turn; underlying ledger retains per-role/round2 and total16 bounds.
No refund, automatic retry, tool execution, provider or external dispatch exists.
Malformed output leaves the turn pending for explicit correction or stop; this
is not a new model call. Pending stop/failure is recorded unknown conservatively.
600-second cooperative deadline is checked at boundaries, not a hard watchdog.
Database errors permanently block the instance with persistence_unknown, not a
safe retry or success claim. Unknown commit is never automatically retried.
A fresh exclusive file is required; existing files and crash leftovers are not
reused/deleted. SQLite metadata persists, opinions/context/summary do NOT persist.
There is no resume, full meeting audit recovery, cross-meeting quota or lease.
Inspection of declarations cannot establish real execution or current ownership.
Local files/callers are not authenticated. File retention is the operator's duty.

The packet has three manually authored test claims (including counterexamples)
from the same public YANGZE 22 report page, not three independent sources. Exact
URL, PDF hash and PDF28/printed26 mapping are inherited from the pinned packet;
this task neither downloads nor independently verifies the PDF. No private data.
Token/cost budget, trusted identity/approval, managed Pi/DeepSeek bootstrap and
real process cancellation remain absent. Real four-expert execution remains HOLD.
The code has no production endpoint/UI; no browser or real-model acceptance.
