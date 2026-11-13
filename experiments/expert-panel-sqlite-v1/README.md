# Expert panel E1 storage service slice (isolated, synthetic-only)

Based on PR45 design at 74c3cfe and the user's confirmed workflow. This directory is an independent prototype, not imported by MCIS, not a production HTTP endpoint. It does not change case archive behavior or any production data. No NuGet, .NET, browser, package installation, external model or deployment was used.

## Run
Python standard library only:
```
python -m unittest -v
python demo.py
```
The demo uses a temporary SQLite database and explicitly synthetic fixture opinions. It never invokes a model. The script prints the context the next expert would receive, NOT evidence that a model read it.

## Service contract
- `Store(path).create(panel_id, actor, snapshot, budget=8)`: manually initiated by synthetic investigator identity. Requires synthetic=True; freezes report/source contents and digest. Only four named role IDs are permitted. 海青君 is host metadata, not a fifth voter.
- `context(panel_id, role)`: initial reviewers cannot see peers; after four reviews, exposes peer reviews and ordered previous turns. Returns source manifest, not source text. All returned mutable data is separate from storage.
- `command(panel_id, actor, request_id, expected_revision, operation, payload)`: `read_source`, `review`, `challenge`, `cancel`. Atomic SQLite immediate transaction, expected-revision conflict and exact-request replay receipts. A mismatched reuse fails. Concurrent writers at one revision permit one winner.
- Source read returns the exact frozen version and atomically records delivery. References must match a version delivered to the same role. This is access bookkeeping, NOT proof of reading comprehension or factual support.
- Challenge targets refer to existing peer reviews or turns. Own targets are rejected. Budget applies to cross-examination turns, not tokens or wall-clock costs. Budget exhaustion prevents further turns. Cancellation preserves data and blocks ALL command receipt replay as well as new operations and context reads. Even a repeated cancel returns a controlled cancelled error; receipts remain stored but are not exposed. Production identity/revocation checks are still not implemented.

## What is verified
26 standard-library tests: manual-start and synthetic guard; restart/frozen snapshot; blind initial reviews; source manifest/version and role-specific reads; unread citations rejected without write; receipts/reuse and stale revisions; two SQLite writers; early/invalid/self-targeted challenge; peer context and copy isolation; turn budget; cancellation/history; input limits; no final-report operation or host vote; cancelled read/speech receipt replay rejection (including reopen), retained receipts, malformed source fields, and invalid snapshot input. Demo executes a four-role synthetic cycle.

## Limitations blocking production
Caller-supplied actor strings are trusted test harness input, NOT authentication or role-based access control. The synthetic flag is declarative, NOT a privacy classifier: never insert real case materials here. Only one local process/database path is assumed; production storage ownership, encryption, schema migration and backup are absent. No HTTP/UI, expert avatars/personality execution, LLM integration, real retrieval, source authorization, evidence bytes, substantive citation validation, agenda/claim semantics, output moderation, human adoption, material intervention/reconsideration, summary, report editing or archive exists. No live request cancellation or token budget. Snapshot digest detects representation changes but is not a signature or tamper-proof audit. Raw source text is data; production model/tool prompt-injection controls still needed. API names/contracts remain experimental.
