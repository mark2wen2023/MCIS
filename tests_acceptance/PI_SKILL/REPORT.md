# Version-pinned investigation extraction Skill

## Business outcome
The existing bounded Pi investigator now executes a named built-in source-extraction procedure, not an ad hoc prompt. It reads authorized text, proposes statements, validates exact original citations, stores only the trusted host's accepted PendingReview candidate, and passes that immutable result to the protected per-item review UI and supplemental archive. Investigators can see the Skill ID, version and content digest in current and historical records. This remains an isolated component/host trial, not a mounted production workbench.

Skill: `mcis.source-extraction.readonly` / `1.0.0`. Manifest digest: `9a8b6a55aaf56f7c45243effb712cc3177e19cfc9984eff052f35e4017ab1dcf`.

The pinned manifest includes actual completion-mode prompts, tools, limits, steps and output policy. Remote egress authorization binds the entire manifest and its reference alongside source/session/config. Every remote operation recomputes current authorization, and working save rechecks the same host-owned execution snapshot. Content/permission/source changes fail closed. Arbitrary imported/user/model Skill selection does not exist. Code release and authorization are required for changes.

## Boundaries
LLM proposes; deterministic tools read and check structure/quotes; host owns authorization and persistence; investigator review is outside the model tool loop. No liability conclusion, official fact activation or new write tool. Prompts preserve approximations, subjects and distinction between absent records/negation and command signals/physical action, but these instructions are NOT a semantic-support validator. Exact quote match does not establish that the source supports a conclusion or that the source is true. This is not legal or professional certification.

New working execution profile v2 requires a strict Skill reference. v1 records remain unchanged and display missing Skill version rather than backfilled attribution. The existing archive-v2 wrapper is unchanged. Unknown syntactically valid historical references are inert, unverified declarations, never registry requests or authority. Scripted review remains explicitly scripted.

## Verification
Native implementation and separate native independent reviewers, not separate Codex application sessions. Backend final primary 27/27, independent 16/16; UI primary 26/26, independent 31/31, prior Pi UI 30/30 and archive28/28, strict TypeScript passed. Node runtime87/87. Counts overlap and are not additive unique coverage.

Explicit fixture run `7dac16e4-0def-49f8-ba68-60682d6921f8` used the actual Pi/stdio/Python/SQLite/React-HappyDOM/review/archive path: 3 mocked model rounds, 2 tools, 1 proposal/citation, providerRequests=0. Skill reference equality and original candidate/citation equality verified through saved read, remount, export/import and historical read. Cleanup acknowledgement and exit0 required. No fact activation. This is NOT a real-model run or browser-engine test.

Prior real run `5d3b415b-9e8b-4c5e-aa98-9c978834fd85` remains evidence for the older unversioned chain, not for this new Skill version. No new DeepSeek request was sent by this slice. Historical fourth-run unknown remains unknown. No CI, production authentication, permanent user storage, full-case accuracy, merge or deployment claimed.

Final related Python regression: `test_pi*.py` as collected at run start, **198/198**, zero skips, 147.39s. Separate independent Skill16/16 was run by the reviewer; no unique-count aggregation is claimed. Source hashes remained frozen. This is selected Pi coverage, not the full service suite.
