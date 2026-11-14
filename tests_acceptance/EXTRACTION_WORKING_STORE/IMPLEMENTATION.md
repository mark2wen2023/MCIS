# Persistent working extraction review (explicit host only)

## Implementation and authorization

New `agents/extraction_working_store.py` uses independent WorkingBase metadata, explicit initialize, a dedicated subject + case-incarnation WorkingGrant and append-only proposal/review tables. Neither old Database.create_all nor reading grants provisions these tables/authority. All writes require dedicated grant in addition to real same-database session/case/full-content, original interview access and AgentService testimony policy. Read/list do not require write grant but require the full original binding to remain identical.

`host_extraction.snapshot_in_session` is the only refactoring of the existing extraction engine; old `_snapshot` delegates to it. The store calls this helper using its own transaction, never a nested session. Binding covers case incarnation/epoch, complete record, complete policy and current registered original source declaration/bytes validation. Store checks before and after materialization/mutation. Historical rows remain stored but fail closed for read/list/replay after any binding change; current permission to another source does not unlock the old source. There is no historical-source access recovery mechanism in this slice.

Private `_save_generated` is callable only by a trusted Python host, not an exposed HTTP/RPC input. It revalidates exact result/receipt shape, whole binding, prompt/output/checksum consistency and regenerated verbatim citations/statements against current source. Hashes do not authenticate caller provenance; malicious code inside the trusted Python host remains outside this boundary. No client UI model-result submission endpoint exists.

Proposal rows preserve the original generated result plus actor/server time and binding. Each review row stores a complete 1-based decision/note set, server revision/time and actor. Revision changes append rather than mutate original proposals or prior decisions. Expected revision and operation/actor/full-payload digests prevent duplicate writes and stale revisions. The only allowed decisions are adopted_working/rejected/needs_verification, all explicitly working-only, not facts or old Statement/Draft activation. Budgets:50 proposals/case,100 review versions/proposal,20 decisions,512KiB proposal payload,4MiB read view.

## Usable opt-in host

`PersistentExtractionReviewHost` in `agents/persistent_extraction_review_host.py` exposes explicit synchronous generate(operation_id), review(proposal_id,operation_id,expected_revision,decisions), read/list/close, under profile `mcis-extraction-review-persistent-trial-v1`. It does not implement or change old ephemeral UI RPC. Constructor binds authorized record, provider remains host-supplied. No database transaction spans model inference. A durable pending proposal is stored independently of later review events; saved proposal does not imply any review was saved.

Cross-host retry lookup requires current binding/authority, same actor, record and provider declaration before returning an old result; it avoids ordinary retry inference. Concurrency across separate hosts can still invoke a provider twice before the first save commits: durable operation uniqueness protects stored effects, not exactly-once inference. Within one host generation is busy-guarded. Closing while inference is pending prevents its later persistence; already committed effects are not rolled back by closing. Default disconnected provider yields no stored proposal.

## Verification

Main10 + existing extraction-main15 = **25 passed, zero skipped,14.70 seconds**, one existing deprecation warning. Main coverage: generate/store/review/reopen/replay/revise/read/list, dedicated grant, read without write grant, revocation, failclosed source binding, no automatic tables, forged/extra output rejection, revision/operation conflicts. Separate parent independent suite covers threaded concurrency, rollback, trigger enforcement and reopened Database reads; its results must be reported separately unless rerun together.

No new HTTP route, old Draft/Statement writes, deployment, real inference, browser/IdP integration or complete-case archive support. This working history is NOT yet included in `.mcase` or the separate issue archive. No auto-deletion/retention policy is implemented. Main tests are implementer tests; separate review required.

Hashes at initial successful test:
- host_extraction.py `1afdb4661d17df122f0bf4d48daf6e50235a41920f704019d8fca58674dba015`
- extraction_working_store.py `29954eb1b9721ab3fea109eaa3f25190e6c47219a3fea65ce2de6eab1125737c`
- persistent_extraction_review_host.py `3453b451af7a14e043b3cd3d738530466145a3ef1584ff6e6acca06a92e7151a`

Combined verification rerun: main-store10 + independent-store7 + extraction-main15 + ephemeral-review16 = **48 passed, zero skipped,27.93 seconds**. Command: `PYTHONPATH=issue-journal/service mcis-work/service/.venv/bin/pytest -q issue-journal/service/tests/test_extraction_working_store.py issue-journal/service/tests/test_extraction_working_independent.py issue-journal/service/tests/test_host_extraction.py issue-journal/service/tests/test_extraction_review_host.py --disable-warnings`. Tests and product files frozen pending remaining independent source review.
