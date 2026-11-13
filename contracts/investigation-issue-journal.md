# Investigation issue journal: trusted-host first slice

## Business behavior

An investigator can preserve an initial judgment, append a verification with a
reason and `supports` / `refutes` / `inconclusive`, append a changed judgment without
replacing the former view, and record a discussion. Verification/discussion must
name the current judgment's event sequence in `againstJudgment`. A new judgment
requires a new verification before discussion. Discussion records are human notes,
not proof that a meeting occurred or unanimous agreement. Nothing here approves a
fact, adjudicates responsibility or publishes a final report.

The journal stores real SQLite records, not mocked results. Creation is the first
`append` with `expected_revision=0` and kind `judgment`. Subsequent writes use the
last read revision. Concurrent stale writes fail 409. Canonical UUID issue and
operation IDs are caller-generated. Same operation + exact request + same subject
replays the historical success without duplicating an event; changed content or
subject conflicts. A replay still requires current write authority, but does not
re-attest historical evidence. It returns the current journal, marked replayed.

## Entry points

`mcis_service.investigation.journal` provides:

- `initialize(db)`: trusted host explicitly creates separate journal tables and
  append-only triggers. Not installed by legacy `Database.create_all`.
- `grant(session, subject_id, case_id, enabled=...)`: explicit trusted-host issue
  writing permission, tied to current case incarnation. No HTTP provisioning.
- `append(db, settings, token, case_id, issue_id, operation_id, expected_revision,
  entry)`; entry fields: kind, note, sourceIds, outcome, againstJudgment.
- `read(db, token, case_id, issue_id)` and `list_issues(db, token, case_id)`.

These are usable in-process service APIs. The explicit identity trial app now also
provides the bounded HTTP adapter below; this is **not a production/browser feature**. They use
server-issued local sessions from existing trusted host identity, not role headers.
No existing app route is mounted or changed; no browser token storage is introduced.
The write grant is for this new journal resource, not a timeline or report permission.
Read requires current case membership and the conservative full-content policy;
write additionally requires the independent issue grant. All checks, seq allocation,
source checks and insertion share a SQLite reserved-writer transaction.

Optional source IDs are validated against current locally registered evidence,
including source bytes and case/source incarnation. Stored snapshots retain the
then-current source identity/hash/registration and case epoch. Reading old entries
retains these historical references, explicitly **not current source attestations**.
Narrative text may contain unstructured claims; it is not automatically verified or
parsed into reliable evidence links. Authors and server timestamps are recorded;
credentials are never in returned documents.

## Budgets / lifecycle / limitations

100 cards per current case incarnation; 200 events per card; note 1..8000 chars;
at most 20 distinct source IDs. Lists return bounded summaries, not all event text.
Unknown fields, invalid outcomes/references and malformed UUIDs are rejected.
No edit/delete interface; database triggers reject direct UPDATE/DELETE. This does
not defend against a database administrator dropping tables/triggers or replacing
the database. Trusted initialization and a trusted local database remain prerequisites.

Journal data is currently **not included in existing `.mcase` export/import or
restore**. No backup-completeness claim is made. Case replacement never migrates
old notes to a new incarnation. No task assignment, file attachment, auto-extraction,
LLM generation, consensus algorithm, formal approval, UI or production login is
implemented by this slice.

## Local acceptance

`PYTHONPATH=service pytest service/tests/test_issue_journal.py
service/tests/test_issue_journal_independent.py` (one shell command).
Uses isolated temporary SQLite and registered evidence fixtures. These tests are
business-service acceptance, not real browser/CSP/production identity acceptance.


## Isolated authenticated HTTP adapter

Only `create_identity_trial_app(db=..., settings=...)` serves these routes; the
legacy app and default protected entry are unchanged. Trusted host must separately
call `initialize` and provision an issue grant. The HTTP API cannot create accounts,
issue sessions or grant permissions. No browser-facing token injection is offered.

- `POST /api/v1/trial/cases/{caseId}/issues`: strict JSON `{issueId,
  operationId, entry}` creates initial judgment at revision0. Returns201 new or200
  same-operation replay. Caller supplies canonical UUIDs.
- `POST /api/v1/trial/cases/{caseId}/issues/{issueId}/events`: strict JSON
  `{operationId, expectedRevision, entry}`; revision1..199. URL fixes issue identity;
  cannot create a missing card at revision0 through this endpoint.
- `GET /api/v1/trial/cases/{caseId}/issues`: bounded summaries.
- `GET /api/v1/trial/cases/{caseId}/issues/{issueId}`: historical working entries.

Authentication is one server-issued Bearer session, rechecked against the actual
server database and case membership before reading the body and again by business
service under its transaction. Writes also require current IssueGrant; read does
not require a write grant. Full-content policy is enforced for all actions.
Cookie, Origin, content/transfer encoding and X-MCIS-Role/X-MCIS-Operator are
rejected; no old-role fallback, CORS, redirects, arbitrary routes or provisioning.
POST requires application/json, at most65536bytes, ten-second body deadline,
unique keys, no nonfinite numbers and strict fields. Invalid/stale/conflicting
writes return generic errors without notes, evidence metadata, token or SQL.
Failures after uncertain write completion explicitly instruct same-operation retry;
read-before-retry and the business service receipt prevent duplication.

HTTP exposure does not complete workbench integration, production login,
archiving/restore or browser security acceptance. All returned content is still
working_unreviewed. There is no fact approval or LLM generation endpoint.
