# Restored attachment download basename

Historical evidence content retains application/octet-stream, no-store, hash verification,
and an Access audit committed before delivery. After full current authorization and byte
verification, rebuild the archived evidence-intake binding with the existing validator;
require exact canonical binding/request digest, case, evidence ID, source SHA and byte size.
Invalid stored metadata fails409 ARCHIVE_HISTORY_INTEGRITY before an Access event.

Response Content-Disposition is `attachment; filename="historical-source.bin"; filename*=UTF-8''<percent-encoded-original-basename>`.
The original Unicode filename comes only from the validated historical registration;
never from a query parameter, current title or inferred media type. Percent encode quotes,
newlines cannot pass intake validation, and no directory/colon/backslash is accepted.
The name is a user-supplied historical declaration, not a verified author identity/content type.
The browser keeps the file opaque and only sets a download filename. It never executes it.

Web transport accepts this exact extended profile and decodes/validates the basename;
malformed/ambiguous extended headers reject before saving. Old responses without filename*
retain the existing historical-<evidenceId>.bin fallback. SHA, size budget, session invalidation
and cache checks remain mandatory. UI says download initiated, not confirmed disk save.

Existing explicitly registered PDF/DOCX/ZIP report attachments roundtrip with their name
and exact bytes. Generated report-output bundles remain client-download-only unless an
investigator separately registers a file copy. No automatic server retention, reportId link,
file signature validation, new HTTP route or .mcase version is introduced.
