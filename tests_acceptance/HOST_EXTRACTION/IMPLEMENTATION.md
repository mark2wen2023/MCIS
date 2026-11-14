# Protected host extraction implementation

New isolated callable `agents/host_extraction.py`, no old HTTP mount. `describe(db,settings,session_token,case_id,record_id)` returns bindingDigest/sourceScope only; `run(...,expected_binding_digest,provider=None)` defaults to not_connected with no proposals/inference, regardless of model environment variables.

Explicit FixtureProvider returns fixed contract text and is always labeled fixture, inferencePerformed=false. Explicit LocalProvider requires ModelConfig supplied by trusted host, validates loopback literal HTTP /v1 URL and nonblank model at every call, uses existing no-proxy/no-redirect model transport. No secret/environment config discovery. Configured model name is only a declaration: modelIdentityVerified=false.

Same-database session/case membership/full-content and caller testimony policy plus AgentService testimony policy required. Whole interview/policy/source registration declaration and case incarnation/epoch form binding; registered sources are checked against original bytes using source_current. No evidenceId uses interview_document_only and does not pretend an original was registered. Deep copies preserve input; provider receives mandatory-redacted prompt only. Before-egress and after-output binding/authorization checks suppress stale or unauthorized proposals. No lock spans inference; already-sent bytes cannot be recalled by later revocation.

Outputs must fit256KiB and pass existing strict parser and exact unique raw+redacted quotation checks. Returns PendingReview proposals with Draft statements and citations, saved=false. Does not persist Drafts/Statements/audit records or invoke review decisions. Receipt is only a deterministic runChecksum, not a signature, verified model identity or durable audit. Quote matching does not establish semantic/factual correctness.

Main tests: **15 passed, zero skipped, 7.47 seconds**, one known deprecation warning. Includes no implicit inference, fixture/no writes, mocked local redacted message inspection (not actual LLM validation), external/authenticated/query URLs and blank model rejected before network, malformed/duplicate/oversized/nonverbatim output, revoked session during call, stale binding pre-call, registered original success then changed-byte rejection. Initial13 setup errors were from legacy fixture lacking case incarnation; corrected fixture imports current case through existing trusted test setup, without relaxing product identity checks.

Test command: `PYTHONPATH=issue-journal/service mcis-work/service/.venv/bin/pytest -q issue-journal/service/tests/test_host_extraction.py --disable-warnings`.

These are implementer tests; parent independently reviews. No real model inference, browser UI, HTTP route, durable queue persistence, push, merge or deployment performed.
