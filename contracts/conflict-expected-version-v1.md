# Conflict optimistic write precondition (candidate)

GET /cases/{caseId}/conflicts:editable returns [{conflict,version}] using the existing
timeline read permission. Content and token are taken in one reserved SQLite
transaction. Version is canonical SHA256 over caseId/conflictId/current stored doc
and last full revision SHA (null for an existing pre-journal row). It is not an
identity credential or evidence-file hash. The old GET /conflicts response is unchanged.

PATCH /conflicts/{id} requires body.expectedVersion. POST /conflicts requires it
when the ID already exists. New-ID/auto-ID POST still works without a version; a
supplied version for a nonexistent ID returns412 rather than re-creating a vanished
record. Expected token is stripped before validation/persistence of the conflict.
Successful response remains the existing Conflict document, not a new envelope.

After existing write authorization, compare token with current state inside the same
reserved write transaction as revision preparation/current update/audit/capture:
- absent/null:428 CONFLICT_VERSION_REQUIRED (upgrade/re-read required);
- malformed token:422 CONFLICT_VERSION_INVALID (Pydantic may reject wrong types);
- mismatched token:412 CONFLICT_VERSION_CHANGED; no row/revision/audit/file mutation.
A same-document A->B->A cycle still changes the revision token. Never fall back to
unconditional writes or auto-fetch a new token and retry the old payload.

Compatibility: old read clients and new-record creates remain compatible. Old clients
that modify/replace existing IDs must upgrade; they fail428 explicitly. This is an
intentional write-contract tightening, not transparent backward compatibility. Legacy
rows can be read with a version without changing data; first accepted write preserves
unknown-before-capture history. Nothing reconstructs missing prior history. Existing
conflict permission and archive refusal remain; versions never grant authorization.

Workbench loads the editable endpoint. Note editing captures the selected row version;
refreshing the list does not replace that saved edit version. On412/428 retain local
note, show a persistent refresh/compare warning and offer refresh without auto-save.
User must preserve/compare their draft and explicitly reselect/re-edit after refresh.
Status actions use the version associated with their displayed row. Client sends no
blind overwrite or automatic retries. No new authentication, original-byte checking,
production concurrency or real browser acceptance is implied.
