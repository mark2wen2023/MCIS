# W8 package ZIP decoder boundary

Base: main d695134ba74d1c3cf79f802eeaaf6b8f697f85fc. Isolated from W8.2 create-case UI.

## Scope and compatibility

The existing `/api/v1/packages:verify` and `/api/v1/cases:import` share `read_zip`.
This slice preserves route schemas, valid ZIP content bytes, Unity backslash path normalization, stored/deflate/bzip2/lzma support, and ordinary export/import round trips.

Return existing HTTP 422 `BAD_PACKAGE` for corrupt CRC/header/compression, encrypted or unsupported compression, and unsafe or ambiguous member names. Do not expose parser exception text or member paths. Reject all paths containing empty/dot/parent segments, leading slash, NUL or colon (Windows drive/alternate-stream ambiguity), including directory entries. Reject duplicate normalized names and case-insensitive aliases, even identical content, and exact file/directory collisions, including any file occupying the ancestor of another member (case-insensitively and independent of entry order). Validate the full member inventory before decoding file content. Close archive handles on success and failure. No filesystem extraction.

Compatibility change: archives relying on duplicate overwrite, case-insensitive collisions, redundant path segments or Windows-invalid names are now rejected instead of silently choosing bytes or failing later. Exporter-created archives and ordinary Unity ZIP packages do not use these forms. This is intentionally narrower than semantic validation of manifest or imported document data.

## Acceptance

- Exercise both HTTP endpoints with synthetic invalid ZIPs; 422 and no imported cases.
- Cover corrupt CRC, encryption, unsupported compression, truncated ZIP, NUL and non-ZIP data.
- Cover duplicate exact/normalized/case aliases, directory traversal and Windows-invalid names.
- Keep valid Unicode filenames, backslash normalization, four supported compression modes and all existing package tests green.
- Independent tests and review must be produced outside the implementation session.

## Explicit limits

Not a complete `.mcase` security hardening. No upload/compressed/uncompressed size or entry-count budget; large VDR payload policy remains undefined. No fix to malformed JSON/schema/manifests, trust/authentication, case ID validation, semantic cross-document consistency, atomic filesystem writes, or symlink policy. ZIP identity is not an authenticity/signature guarantee. No deployment or claim of production readiness.
