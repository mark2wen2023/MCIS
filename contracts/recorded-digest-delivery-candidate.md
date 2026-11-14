# Local candidate: recorded digest match before delivery

Depends on ee6071f. GET obtains SQLite writer reservation before loading policy/item/events;
legacy export already reserves its transaction. Delivery verifies the same immutable bytes
returned or inserted into ZIP, not a second read. Original digest must be64hex; Register
rows must agree; Change events must have valid previous/current digests and chain from the
recorded original. Change means current recorded version, not original bytes. Verify/Access
cannot redefine expected digest. Missing/malformed409 EVIDENCE_DIGEST_UNAVAILABLE;
conflicts409 EVIDENCE_DIGEST_CONFLICT; byte mismatch409 EVIDENCE_CONTENT_MISMATCH.
Failures have no success Access/export audit. Metadata-only missing content retains404/omit
when recorded digest is valid; invalid digest rejects even when local file is missing.

Trust assumption: attacker may modify local blob inode but cannot modify trusted SQLite
records/process. This is NOT a digital signature/provenance guarantee. Registration with
bytes computes SHA256; digest-only registration and imports accept externally supplied values.
Existing records cannot distinguish these origins. No claim of service-observed original
content is made for every record; only consistency with recorded current digest.

SHA256 collision resistance is assumed. Reads may observe mixed concurrent bytes, but no
bytes are delivered unless the final memory snapshot matches the pinned digest. Mutation
after read cannot change immutable bytes. No filesystem immutability, aggregate memory
bound, writer protection, all-endpoint integration or deployment readiness is claimed.

Legacy migration proposal (not executed): retain metadata/custody history and the original
file, mark the record as requiring manual integrity review. Recover an absent digest only
from a separately trusted original or existing independently verified record/package,
with provenance and approval audit. Do not silently backfill from current mutable disk
bytes. If no such anchor exists, keep delivery blocked; a future explicit unverified-copy
workflow would need a separate contract and clear labeling. No provenance migration can
be inferred from existing sha256 alone. Declared/imported64hex records remain usable under
trusted-record assumptions, but must not be labeled service-observed or authentic originals.
Access SHA must equal verified delivery SHA/current recorded version; mismatch produces no
successful Access or export audit. This does not repair prior misleading audit rows.

This local candidate supersedes the earlier legacy-descriptor-read contract's preservation
of delivery without expected-digest enforcement. SQLite writer reservation spans reading;
large-file/multiple-worker contention is an unmeasured operational cost, not a free guarantee.
