# Durable human working review

Implemented an explicitly provisioned, non-production trusted-host path: generate a checked pending proposal, persist its original quotes/citations/model declarations, append per-item human working decisions, reopen and read prior history, and append revisions without rewriting earlier opinions. Dedicated write grants are separate from issue notebook grants. Default ephemeral UI and old routes are unchanged.

Independent design/source review preceded final acceptance. Real concurrent writers, transaction rollback, SQL append-only triggers, restored Database connections, actor-bound idempotency, revocation, binding changes, closed-host suppression and cross-host retry were tested using fictional fixtures.

Final local verification:
- 406 related Python regression tests passed, zero skipped, 194.94 seconds.
- An additional independently authored 16-test review suite passed, zero skipped, 10.88 seconds. These tests were added after the 406-test collection started and are reported separately, not falsely included in that run.
- One existing Starlette/httpx deprecation warning per run.
- Frozen implementation hashes are recorded in independent acceptance reports.

No real LLM/API call, production authentication, browser UI connection, CI result, merge or deployment is implied. `saved:true` means a working record only. Original proposals remain Draft and neither human adoption nor generated citations establish facts. When original source/record/policy changes, history is retained but content access fails closed; this does not mean the earlier save failed. Working history is not yet included in `.mcase` or issue archive export. Cross-host inference is not guaranteed exactly once, even though database operation IDs prevent duplicate stored effects.
