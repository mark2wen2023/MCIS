# Candidate review worksheet export

Internal deterministic callable build(body) and export_json(body), not an API or
UI download route. Exact input fields content and expectedDigest. Reuses existing
knowledge-card validation and canonical content digest. Invalid/missing source
fields reject; unverified sources never count as complete. A changed content
digest returns VERSION_CHANGED (409). No card ID, path, DB lookup or role spoofing
is accepted. Caller must provide already-authorized content; no authentication or
permission boundary is added or replaced.

Output binds full content and digest to six pending checks: source identity,
locator/excerpt, claim support, applicability, use rights and release scope.
The existing three required publication approvals are all pending. No prior
approval/reviewer/status input is accepted, no checklist completion or approval
is inferred, and no review state is written. Source Public and Synthetic both
require review; Synthetic is never promoted to real evidence.

The JSON export includes content verbatim, so it is INTERNAL REVIEW ONLY, not a
redacted public release. Caller authorization is required before delivery to any
reader. No automatic retrieval or outbound communication occurs. No model use.
export_json serializes with ensure_ascii and escapes < > & as Unicode JSON escapes.
After JSON parsing, UI must render content as text, never trusted HTML. This is
not an HTML/PDF exporter; no template, script or markup in source is executed.

No new route, database schema, shared router, formal-review workflow or UI change.
Remaining integration: authenticated internal download endpoint, text-only UI
rendering, current card re-read and digest comparison at review, accepted evidence
for each completed check, and production/browser validation. This worksheet is
not an expert opinion or source/rights certification.
