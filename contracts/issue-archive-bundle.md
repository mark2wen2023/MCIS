# Supplemental issue history / direct-source bundle v1

This is a **supplemental problem-record and directly referenced source byte bundle**,
not a replacement for `.mcase`, a full case backup, source-parent lineage archive,
or production archive UI. Existing package formats and apps remain unchanged.

## Operations (trusted-host service API)

`mcis_service.investigation.archive.initialize(db)` explicitly creates independent
archive metadata and UPDATE/DELETE rejection triggers. No account, grant, source
activation or existing journal mutation occurs. It is not an HTTP endpoint.

- `export_bundle(db, settings, token, case_id)` returns UTF-8 JSON bytes. Current
  authenticated case member and full-content permission required. Exports all
  locally current journal cards/events and actual bytes for every directly
  referenced source hash. No issue operation receipt, identity/session record,
  permission grant or credential is included.
- `restore_bundle(db, token, case_id, raw_bytes)` requires current member/content
  access plus the separate issue write grant. Fully validates before insertion;
  saves one immutable imported-history record under target case incarnation and
  epoch. Same digest replay remains authorized and does not duplicate the record.
- `read_imported(...)` and `list_imported(...)` expose only authorized historical
  imports, explicitly marked `imported_history_untrusted`, `activated: false`.

All operations use the reserved SQLite writer transaction and final authorization
check. Restore/receipt commitment is atomic. A failure must not partially import
cards, create live events or change local authority.

## Format / validation

Envelope `{sha256, payload}` hashes canonical sorted JSON. This hash detects
accidental corruption; **it is not a signature or proof of provenance**. Anyone
can make a self-consistent bundle. Original author IDs, dates and source statements
remain unverified claims after import. Import never approves a fact or accepts a
source into the active evidence index.

Payload has a fixed version, originating case ID/incarnation and explicit `exportCaseEpochUtc`,
all issue events (including each event's own historical epoch), and a hash-keyed
map of base64-encoded direct source bytes. No paths, URLs, compression, external
fetching or executable content are interpreted. Empty source map is valid only
when no issue references any sources.

Strict validation rejects unknown/duplicate JSON keys, nonfinite values, bad IDs,
noncontiguous sequences, invalid judgment/verification/discussion order, mismatch
between source ID lists and snapshots, foreign case references, missing or extra
source hashes, malformed base64, and byte-hash mismatch. Whole JSON is bounded to
8MiB, decoded source total to8MiB,100 cards,200 events per card and200 direct sources. No partial bundle
is returned when the budget is exceeded. At most20 imported bundles per target
case incarnation. Entries remain unreviewed.

Export requires each historical direct source snapshot still to match the current
registered source and its original bytes. Conflicting historical versions, missing
or altered files prevent export; history is not silently discarded or replaced.
References to parent evidence inside a source's own metadata are not recursively
bundled; consequently this is not a claim of full evidence-chain preservation.

## Restoration semantics

Only the same case ID is accepted. It may be a newly created case incarnation,
but the data remains historical and inactive. Original identity/epoch and target
epoch stay distinct. Changing target epoch prevents reading/replaying the old
record through the current-epoch endpoint; old history is not deleted or promoted.
Imported source bytes remain inside the historical bundle, not on arbitrary paths
or in active evidence storage. There is no automatic resumption of old operations.

Users still need the existing case/evidence package for a full case workflow.
This supplemental bundle does not yet integrate with that package or browser UI.
No actual LLM, production login, deployment or merge is involved.

## Explicit trial HTTP transport

Only the nonproduction `create_identity_trial_app` exposes these paths:

- GET `/api/v1/trial/cases/{caseId}/issue-archives/export`: exact UTF-8 JSON bundle
  bytes, fixed `mcis-issue-history.json` attachment filename, no double encoding.
- POST `/api/v1/trial/cases/{caseId}/issue-archives/import`: raw application/json
  bundle, returns only digest/count/replay/inactive summary, not source bytes.
- GET `/api/v1/trial/cases/{caseId}/issue-archives`: bounded historical summaries.
- GET `/api/v1/trial/cases/{caseId}/issue-archives/{sha256}`: authorized inert history.

Explicit host initialization remains required. No credential provisioning, grant
creation, active-event restoration or old-route passthrough is exposed. Export and
history reads require current membership/full-content access; import additionally
requires issue write grant. Authorization happens before receiving body and again
in the transaction. One Bearer header is required; Origin, Cookie, old role/operator
headers, compressed or transfer-encoded bodies are rejected.

Input limit8MiB enforced from Content-Length and actual chunks, with30-second total
body deadline. Duplicate headers/JSON keys, invalid UTF-8, nonfinite numbers and
all invalid bundle content fail closed. GET accepts no request body. Exact paths,
no query variants, unsupported methods/HEAD receive no archive. Responses are
no-store/nosniff; historical response envelope capped at8MiB+1024bytes.

Disconnect during receiving does not import. Once synchronous service execution
starts, loss of response does not prove rollback; retry the same bundle digest to
confirm without duplication. Do not reinterpret an import receipt as live-system
recovery or evidence approval. This is ASGI trial HTTP, not a production browser
session, public listener, UI or deployment.
