# Timeline local-binding entry boundary (preparatory slice)

This is NOT evidence-version binding, receipt issuance, source approval or a
complete import security fix. No local receipt table exists in this slice.

## Protected names and behavior
The exact JSON key `timelineSourceBinding` is reserved at the draft root and
as a direct property of its payload. Generic draft submission rejects it,
including null/empty values, with422 TIMELINE_BINDING_LOCAL_ONLY after the
normal draft-write authorization check. No arbitrary text, recursive metadata,
case variants of JSON keys, sourceSnapshot or other existing user fields are
reinterpreted as binding authority. Review payloads are checked for every
decision; Confirmed/Modified also check the existing stored draft. A rejection
with no replacement payload may still dismiss a schema-valid old draft whose
payload contains the field, without treating it as trusted. A root-level field
violates the existing closed schema and remains CONTRACT_VIOLATION even on
rejection; no schema relaxation or automatic cleanup is introduced. Future binding must read only server-owned
records, never those alternative caller fields.

The .mcase importer rejects the same claimed fields in agents/drafts.json.
It also rejects the exact case-insensitive package root namespace
`timeline-bindings` or `timeline-bindings/…`, with422
TIMELINE_BINDING_IMPORT_UNSUPPORTED. These checks occur before any import SQL
or blob writes, including when a package is otherwise hash-consistent.
Do not silently drop a claimed receipt and report successful historical restore.
The original package remains the user's recoverable source.

No archive white-list, schema, table, signed record or original blob is changed.
A future receipt/history implementation must explicitly supersede this rejection
with a validated inactive historical representation; current imports cannot
claim that capability. Existing unbound drafts retain their existing behavior.
This means they STILL do not have trustworthy version binding, and this slice
must not be described as fixing that whole gap.

## Compatibility scope
A search of the selected current service/contracts and older full checkout
found no existing use of these exact reserved names. This is not a survey of
all external user packages. Legitimate external metadata at these exact reserved
locations will now be rejected; similar keys, nested ordinary notes and
`timeline-bindings-notes/` do not match. Tests exercise such nonmatches.
A valid legacy1.0.0 package with unbound draft, registered source bytes and no
reserved names imports and exports without changing draft JSON or source bytes.
Working-record history and other closed-world gates are unchanged, not bypassed.

## Tests and claims
12 API/SQLite tests cover root/payload null/empty/forged values, rejection before
row/file writes, namespace/case handling and the legacy roundtrip. A prior test
fixture omitted evidence registration and the existing exporter omitted that
unregistered raw file; the fixture was corrected to register it. No product
export rule was weakened. Native independent review is required before push.
Tests use fictional content, not actual LLM output or real incident evidence.
No CI/full-archive/production authentication certification, merge or deployment.

Independent review found and reproduced an initial omission in review payload
updates (Modified saved the reserved field). The review ingress was patched
before publication; final independent regressions include this path.

Final independent21/21 passed (12 entry/import/legacy +9 review/historical
probes), zero skips. Review failures use full-table/full-row snapshots to
verify no changes; schema-invalid root claims remain rejected on dismissal.
Existing package tests separately9/9 passed. No new tables or archive whitelist
changes. All fixture data is fictional.

Final combined local rerun after review fix:95 passed, zero skips,35.30s
(agents/colreg/W20, earlier timeline permissions, model facts, new boundary,
independent review and existing package tests). Actual W2 wrapper for existing
core tests; model tests still fakes. Not a whole-repository or CI pass.
