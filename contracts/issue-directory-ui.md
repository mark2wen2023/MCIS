# Trial issue directory and reopen

Unmounted IssueWorkspace adds optional JournalPort.list(caseId). No credentials,
fetch, legacy identity, browser storage or deployed route. Host action:list sends
only caseId plus existing fixed profile/context/request correlation fields. Reply
is projected from trial-issue-list-v1 same-case body; at most100 unique UUID cards,
revision1..200, openingNotePreview up to200 chars, known lastKind and explicit
working_unreviewed. Unknown fields are not passed to UI.

Refresh directory explicitly. Summaries are not full history or authority. Opening
a card clears visible history/sources and requires a successful read before append.
A new blank card performs no save until the first judgment is submitted. Existing
issueId prop continues to open in read-blocked state. Nonempty draft, busy and
unknown-outcome states block directory refresh/card switches; history refresh is
also blocked with a draft. Context changes intentionally clear old scope state.

Keep per-card last known histories inside the current context to reject rollback
or rewritten prefixes on reopen, including switching away and back. Clear them on
context change; no persistence or claim of cross-session integrity. Directory read
failure hides directory, visible history and source metadata; existing card remains
read-blocked rather than becoming a new card. Unknown save remains same-op retry.

Local rehearsal supports multiple fictional cards in memory, not a database.
Directory lists only limited current trial cards; no case-wide discovery/production
login claim. Displayed notes are unreviewed working opinions, not evidence approval,
liability findings or expert consensus. Refresh to obtain latest directory versions.
