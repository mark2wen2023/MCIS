# Conflict archive member v1 — isolated candidate, not enabled

This contract defines only an offline JSON member (`conflicts/records.v1.json`),
validated by `working_records_archive.conflicts.parse`. It does **not** allocate or
enable a new outer `.mcase` version. Existing package1.0–1.4 export/import rules,
permissions and unsupported-state refusals are unchanged. There is no restore code.

## Inputs, preservation and limits

UTF-8 JSON, no duplicate keys, nonfinite numbers, unknown fields or alternative
encodings. Schema: `schemas/conflict-archive.schema.json`. `format` is
`MCIS-CONFLICT-ARCHIVE`; integer `version` is1. Mandatory caseId and1–256 records.
Each record preserves exact key/createdUtc/updatedUtc/doc/coverage/revisions. Parse
returns the original JSON values without defaults, normalization or rehashing.
16MiB member;4096 revisions total (also per-record cap);4096 evidence dependencies;
65536 lines and16MiB each for audit/custody inputs. Excess is refused, not truncated.
These are new offline parser budgets, not changes to existing live business limits.

Caller supplies case_id, complete same-case evidence documents, vessel ID set, and
complete original audit/custody raw line lists from the same package snapshot.
The function checks identity and the consumed associations, but does not authorize
access or replace the enclosing package's full parser. In particular custody register
metadata/path matching and original-file digest validation remain outer prerequisites.
No database/network access, case/source-file reads, writes or source-byte verification occur here. The existing contract loader may read checked-in JSON schema files.

## History checks

Closed revision fields include original actor declaration, UTC, action, audit sequence
and raw-line hash, before/after snapshots and source bindings, previous and own canonical
SHA256. Original journal format remains `MCIS-CONFLICT-REVISION-1`.
Revisions are contiguous from1; identity, coverage and exact preimages agree; terminal
after equals current doc. `conflict.update` can change only status/resolution;
`conflict.add` may create or replace. Audits must match raw line SHA, entity ID/type,
category, action, declared operator/role and UTC. Link sequences increase and cannot
be reused. Audit/custody raw line order/prev hashes and UTC timestamps are checked.
Linked later captured audits cannot silently disappear with a dropped last revision;
conflict audits cannot point to omitted current records.

`captured-from-creation` requires nonempty history and first before=null/add.
`unknown-before-capture` permits no history, or retained later history with unknown
prefix. The first beforeSources is null. Never fabricate earlier revisions, evidence
versions or authenticated identities. Coverage must remain explicit in future preview.
No hash authenticates the exporter: self-consistent forged data, a removed prefix
relabelled as unknown, or absent evidence of earlier capture cannot be distinguished
from genuine legacy records by this offline member alone. Future exporter must obtain
coverage and the full inventory from trusted server rows; import must retain provenance
without converting claimed history into new human verification. This parser is not
an authenticity or malicious-database-tampering guarantee.

## Sources and versions

Each observation's evidenceId must match its side binding and an included same-case
registration. Truly inline observations have null evidenceId, status unregistered,
bytesVerified=false. Unresolved nonnull references are refused; no implicit registration.
Registered bindings preserve sha256, registrationSha256, registryDocSha256 and nullable
custodyHeadSeq/custodyHeadSha256. Registration digest must match the evidence index.
A present anchor must match the exact custody line, correct evidence and version state
at that point. Null anchors require both fields null, no custody entries for that ID,
and the declared hash equal registration. Unchanged observations keep prior bindings.
Unknown first legacy source preimages stay null. Every bytesVerified must be false.

registryDocSha256 is a retained historical declaration whose preimage may be absent;
it is not proof of current registry equality or original file contents. The parser
explicitly does not reclassify a historical/current digest difference as tampering.
The member can describe multiple registered versions. The existing outer package
parser still rejects replaced-original history; successful member parsing does not
remove that restriction or prove all historical bytes are available.

## Failures and integration gate

All malformed/unsupported/inconsistent input raises ConflictArchiveInvalid(ValueError),
with no partial result or side effects. No HTTP status mapping is wired. Whole-package
validation, history-source permission checks, exact transactional restoration,
rollback/second-export tests and an explicit UI preview remain required before any
change to export refusal. Old packages must keep their existing contracts. Other
unsupported states remain rejected. No SSO, browser or production acceptance is implied.
