# Issue archive independent review

Scope: isolated supplemental issue records and directly referenced source-byte bundle. Not `.mcase`, not whole-case or parent-evidence-chain backup. Imported payloads are inert, explicitly untrusted historical material. No production/browser/LLM validation.

Independent suite: `service/tests/test_issue_archive_independent.py` (19 tests), alongside 9 implementation tests. Covers missing/extra source closure, invalid base64, duplicate cards/source IDs, foreign source case/incarnation, exact version type, duplicate JSON/size budget, rollback on commit failure and final authorization revocation, concurrent same-digest replay, fake historical author not activated, explicit schema initialization, append-only triggers, final source-byte checks and revoked-session replay/read.

Finding: source `version=true` was accepted after Pydantic Literal normalization despite post-validation integer check. Reproduced in actual test, then fixed with original-value before-validator. Regression retained.

Model clarification (not a product defect): individual historical event case epochs can differ from export-time epoch. The top-level field is now `exportCaseEpochUtc`, while individual event epochs are preserved without authenticating historical claims. Independent test confirms untrusted/non-activated status. An intermediate test run crossed the field rename and failed with stale loaded test field name; final run uses aligned files.

Digest is accidental-corruption integrity only, not authenticity/signature. Synthetic author UUIDs can intentionally be imported as untrusted historical strings but do not create subjects or grants. Future UI must retain these qualifications. Tests execute Python + real local SQLite; not browser/network/production security acceptance.

Final aligned run: **28 passed, zero skipped, 63.84 seconds** (19 independent + 9 main); one known Starlette/httpx deprecation warning. Command: `PYTHONPATH=issue-journal/service mcis-work/service/.venv/bin/pytest -q issue-journal/service/tests/test_issue_archive.py issue-journal/service/tests/test_issue_archive_independent.py --disable-warnings`.

Reviewed product SHA256: `c120241ecc835e2046e31a27ff3788aae9b72fa8cd2951ac52a4ee69e941f7ae` (`archive.py`). No remaining correctness blocker found within this scope. Nonblocking hardening suggestion: enforce cumulative encoded-source budget per source, before constructing an oversized per-card payload, to reduce transient memory amplification. Test files frozen; no product edits, push, merge or deployment by independent reviewer.

## Final resource-hardening retest (supersedes preceding hash/count)

Implementation now checks metadata budget before processing a card and encoded source budget **before base64 allocation**. Added a test where metadata fits but encoded-source room is one byte, with an encode spy proving allocation is not attempted. Independent suite now **20 tests**, file frozen.

Final main + independent result: **29 passed, zero skipped, 20.28 seconds**, one known deprecation warning. Product `archive.py` SHA256: `663d202eb15b8d6a0d99dbf0f1338ba6f7dd9d9ec25c8181860d26cc3c2d1bc5`. No remaining blocker within reviewed isolated callable-service scope. Earlier resource suggestion resolved.
