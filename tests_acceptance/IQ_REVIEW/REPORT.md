# IQ-1B current hypothesis / verification read snapshot

Base PR47 `11c6b41fad9ff4d308c5fddc4e25490299286fb4`, isolated new branch. Changes only IQ router, new projection, contract/OpenAPI and tests/docs; no semantic_support changes or mutations.

Implemented GET /investigation-issues/{issueId}/review: returns current issue plus one row per hypothesis, joining only its current-round/current-version recorded verification and full activity/result/source/actor text. No verification means null, never a negative conclusion. Prior overwritten records remain in event history. Missing/misbound current event fails closed 409. Existing authorization and historical/current source checks remain; BEGIN IMMEDIATE is delegated to existing access helper through JSON response construction.

Original 29 API tests passed before changes. Final original29+new12+independent5 =46 passed (local FastAPI TestClient/SQLite). Independent test covers concurrent permission revoke waits for response construction, historical source removal, read-only policy, unsorted source refs, and exact text preservation. Initial test collection failed due to import path and was corrected to package import; initial ordinary BEGIN design was rejected by independent review and removed before concurrency tests. No pre-fix executed concurrency failure claimed. See INDEPENDENT.md.

146 unchanged runtime files were matched against base Git blob hashes (materialization-only extra trailing newlines corrected). No production database, model API, real-case model quality test or browser run occurred. No actual identity or audit-chain certification. Archive/full UI integration remains a merge blocker inherited from PR47. This is additive backend groundwork, not complete problem-card product delivery.
