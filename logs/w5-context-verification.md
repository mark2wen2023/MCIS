# W5 active-case context verification

Baseline: remote main `0a29f28eeabae8087978de000caf47e5fe2aff30` verified immediately before publication. Selected source/test files were materialized from available local copies only when their Git blob SHA matched the remote recursive tree. Missing unrelated files were not represented as validated. The remote commit is created from the complete baseline tree plus an explicit allowlist, so absent local files are not deletions.

## Change

Interview reads and four mutation types now follow the active `?case` through the sidebar instead of a fixed demo ID. Case + role/operator and record boundaries reset protected text, row selections and forms. Response IDs are checked; identifiers are URL encoded; pending writes are synchronously guarded and their late UI effects suppressed on unmount. Empty cases have explicit empty rosters. W5 disclaimers no longer infer public provenance or borrow Lily/Mary for arbitrary cases. Legacy demo entry retains IR-03 selection. No API/schema changes or deployment.

## Final evidence

- `logs/w5-context-full-service-retry.log`: **532 passed**, 0 failed, 0 skipped, complete configured service pytest suite. Environment: `DOTNET_CLI_HOME=/workspace/shared/mcis-dotnet-home MCIS_DOTNET=/workspace/shared/mcis-dotnet/dotnet DOTNET_ROOT=/workspace/shared/mcis-dotnet`.
- `logs/w5-context-service.log`: targeted W5/contract/redaction self-tests **33 passed** (subset of full suite).
- `logs/w5-context-web-regression-retry.log`: all 13 current Web test groups, **666 assertions**, including W5/context/navigation, W6, W12, W16, W4, W7, W8.
- `logs/w5-context-selftest.log`: TypeScript force rebuild and production build pass; source lint exits 0 with 11 existing unrelated warnings, no W5 warnings/errors.
- Independent session: **10 real TCP HTTP tests + 19 Chromium scenario groups**, no failures/skips/page errors. Includes real lobby creation→W5 empty case, all four real UI writes versus peer cases with identical identifiers, privacy/role changes, late responses/writes, double clicks, Back/Forward, mismatched responses and special statement identifiers. Deliberate fault injection is labeled. See `logs/w5-context-independent-review.md` and `tests_acceptance/W5_CONTEXT/`.
- 9 frozen implementation/test hashes match after all verification. The independent suite and findings were not edited by the implementer.

## Recoverable setup failures retained

The first added pytest used an incorrect `conftest` import; corrected test import only, then reran 33 and 532 green. Initial broader Web run lacked a pre-existing analysis fixture log in the selective materialization; restored the exact blob-verified fixture and reran all Web groups. The first full service run hit .NET's read-only default home and was interrupted; set a writable `DOTNET_CLI_HOME`, built the unchanged core successfully, and reran the entire suite. Original failure logs and superseded freeze drafts remain for traceability. These were setup/test harness issues, not skipped tests or production-code workarounds.

## Scope limits

Not complete W5, production authentication, arbitrary-timezone display (existing W5 UTC+8 remains), interview creation/import UI, Unity/3D or LLM certification. No reports, original data, core/C# code, permission behavior, credentials or deployment were changed. Existing package/ZIP and other old security limitations are not declared resolved. GitHub branch metadata currently says `protected:false`; ruleset listing returned 403 for plan/access, so no claim is made of exhaustive ruleset visibility. Only normal PR merge is permitted; no bypass or force update.
