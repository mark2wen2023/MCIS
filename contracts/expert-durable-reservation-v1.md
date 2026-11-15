# Offline four-expert reservation candidate v1

Implementation/limits: research/expert_budget/README.md and ledger.py. Separate research
profile only; does not alter main's two-role meeting, its snapshots, Pi transports or
permission/credential holds. Exact packet SHA must equal expert_group.packet.PACKET_SHA256.

Meeting and attempt IDs are canonical UUID strings, not identities or approvals. Four
roles regulations/navigation/investigation/vessel derive from the prior expert panel
proposal. Two rounds,2 attempts per role/round,16 total are immutable in profile v1.
Only an approved future controller may bind intents/meetings/requests; no controller
or execution API is implemented by this change.

New reservation transaction: BEGIN IMMEDIATE, check persisted meeting/binding/stopped/
pending/round/counters, insert one immutable attempt identity, COMMIT, return metadata.
Duplicate same ID is lookup, not repeat dispatch. Unresolved requests block new ones
across Ledger objects/restarts. Invalid requests do not consume budget. Once reserved,
failed/not-dispatched/unknown attempts are never refunded. Outcome can move reserved to
one terminal declaration only; repeated equal declaration is metadata lookup, changed
terminal declaration refused. Stop is sticky and pending becomes unknown.

Every output retains executionAuthorized=false and no real-execution proof. Settlement
is caller-declared, not authenticated model completion. No credentials or input/output
model text stored. No socket/process/environment reads. No monetary/token/tool/time
budget, hard cancellation, production authorization, platform bootstrap or actual
provider request is implemented. Existing production refusal is unchanged. Exception
rollback before commit is tested; uncertain commit must not be automatically retried.
Future trusted reconciliation and execution integration require independent review.
