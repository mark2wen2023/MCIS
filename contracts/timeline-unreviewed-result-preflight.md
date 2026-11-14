# Unreviewed result save: design gate and generation preflight

This slice does NOT implement saving, a public endpoint, durable receipts or approval.
An internal preflight accepts only the existing strict registered-preview request
(IDs, mappings and explicitly unverified declarations). It never accepts a caller
result, receipt, approval, incarnation or arbitrary payload.

Before calculation, reserve the SQLite writer, recheck existing source visibility
and timeline ReadWrite, capture the local case incarnation/epoch and each source
and parent-report incarnation, and resolve original registered bytes. Release the
transaction before invoking the existing server/core preview. In a fresh reserved
transaction, repeat the same checks and require exact equality of captured local
identities/versions and case epoch. Return only the server-generated result,
frozen request, identities and explicit not-assessed/persisted-false markers.
No audit, result or timeline rows are written. Declarations are not semantic proof.
A returned envelope cannot authorize a later write; future save must own the final
transaction and persist the validated server result there, without a roundtrip
through caller-supplied JSON. This preflight is deliberately not exposed to users.

## Required next design before actual persistence
- A bounded exact result envelope (including mapping, comparison and parent-report
  declarations, source snapshots, case identity, epoch, core/protocol version,
  timestamps, complete generated result, status and schema version).
- Atomic storage and audit with explicit outcome/replay semantics on delivery
  failure. No inference that identical request means identical compute output.
- Complete archive representation and parser validation. Restored results must be
  historical/unapproved, never reconstructed as local live authority from IDs.
- Read/list access, role revocation, review invalidation, replacement and concurrent
  source mutation tested in the actual save transaction.
- No schema/version silently allocated and no populated table whitelisted until
  complete preservation/restoration tests exist. No import of trusted result via
  generic AgentDraft JSON. Human approval is a separate future operation.

The current safety preflight solves case/source incarnation comparison across
server computation; it does not complete these remaining persistence requirements.

Implementation reuses captured initial bytes directly with the existing server
preview/core port, not a second client text submission. The returned internal JSON
envelope has a 2 MiB UTF-8 cap, finite JSON and explicit usableAsWriteCredential=false.
This is an engineering bound, not a complete future archive/save schema.

Output reference checking rejects foreign source IDs, conflict labels/evidence IDs,
self-source conflicts and duplicate conflict IDs. Fixed GNSS is allowed only as the
existing core's configured reference/via name, not as an additional acquired source.
This checks references, not observation-value factual correctness.

Local implementation tests:19 passed, zero skips when explicitly configured with
an already-built real W2 wrapper.18 tests use controlled core results for failure,
permission/race and boundary probes;1 executes the actual C# core on a fictional
registered CSV. Initial real-core attempt passed a multiword command to a
single-executable setting and failed503; corrected by an explicit local executable
wrapper, not by bypassing or mocking the real-core test.
