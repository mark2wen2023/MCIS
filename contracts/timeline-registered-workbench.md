# Registered-evidence timeline workbench (draft)

The evidence page includes a read-only investigator panel for the existing
`POST /api/v1/cases/{caseId}/timeline/registered-align-preview` service.
Select 1–4 local intake evidence IDs, map one timezone-aware timestamp and one
Heading/COG/SOG column per source, confirm mapping/units, then compute. The panel
sends evidence IDs, mapping and explicitly unverified comparison declarations, not user-supplied paths, hashes or approval claims. See timeline-comparison-scope.md. It displays the server's byte hashes and existing conflict/calibration
preview. Cancellation discards local results; it does not promise server abort.

Identity, case, source metadata/path or mapping changes invalidate results.
Response case/source IDs and transient/no-approval scope are validated. Server
policy, current bytes, registration and custody remain authoritative. Client
controls are not authorization. No persistent binding receipt, fact approval,
clock correction, evidence edit or timeline write is added. An empty conflict
list is not proof of agreement. Different ship/object measurements still need
investigator screening; no automatic vessel matching is supplied.

## Validation scope

- TypeScript + Vite production build passed (existing large bundle warning).
- Independent HappyDOM React lifecycle tests use controlled fetch, not a real
  browser or end-to-end network.
- Separate local uvicorn + actual W2 HTTP acceptance registered two explicitly
  synthetic CSV files (45 and 50 degrees), returned 200 and a 5-degree conflict,
  with both sources uncalibrated and observationApproval=not_assessed. This is
  not real accident evidence and is not a live LLM test.
- Cloud browser could not reach this execution workspace's localhost port
  (ERR_CONNECTION_REFUSED). Browser appearance and browser-to-service flow are
  **not accepted yet**. No public deployment was used to bypass that limitation.
- No CI run or full-repository test pass is claimed by this slice.
