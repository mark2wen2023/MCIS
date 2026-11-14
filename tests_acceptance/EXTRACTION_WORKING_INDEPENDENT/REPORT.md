# Independent durable working-review checks

This is an explicit trusted-host trial, not a production browser login, mounted UI, formal statement approval, fact verification, or deployed service. Only synthetic fixtures were used; no external model/API was called.

Independent test file: `service/tests/test_extraction_working_independent.py`.

Verified (7 tests):
- Two real concurrent threads append against revision 0. Exactly one commits and one returns conflict; resulting revision is 1.
- Injected final guard failure rolls back both a review append and a new proposal save. No partial event/proposal remains.
- Direct SQL UPDATE and DELETE fail for both immutable proposal and review tables.
- A newly opened Database instance replays a prior review operation without duplication.
- A second valid, explicitly authorized investigator cannot reuse the first actor's operation ID/content.
- Original proposals remain Draft; tokens do not appear in returned history.

The database must be initialized and grants provisioned by a trusted host. `_save_generated` is a private trusted boundary, not a remotely callable API: hashes and shape validation are not cryptographic provenance. The dedicated host obtains proposals from the existing checked generation path, not client-submitted model results.

Stored human choices remain working judgments. `saved: true` means only the working record was stored; it does not mean original testimony, report facts, a training dataset, or official findings were approved. A proposal at revision 0 is a saved pending proposal, not a partially saved review.

Historical content is retained, but current full source/policy/record binding must still match before it is exposed or revised. A mismatch means current access is denied, not that a previous successful save did not happen. This conservative rule is intentionally not a historical-source access system.
