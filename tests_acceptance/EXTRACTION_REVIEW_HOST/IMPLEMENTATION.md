# Ephemeral extraction review host

`ExtractionReviewHost` in agents/extraction_review_host.py binds an authorized case/record/source digest at construction. Provider supplied only by trusted host (None, fixed FixtureProvider, or validated LocalProvider). No new HTTP endpoint or legacy role app route. Context exposes nonproduction scope, never token.

Strict generate request allows only profile/contextId/caseId/recordId/requestId/action. Review additionally requires proposalId and exactly one decision per1-based proposal index, each with nonblank note<=1000 and one of adopted_working/rejected/needs_verification. Review cannot edit quote or extraction payload. Input JSON encoding bounded64KiB, output512KiB. In-memory active proposal is a deep copy, and response objects cannot mutate it.

Same requestId+complete payload replay does not repeat generation or review; cached responses require current auth/binding. Only current generation caches retained, <=32 seen IDs; superseded generate IDs cannot revive old proposals. Review success consumes active proposal, retains only its review receipt for identical retry. Failed/unknown generation is not automatically reinferred under same ID. Caller must distinguish retry from an explicit new generation. Concurrency is rejected while busy. Close clears credentials/state before pending generation returns; late results cannot reactivate it.

Review returns reviewedAsWorkingOnly=true, saved=false, factVerified=false and ReviewedWorking. Checksum is nonpersistent, unsigned working receipt, not approval or activation. Nothing writes old Draft/Statement tables or changes original evidence. No durable recovery after host process exit.

Main tests:16 new review-host +15 extraction-main = **31 passed, zero skipped,17.10 seconds**, one known deprecation warning. Covers disconnected provider, fixture labels, immutable result/replay, one generation call, same-review idempotence, payload-conflict refusal, superseded generation, forbidden client configuration, decision completeness, revoked cached access, busy/close delayed results,32-ID budget.

Command: `PYTHONPATH=issue-journal/service mcis-work/service/.venv/bin/pytest -q issue-journal/service/tests/test_extraction_review_host.py issue-journal/service/tests/test_host_extraction.py --disable-warnings`.

These are implementer tests. Separate parent review remains required. No push/merge/deployment, production login, real model, durable workflow or UI validation claimed here.
