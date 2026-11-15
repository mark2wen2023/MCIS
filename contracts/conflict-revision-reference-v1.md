# MCIS conflict revision reference v1

A reference has exactly format=MCIS-CONFLICT-REFERENCE-1, caseId, conflictId,
revision (positive integer), revisionSha256 (lowercase SHA256).
It identifies an investigator-recorded observation revision, NOT a confirmed fact,
original-byte verification, trustworthy identity, or human-read proof.

GET /api/v1/cases/{caseId}/conflicts/{conflictId}/revisions/{revision}?sha256={revisionSha256}
returns {format:MCIS-CONFLICT-REFERENCE-RESOLUTION-1,reference,revision,
coverage,bytesVerified:false,humanReadVerified:false,identityVerified:false}.
The revision field is the exact captured revision document, not the latest record.
The server applies exactly the existing whole-conflict history read path (case,
timeline, full report content, all referenced source visibility, captured chain
and audit consistency), then selects the requested revision and compares digest.
This may refuse a historical reference when another historical source is now
inaccessible; it never bypasses that existing restriction. No original files read.
404 means no captured revision; 409 means supplied digest differs. Malformed
revision/digest returns422. There is no fallback to current state and no fabricated
legacy revision. A->B registry changes do not rewrite captured revision A.

This candidate adds only the read prerequisite. It does NOT add a report citation
kind, auto-generate conflict prose, change old reports, or enable archive support.
New reference schema is standalone, not accepted inside report.schema citations.
Report integration remains BLOCKED on lossless conflict revision/audit/receipt
archive and versioned citation handling across report read/edit/export/restore.
Old reports retain their original semantics; old missing history remains unknown.
No receipt or resolver response claims evidence was read or verified.
