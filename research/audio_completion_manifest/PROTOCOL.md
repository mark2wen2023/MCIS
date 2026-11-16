# Proposed new-task completion manifest v1

Base d1eb654b7c3ef8c0fb43ec07c4deb9ebfec4ac09. Pure isolated research only; no product wiring or persistent writes. The representation preserves per-member size/digest plus case/task/generation/audit bindings. This does not yet save a real completion record.

## Required future producer protocol (not implemented)
1. Before dispatch, commit a unique generation identity and protocol version bound to case/task and original registration. Legacy tasks cannot be upgraded from current observations.
2. Preserve source, raw results, worker output and all HOME entries. A closed inventory includes empty directories; do not classify members as disposable based on names. Unknown types/ownership or incomplete inventory hold the task.
3. Observe successful worker exit AND establish that every writer has stopped. Direct-child exit alone is insufficient; no such ownership/closure proof is implemented here. Capture complete bounded member inventory and byte digests only after closure. Canonical raw-result digest and physical raw.json digest remain distinct.
4. Persist the manifest with an immutable completion audit ID, task/generation linkage and manifest digest in the same final database transaction. The completion audit must reference that digest; no circular digest construction. Preserve files before that transaction, with a durable publication protocol still to be designed/proven.
5. Unknown commit leaves an unresolved operation. Read-only reconciliation by operation identity may later establish a confirmed result, but no blind dispatch, deletion or commit retry. Missing or changed files still block. Transaction result/identity must come from trusted server records, never client declarations.

## Pure validator
`inspect(manifest, context)` checks exact versioned keys, task/case/generation/audit linkage, successful exit, confirmed writer closure and commit, complete declared membership, sizes, hashes, directory ancestry, and canonical manifest digest. Context membership must match exactly (including order); caller must produce deterministic ordering. All values are merely supplied claims. `consistent_claims=true` is not observed provenance, a filesystem snapshot, valid authorization or historical proof.

Directory sizes use zero as a schema marker, not an OS directory byte count; directories have null digest and explicit child entries. Empty log files can be represented. Unsupported members/types are rejected, never discarded. Bounds in this research schema are not a production I/O or memory budget.

Historical tasks without a generation-time record remain blocked. Rehashing a current directory cannot create that historical record. Raw transcripts, diagnostic logs and HOME content may be sensitive; this contract does not authorize their reading/export. Existing permissions and formal archive refusal remain unchanged. No actual files, databases, processes or model were inspected by the pure validator.

## Outstanding implementation prerequisites
Trusted producer/transaction adapter; audit uniqueness/existence verification; source-registration/result linkage with existing adapter; writer closure proof; filesystem publication/durability and restart reconciliation; content preservation and access policies for log/HOME. Actual concurrency, crash, browser and production identity unverified. All action flags remain false even for consistent claims.
