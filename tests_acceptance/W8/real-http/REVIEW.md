# W8.1 real HTTP integration review

Passed 21 checks on canonical source snapshot service plus frozen W8.1 frontend. No API mocks or route interception. Fresh isolated temporary SQLite database seeded by existing canonical service, real Uvicorn on 127.0.0.1:18781 and Vite proxy on 127.0.0.1:5193. Official Chrome headless used. Both processes terminated after run; temporary database removed. No implementation edits, remote operations, deployment, mutations or screenshot capture/upload.

Coverage: actual /cases response of 3 seeds parsed/rendered; 1 fictional and 2 public-report labels; default lobby route and refresh; enter each of Lily/Mary, Haili5 and YANGZE22; exact case URL/metadata; downstream report navigation preserves case (default Lily/Mary intentionally omits query under existing navigationForCase contract); each evidence endpoint returns 200; return to lobby; role switch; no browser runtime errors; six implementation source hashes unchanged.

Command: python /workspace/shared/w8-http-review/real_http.py
Artifacts: real_http.py, result.json, run.log, service.log, vite.log, cases-response.json, requests.json.

Harness-only failures retained: initial Playwright positional argument incompatible with API, fixed to named arg; initial expectation incorrectly required query for default case, corrected to actual existing navigation contract. No product changes were needed.

Limits: development Vite and fresh seeded local SQLite, not production build serving or deployed service. Role headers are existing demo identity, not real authentication validation. Only reads performed; no case editing, .mcase, persistent writes, full module form isolation, Unity or production concurrency coverage. Prior mock-browser negative/error/late-response coverage is separate; this run tests the actual successful HTTP integration.
