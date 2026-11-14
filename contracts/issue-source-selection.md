# Pinned issue source selection trial

## Scope
The nonproduction IssueWorkspace explicitly loads authorized current local CSV/PDF candidates through a credential-free host callback. Python calls only the protected catalog ASGI endpoint and checks current session, case incarnation and epoch before/after discovery. Projection includes evidence ID, source incarnation UUID, SHA256, media kind, byte count and registration timestamp. It does not return source contents, paths or credentials.

## Selection and commit
Selecting candidates freezes `{evidenceId,sourceIncarnation,sourceSha256}` in top-level `sourcePins` beside the entry's sourceIds. The new host requires pins whenever sourceIds is nonempty. The journal validates an exact unique set of pins, obtains the current source snapshots inside its reserved SQLite write transaction and compares incarnation plus SHA before adding the event. It revalidates at the final source check; mismatch aborts/rolls back instead of silently binding a newer source. The saved event retains the authoritative full source snapshots; Entry/history/archive schemas remain unchanged.

Discovery itself is not a persistent lock (`selectionSnapshotPinned:false` describes discovery, not omission of write-time checking). It supplies version assertions that must match at commit. No lock on the source filesystem lasting after commit is claimed.

## Retry and errors
Nonempty pins join the operation digest, canonicalized by evidence ID. Same operation + original pins after a successful commit returns the historical success before checking current source bytes, with current permissions still required. Changed pins under the same operation conflict. Unknown failures retain the entire original command for retry.

Only the fixed, scoped/request-correlated `ISSUE_SOURCE_SELECTION_CHANGED` 409 signals a known uncommitted transaction. UI hides old source candidates, retains the investigator's text and requests fresh selection. Permission failures, generic exceptions, mismatched envelopes and callback-thrown errors never become that definitive status. An error after a successful commit cannot be recast as this rollback response by source revalidation.

## Compatibility
Existing direct trusted service/HTTP callers with no sourcePins retain their previous unpinned current-at-save behavior and digest for existing retries. Empty pins with no sources leave that digest unchanged. They must not be described as version-pinned. The new host refuses source-bearing commands without pins; old no-source commands remain supported. Old source catalog payloads without incarnation fail closed in the new UI. No migration, credential activation or legacy-role route change occurs.

## Limits
Still disconnected/unmounted by default and not a production login or native/browser IPC. Actual integration tests use React/HappyDOM, trusted Node stdio, Python ASGI and real temporary SQLite with fictional sources. No source preview, OCR, LLM, official fact review or liability decision is introduced. Historical references do not attest that the source remains current today.
