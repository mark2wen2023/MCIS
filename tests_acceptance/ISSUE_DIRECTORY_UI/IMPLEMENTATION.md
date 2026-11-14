# Issue directory UI implementation verification

This report is by the implementer, NOT the independent reviewer. Parent/client
reviewers independently inspect the products and record their own checks.

Products: model.ts (list schema/projection, optional list port, multi-card memory
rehearsal), hostPort.ts (fixed case-scoped list action and correlated parse),
IssueWorkspace.tsx (explicit directory/open/new blank/read-before-append).

Primary issue-directory.tsx:24 checks pass, exit0. Covers strict list parse,
multi-card rehearsal, open→read→append, draft-protected switching/refresh, blank
card no implicit save, create on first submit, directory failure fail-closed,
late context response, cross-card reopen rejecting earlier history.

Regression all exit0: existing main DOM workflow, existing DOM29, sources24,
source-pins22, host-adapter15, strict TypeScript. Counts are script checks and
may overlap; not complete repository/CI coverage.

Real cross-language issue-host-integration.tsx passes: React/HappyDOM→TS port→
Node stdio fixture host→protected Python ASGI→temporary SQLite. Two synthetic
CSV candidates, EV-001 selection, five saved entries, directory refresh/open,
read-before-write and sixth appended entry. Not real browser IPC, production
identity/login, network deployment, LLM or real case data.

Independent parent review requested two corrections: prevent draft loss through
history refresh; preserve known per-card baseline across reopen. Both implemented
and included in primary checks. No claim of old-code failure reproduction.

Files changed by implementer for publication: three products; new issue-directory.tsx;
updated issue-host-integration.tsx with directory/reopen/append scenario; this report
and contracts/issue-directory-ui.md. Independent reviewer file separate.

Frozen SHA256:
model.ts 145467a3dc2585d248ad94a52ca1127ebdf391bf264696ba5e934e04f54f706a
hostPort.ts 59fc408b4d8fe16e62b10edcbc034c5eaad91e9a2dbbc83fcc1956c8570233c1
IssueWorkspace.tsx 496e8a7faf5e33527068d50092910c33b38877fcb7871535b5225cf2a5b709d7

No push, merge or deployment performed by this implementer.
