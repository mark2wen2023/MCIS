# Proposal: explicit expected checksum for legacy dual-field registration

Status: implemented by the isolated checksum follow-up on1759643; not part of the earlier
strict-Base64 patch. This document preserves the originally evaluated design. New contract rather
than an assertion about original behavior. OpenAPI at /cases/{case_id}/evidence currently
says sha256 is required without content; current content branch ignores a supplied sha256.

Recommended explicit rules:

- contentBase64 present, sha256 absent/null: strict decode, compute recorded digest as now.
- contentBase64 absent/null, sha256 provided: keep metadata-only registration; do not
  fabricate file bytes or claim the declared digest has been verified.
- both present: require SHA to be exactly 64 hexadecimal characters (accept upper/lower
  case and normalize for comparison). Compare to SHA256 of decoded bytes BEFORE blob
  writes, evidence insertion, custody or audit. Equal -> normal registration; mismatch
  ->422 EXPECTED_SHA256_MISMATCH; malformed digest ->422 INVALID_SHA256. No silent trim,
  no silent fallback to ignoring a provided value. Explicit empty content is a zero-byte
  file; its expected digest must be SHA256(empty). Explicit empty SHA is malformed.
- invalid Base64 remains422 before checksum comparison; preserve authorization before
  disclosing validation detail. Do not log or echo content or supplied digest.

Compatibility: canonical content-only, metadata-only and matching dual-field callers keep
working. Existing clients that send stale, placeholder or malformed sha256 alongside content
will newly fail422. This is deliberate new validation, not backward-compatible for all
old dual-input callers. Existing browser uses Intake but unobserved external legacy callers
cannot be ruled out. Publish API description/release note and enumerate test fixtures;
never retain an ignore-mismatch fallback or imply rollout clients are verified.

Before implementation: update OpenAPI description plus contract, REQUESTS, frozen hashes;
exercise actual HTTP tests for matching lowercase/uppercase, mismatch, invalid lengths and
characters, empty bytes, binary and larger bytes, content-only/SHA-only/missing inputs,
existing-path preservation and zero DB/custody/audit mutation on every rejection. This
proposal supplies consistency checking, NOT authenticated origin, signer verification,
strong identity or a solution for the inherited content-GET field-rule defect.
