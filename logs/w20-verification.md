# W20.1 verification summary

## Scope and provenance

Started from remote main `0a29f28eeabae8087978de000caf47e5fe2aff30`; service and contracts materialized via the authorized GitHub connector and checked against Git blob SHA-1 identities. W5 merged main `27f4825fae2d6470ef15b7617e49a089447bd903` was integrated without changing its implementation.

Changed functionality is isolated to `service/mcis_service/agents/`: a real opt-in local OpenAI-compatible HTTP client, source-bound people_ops extraction, and human-only reviewed append to interview statements. There is no W5/W9 UI edit, external endpoint, credential, automatic conclusion adoption, deployment, OCR, ASR or video processing.

## Passed at W5-integrated v2

- Service suite: **565 passed** (`logs/w20-service-full.txt`), using existing dotnet SDK via `DOTNET_ROOT` and `MCIS_DOTNET`.
- Focused W20 + existing contract/redaction tests: **43 passed** (`logs/w20-selftest.txt`).
- Independent acceptance: **23 passed** (`logs/w20-acceptance-v2.txt`), frozen files unchanged before/after.
- v1 independent acceptance originally failed three boundary checks (four cases): overlapping quotation uniqueness, private fragment/name overlap, invalid JSON in Modified. All retained and now passing; see `DEFECTS/W20.md`.

The initial isolated workspace lacked some W14 reference logs, had an old font, and lacked explicit dotnet location. Those test inputs were restored from current-main blob-verified copies, the existing SDK was configured, and the final full suite above passed. No unrelated implementation was modified to make tests pass.

## Honest validation limits

A controlled fake model and a real loopback HTTP endpoint serving controlled OpenAI-compatible responses verify the code/protocol path. **Neither is actual LLM inference.** No actual local model endpoint was available for this task, so semantic extraction quality and actual model behavior remain unverified. Only people_ops is wired; the other five roles remain not_connected. Default is disabled and configured registry status is not a health assertion.

The existing role-header trust boundary remains for local development. This is not production authentication assurance. No secret, real user case, remote model service or deployment was used.

## W9/W5 combined baseline

Exact integrated main: `e8db196982d633579de38bca65ed2cd36d96becc` (tree `d0865b1a12c9f37ed3245abceee439cb8d103cd1`). The W9 vessel POST/schema/source requirements and W5 interview changes are preserved.

- Final full service suite on this baseline: **603 passed**, no failures/skips (`logs/w20-service-full.txt`). Previous W5-only suite retained in `logs/w20-service-full-w5-base.txt`.
- Independent combined W20, W9 real HTTP/storage and W5 tests: **91 passed**, plus schema/OpenAPI **4 passed** (95 total). See `logs/w20-combined-independent-*` and `DEFECTS/W20.md`.
- W20 six implementation hashes still match. W20 does not modify web files; publication is an additive tree over the exact integrated main, retaining its complete UI.

## Final W8.3 baseline preservation

Publication base is main `03e3fb8d7bb982e26f5d43d6f67ef888a61d2a48`, tree `ca5991e109edc5d88fa5092712f4e47386b1bb3a` (W8.3 PR #11). GitHub comparison against e8db196 shows W8.3 changed UI, its dedicated documentation/acceptance artifacts and shared REQUESTS/ROADMAP, but no service implementation or existing schema/OpenAPI. Latest shared records were preserved before appending W20 records. No web file is in the W20 publication allowlist.

The complete service tree tested at 603 passing tests is therefore unchanged by this base update. Final affected regression reruns W20 independent tests, W20 self-tests, contracts and package boundaries: **102 passed** (`logs/w20-final-affected-regression.txt`). All frozen hashes match (`logs/w20-final-hash-check.txt`). No broader frontend/browser test result is claimed for W20; the entire existing frontend is preserved from the reviewed base tree.

Only diagnostics' workspace-root paths are normalized to `<workspace>` in published logs, with original local diagnostics retained outside the publication list. Test outcomes and failure details are unchanged.
