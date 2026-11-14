# Agent regression fixture migration

Base: ac36f328529c5ffe2f64a20c996d83e9b6aa4932. Native implementation
subtask and separate native reviewer, not a separate Codex application run.

## Diagnosis
The old W20 setup used default Investigator for full-original interviews.
The current conservative full-content gate rejects that default role because
medical is Deny and a PII masking rule applies. This is expected current policy,
not the timeline permission patch. Simply changing the test caller to Lead
then reveals a second obsolete assumption: creation now accepts only empty
unsigned drafts. Tests must append questions through the existing turns API.
The old AD-001 statement test targets signed IR-03; current policy correctly
rejects that write with INTERVIEW_SIGNED rather than changing a signed record.

## Changes (tests only)
Normal full-content paths explicitly use LeadInvestigator via a helper scoped
to the W20 test module. Global test H(), product policy, service implementation,
and source binding are unchanged. No categories or field rules are loosened.
The existing policy weakening test remains a deliberately adverse fixture
proving model-input redaction survives weakened rules, not product defaults.

Default Investigator and AgentService now explicitly fail extraction with no
model call. Revocation fixtures start with an authorized Lead, then deny its
testimony/agent_drafts or AgentService testimony. Existing invalid citations,
malformed model JSON, audit-independent source-change review rejection,
source-immutable edits and minimum redacted input assertions remain.
Signed seed review now proves 409, unchanged record and PendingReview draft.
A new unsigned-record test retains the old single-statement rejection behavior.
Two fake-model callbacks change policy/source in a second API transaction
while inference is in progress; 403/409 discards output and creates no draft.

The UTF-16 check uses the submitted original fixture string: current GET
redact_text applies mask_pii even for Lead, changing text length. Coordinates
bind stored original, not its masked display. This existing display-coordinate
limitation is recorded, not fixed or certified as a working UI in this slice.

## Verification and limits
Local combined W20/agents-colreg suite:45 passed, zero skips,20.89 seconds.
Real temporary SQLite and FastAPI handlers; configured real compiled W2 wrapper
for existing core tests. LLM completions are controlled fakes (one local HTTP
protocol fake server), never a real LLM or real investigation evidence.
Earlier 8 pass/1 fail/31 errors remains a true historical result for old tests;
this migration repairs test premises, not a production permission defect.
No CI/full repository/browser/production authentication claim. AgentService
cannot itself enter the full-original gate despite the later nominal role
allowlist. Do not broaden that gate to make agents run autonomously.
No merge or deployment.

Independent reviewer reran the two suites45/45 and added one direct SQLite
fixture-original check (46 combined). Review also prompted a stored
reviewStatus assertion after legacy rejection and direct stored-original
checks in the fixture; final rerun follows those changes.

Final independent rerun after both strengthened assertions:46/46 passed, zero skipped.
