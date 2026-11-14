# Legacy POST evidence contentBase64 validation

When provided, contentBase64 must be canonical RFC4648 standard Base64: ASCII alphabet,
correct required padding, no whitespace or junk, and zero unused pad bits. Decode with
strict validation and require encode(decode(input)) == input. Invalid inputs produce
422 INVALID_BASE64 without reflecting input and before blob, evidence, custody or audit
writes. Schema-invalid nonstrings retain framework422. Existing authorization runs first.
Empty string explicitly means a real zero-byte file (SHA256 of empty bytes), preserving
legacy behavior. Missing/null content still uses the existing digest-only registration
path if sha256 supplied. Valid binary bytes are preserved exactly. No new file-size cap
is introduced; tests cover0,1,2,3,255,64KiB,1MiB,1MiB+1. JSON still buffers request data;
this repair does not claim bounded memory or production identity/source authentication.
