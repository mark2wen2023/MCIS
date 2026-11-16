# Four-seat messages — developer synthetic evidence

Parent f544e08f3ce7e0357737ed5066bd4644a4ef5a97.
Branch candidate/four-seat-messages. New isolated FourSeatMessages uses only
revision5 ledger; inherits framing/envelope/commit guard and read-only inspection
from SingleSeatMessages, without invoking its constructor or creating a v4 ledger.
Old adapters unchanged. No provider/runner/process, network, credential or resume.

Issue/seal are separate explicit synthetic host methods. Every model/tool/response
carries ticketId and requestId. Active ticket checked before message handling;
ledger validates request/tool associations. Per-ticket transcript selects responses
and committed tool outputs; no implicit reassignment to another seat. Repeated tool
IDs across seats remain isolated. Duplicate/exception blocks this owner. Error
stub does not demonstrate an actual uncertain SQLite commit. Late-seat test is an
ordinary protocol check before any ledger write attempt, not a write-refusal probe.

Seal requires explicit candidate digest and ledger preconditions; tools do not seal.
Done always returns accepted=false/lifecycle_unverified, never seals. Fourth seal
blocks further messages with recorded simulated-unverified status. No expert
completion, real lifecycle observation or execution authority is inferred.

Per seat2/global16 unchanged, first round max8; third request stops meeting while
retaining prior sealed and current incomplete records, later seats remain unissued.
Existing 262144-byte raw frame, 4096-character full action, 128-operation and tool
limits reused. No second round. Legacy inspection still prohibits dispatch.

Developer run: 5 passed in1.22s, zero skips; exact node command in COMMAND.txt.
All five new nodes reviewed before execution. Synthetic replies/public text packet,
temporary SQLite only. No paused/security/write-refusal/browser/process/Pi/model
or broad-suite tests. No independent acceptance, actual crash/uncertain commit,
concurrent ownership or production identity verification. HOLD remains.
