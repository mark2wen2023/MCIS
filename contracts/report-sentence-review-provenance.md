# Report sentence text replacement and provenance

Current sentence source/sourceStatus describe the current wording. A successful
sentence-level modify replaces sourceStatus with Investigator, consistent with
source=Investigator and existing whole-section behavior, whether textZh, textEn
or both change. It must not keep PublicReportExcerpt (or another generated-status
label) on manually replaced text. Confirm/dismiss without text edits retain the
original source labels. This is authorship/provenance, not fact verification,
authenticated identity, or causal approval; existing status/review semantics stay.

Keep original generatedText, citations, unchanged-language text and prior reviews.
The normal transaction records beforeValue with the original sourceStatus and
afterValue with Investigator, before storing the report. Citation retention is
trace context, not proof that changed wording is an original quotation or supports
a new claim. No source evidence is edited or reconstructed.

No migration rewrites existing saved reports or past audit snapshots. Previously
saved inconsistent labels remain as stored until a subsequent legitimate text
change; ordinary reads do not silently repair history. No permission change,
new citation type, source fetch, historical binding or archive-support expansion.

## Visible inherited-reference disclosure
For a sentence with source=Investigator and nonempty citations, the report view
and PDF/DOCX place a language-matched, always-visible notice next to that sentence's
citations: inherited context for traceability, not automatic support for edited
wording and not a claim the edit remains an original quotation. Human comparison
is required. This also applies after confirm/dismiss and to older stored reports
whose sourceStatus is stale; it does not rewrite stored documents. Generated
sentences or sentences without citations do not get a false inherited-reference
label. Source/citation/history data and existing permission checks remain intact.
