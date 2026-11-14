# Issue source selection trial

## Implemented path
The nonproduction IssueWorkspace explicitly loads current authorized source candidates via JournalPort.sources. The host-owned TypeScript callback sends a scoped `sources` command without issue/write fields or credentials. Python IssueHostClient calls only the protected trial catalog ASGI endpoint and rechecks session, case generation and epoch before and after the request. No listener or legacy role-header service is added.

The host projects only evidence ID, SHA256, CSV/PDF kind, byte count and registration timestamp. UI selection adds up to 20 source IDs to the frozen append command. Existing journal writes recheck actual source registrations and bytes inside the reserved SQLite transaction and preserve the then-current source snapshots. Historical UI references are not current source validity attestations.

## Meaning and limitations
A candidate is a supported current local registered source, not a verified factual observation. Catalog completeness for all media is NOT claimed. The selection does not pin a source version across UI delay: the server validates and records the current source at save time. A valid later re-registration may therefore differ from the prior discovery entry; the UI does not promise otherwise. No source preview, original text/file download, OCR, LLM or liability determination is introduced.

The UI remains unmounted and disconnected by default. Actual integration acceptance uses React/HappyDOM, trusted Node stdio, Python ASGI and real temporary SQLite with fictional sources. It is not a production browser IPC/login, persistent user database or deployed workbench. No token is stored in browser storage or passed to UI. Fixtures are temporary, removed on normal exit.

Context changes and failed reads hide stale source metadata. Unknown saves preserve the original operation for idempotent retry, not a newly edited request. Closing a UI cannot undo a committed server operation.
