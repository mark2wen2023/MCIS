# Legacy dual-field expected checksum (new contract)

Before this change contentBase64 took precedence and sha256 was ignored when both were
provided. OpenAPI only required SHA without content; it did not promise dual-input checking.
New behavior: strict canonical Base64 first; provided nonnull SHA must match
[0-9A-Fa-f]{64} exactly, then compare normalized lowercase SHA to decoded-byte SHA256.
Malformed expected SHA422 INVALID_SHA256; unequal SHA422 EXPECTED_SHA256_MISMATCH. Both
errors precede blob writes and evidence/custody/audit mutation. Do not echo input.
Content-only and SHA-only retain semantics; null SHA means omitted. Empty string content
is a real empty file requiring SHA256(empty) when supplied. Empty SHA is invalid in dual
mode. SHA-only remains a declaration without fabricated file or verified-origin claim.
Authorization runs first. JSON type errors remain framework422. No new size cap.

Known repository UI/demo clients use new Intake API. Matching dual-input callers remain
compatible; old mismatch/placeholder callers intentionally newly fail422. No production
telemetry or external caller survey is available. Neither checksum nor file integrity proves
trusted source, identity or production authorization; full write locks/memory remain.
