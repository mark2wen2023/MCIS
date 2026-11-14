# Local unreviewed timeline worksheet (not admission or approval)

## Prior-model review and safe slice
AgentDraftRow is a generic document. Existing Confirmed/Modified timelineEvent
reviews can write confirmed timeline events. That path has no trusted source
receipt / reviewed observation lifecycle for registered alignment previews.
The binding plan also requires version/incarnation and archive semantics before
claiming persistence/approval. Therefore this slice does NOT submit AgentDraft,
create database records, issue receipt authority, or add a confirmation button.

## Investigator workflow
After a successfully checked result, the investigator can initiate a local JSON
worksheet download. It includes case/epoch, selected mappings/declarations,
checked source snapshots, explicitly unverified parent references, displayed
computed conflicts/clock status/diagnostic counts and a recheck checklist. The export
time is explicitly not the calculation time. The copy is editable/unreviewed,
not a signed receipt, not approved observations and not an import format.
Before formal review, compare current originals/SHA, rerun, verify extraction,
ship/unit/time assumptions and parent relation, then preserve disagreements for
human collective review. Saving this file does not complete that workflow.

## Data flow and privacy
Only a visible live result under existing investigator role/context gating can
show the button. Existing case/identity/source changes clear it. The serializer
reruns strict response/declaration validation and projects selected known fields.
No raw source CSV/PDF bytes, authentication headers, operator credentials or paths
are added. Unknown nested diagnostic/calibration details are deliberately omitted: only counts,
known clock status and whitelisted numeric statistics are included. The worksheet
explicitly requires checking diagnostic details back in the workbench; counts are
not a pass/fail certification.
The download function uses a local Blob/object URL, a fixed JSON filename and a
local anchor; no fetch, external URL, server save, cloud upload or approval API.
Object URL is revoked and the transient anchor removed even on click failure.
The user must safeguard the resulting case material; later source/permission
changes cannot recall an already-downloaded copy. No atomic authorization lease
or production identity guarantee is added. No password/key handling.

UI states only that download was initiated and asks the user to confirm actual
browser save. There is no success claim about disk persistence. The worksheet
cannot be restored through an added importer because no importer is provided;
editing authority/status strings does not make a file trusted.

## Acceptance
Primary worksheet.test.tsx66 checks pass (prior53 + new13, overlapping): controlled
Blob capture, fixed name, absent network save, unreviewed fields, exact source
hash/declaration, download initiation wording, anchor/URL cleanup and disappearance
after clear. TypeScript/Vite build passes with existing large-bundle warning.
HappyDOM/control-download only, NOT real browser disk-save acceptance. No new
backend, LLM, CI or full-system validation. No merge or deployment.
Independent review results appended below.

Independent review found unknown nested diagnostics could be forwarded during
code inspection; fixed before publishing by omitting details and projecting
known fields/counts. It was not claimed as an executed old-version reproduction.
Independent worksheet-independent.ts16 checks pass, covering malformed responses,
unknown-field exclusion, no fetch and cleanup on download failure. Independent
lifecycle72 passes (primary66 + six invalidation/late-response cases). Main66
rerun independently. Existing53 and source-version71 regressions pass; counts
overlap. Browser actual disk persistence remains unverified.
