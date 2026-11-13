# ECFC new manual draft slice independent disposition

This is a new implementation based on main `3aba2bf`, not restoration of lost W11 artifacts. Previous reported 933 tests are not evidence for this slice. Only synthetic seed=False fixtures are used.

## Final revised-protocol verdict
- D1 and D2: CLOSED for the exercised synthetic scope. Original red assertions retained and passing.
- Mandatory archive acknowledgement revision: independent 30 API/DB tests passed with backend-v2's 13 implementation hashes unchanged before/after.
- Actual loopback HTTP/real core: 10 additional checks passed, hashes unchanged.
- B1 environment blocker: Chromium could not create its process-singleton socket under default sandbox or the same tool's normal approved escalation. Zero actual UI assertions completed. This is not classified as a product bug or approval rejection; no bypass attempted.

Overall **NOT fully accepted / NOT ready to merge** because supported independent browser acceptance remains incomplete. Backend results must not be called whole-W11 completion or ECFC archive support. Final freeze: `logs/ECFCNEW-backend-v2-hashes-frozen.txt`. Reproduction and scope are documented in `tests_acceptance/ECFCNEW/REPORT.md`.

Material browser failure: `process_singleton_posix: socket() failed: Operation not permitted`. The normal approval path admitted execution but did not resolve this runtime failure. Raw logs remain local and are not included in delivery; no inaccessible log is needed to understand this disposition.


## Historical pre-freeze independent findings (2026-11-12)

### D1 — persisted-document binding/integrity not enforced (initially OPEN; now CLOSED in tested scope)

Independent `test_integrity.py::test_corrupt_or_future_saved_document_is_not_returned` saved a genuine synthetic draft through the real CLI/API, then deliberately modified its database JSON. Five variants (different caseId, Confirmed status, wrong digest, unknown future field, future coreVersion) were each returned by GET draft as HTTP 200. The unknown field was returned verbatim. This is a reproduced synthetic corrupted/future-record boundary failure, not a claim of real user data disclosure or an ordinary API path that creates such records.

Required: closed-world schema/status/version, same-case binding and digest validation before exposing or reusing current, receipt and audit document snapshots. Keep the original red assertions; retest a repaired implementation.

### D2 — accepted Unicode input exceeds hidden core-output budget (initially OPEN; now CLOSED in tested scope)

Independent `test_valid_unicode_budget_graph_can_preview` submitted 25 nodes with 1000 Unicode scalar emoji each, within the 128 KiB UTF-8 input and node/text limits. The real C# CLI's default escaped JSON exceeded the HTTP adapter's 256 KiB output cap. HTTP returned 503 ECFC_CORE_UNAVAILABLE, although the input fits the advertised profile. Required: a correctly bounded output budget/encoding aligned with accepted input, or an explicit documented input/response budget restriction with appropriate error semantics. Retain the original red assertion for the supported profile.

## Historical interim status
At the initial review, the implementation was not frozen or accepted and the remaining matrix was pending. This is superseded by the final verdict above. No publication, merge or deployment was performed by this reviewer.

## 2026-11-12 repair verification (backend frozen, UI pending)

D1 repaired by implementation owner: closed-world document/result/event validators, exact same-case/schema/status/core-version/digest checks, current document equal to latest validated audit snapshot, receipt equal to its validated audit event, and adjacency checks within the returned audit window. Independent original five red variants now pass, plus receipt/audit foreign-case injection and coherent recomputed current digest without matching audit are refused. This establishes tested local integrity checks, not authentication or a certified complete audit chain.

D2 repaired by implementation owner: 1 MiB CLI and adapter response budget aligns with the accepted bounded Unicode graph. The original valid 25x1000 emoji fixture now previews through the actual core successfully. No input assertion was weakened.

A further independent 16-test matrix passed real CLI edge/presumption semantics; second-connection source/case/policy mutation while core runs; concurrent distinct-request CAS; commit-then-response loss with idempotent replay; same operator/different qualifying role replay refusal; protected historical sources; three-table rollback at audit/receipt/commit faults; append-only records; case-local package guard; and malformed/partial policy refusal. These are local synthetic SQLite checks, not production multiworker or full-project certification.

The initial 25-test hash-bound run used `logs/ECFCNEW-backend-hashes-frozen.txt`; this is historical and superseded by the final 30-test protocol revision above.

