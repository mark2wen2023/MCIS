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
