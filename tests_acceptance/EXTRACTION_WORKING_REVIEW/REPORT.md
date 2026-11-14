# Independent durable extraction working-history review

2026-11-14. Reviewer did not implement or change products. New independent test: `service/tests/test_extraction_working_review.py`.

## Result

Independent suite **16 passed**, exit 0. One existing FastAPI/Starlette httpx deprecation warning. No blocking defect found in reviewed scope. This is source review and synthetic local SQLite tests, not production login, deployment, real inference, browser IPC or legal/factual validation.

## Reviewed safety boundaries

- `PersistentExtractionReviewHost` is a distinct opt-in Python callable, profile `mcis-extraction-review-persistent-trial-v1`; existing ephemeral UI/protocol unchanged.
- The host generates originals itself. UI-like payload fields cannot be passed to generate or supplied inside review decisions. `_save_generated` remains a private trusted-code entry, not a provenance/authentication guarantee for arbitrary Python callers; no HTTP route exposes it.
- Dedicated grant gates writes and write replay; reads deliberately use current session/case/content authorization, not the write grant.
- Same-session `snapshot_in_session` plus transaction guards check current record, case incarnation, policy and source. Old-binding read/list/replay fails closed. Denial does not delete history or assert that prior writes did not happen.
- Original snapshot and review events are separate append-only records. Generation stores an unreviewed proposal at revision 0; this is not a completed review. Human revisions are append-only; adoption remains working-only, not fact activation.
- Cross-host generation replay resolves durable operation records before provider invocation. Host closure during inference prevents subsequent store/return. No token appears in exposed result structures.

## Independent tests

1–6: quote, claim, authorSubjectId, receipt, token and factVerified extra decision fields rejected, zero review writes.
7: no provider returns not_connected, no fake proposal/review storage.
8: caller mutation of returned proposal/history cannot change stored originals; Draft/fixture/working flags retained.
9: revoked dedicated write grant blocks generation and review replay.
10: record-sensitive-fragment change blocks read/list/exact review replay; prior saved proposal/review remain in database.
11: closed host blocks generate/read/list/review.
12: explicit method signatures reject UI-supplied model result and quote parameters.
13: cross-host generation replay cannot invoke provider again.
14: actual threaded close during delayed inference stores no proposal and returns no proposal.
15: revoked case membership blocks read/list/generation replay.
16: current testimony Deny policy blocks history read/list/new review.

Parent separately covers concurrency, rollback, SQL triggers and actor-bound replay; not counted in these 16.

## Frozen SHA256

- host_extraction.py `1afdb4661d17df122f0bf4d48daf6e50235a41920f704019d8fca58674dba015`
- extraction_working_store.py `29954eb1b9721ab3fea109eaa3f25190e6c47219a3fea65ce2de6eab1125737c`
- persistent_extraction_review_host.py `3453b451af7a14e043b3cd3d738530466145a3ef1584ff6e6acca06a92e7151a`

No products edited, no push, merge or deployment performed by reviewer.
