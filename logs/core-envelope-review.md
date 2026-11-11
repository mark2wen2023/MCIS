# Core envelope type validation — 2026-11-12

Base: 4f3de7aaa7f955ee52873204c3655bbee6359de0, following the separately verified HTTP error-redaction slice.

## Scope

Python core_client rejects non-object envelopes, non-boolean ok, non-object success result/error, and non-string error code/message as CORE_BAD_OUTPUT/502. This prevents incidental attribute/dictionary/type exceptions and uses the prior HTTP safe presentation. Valid domain mappings and successful objects, including extension fields, stay unchanged. Empty error object retains CORE_ERROR and empty-message defaults.

No broad exception catch; no CLI/C# modification; not a full command-specific response schema, exit-status or transport-volume validation. Path capability and authentication remain unresolved. No source report or database changes, no merge or deployment.

## Verification basis

Same exact-source service/contracts partial snapshot as prior slice, not a clone; installed Python dependencies reused, no old database or core binary reused. New 24-case author suite red baseline: 15 failed / 9 passed on the original core_client. Implementation then passed combined 53-case suite. Independent review and final aggregate result recorded separately below. No full service, seeded report, browser or real C# regression is claimed.

## Final independent verification

Independent reviewer added 22 cases, including 17 malformed outputs through the real create_app HTTP exception handler with fresh unseeded temporary databases; all give safe 502. Valid error dictionary defaults, success extension fields and final-line JSON behavior are covered. Final rerun of the complete checked-in HTTP_CORE_ERRORS directory: **75 passed**, one existing Starlette/httpx deprecation warning, 3.06s. See core-envelope-independent-review.md and core-envelope-green.txt. Earlier 369/517 results do not certify this new commit.
