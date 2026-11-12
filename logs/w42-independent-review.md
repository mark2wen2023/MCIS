# W4.2 independent review

Baseline: 096e3d2. No deployment/publication performed by acceptance agent.

| Layer | Freeze1 | Freeze2 |
|---|---|---|
| In-process API (TestClient, not network) | 71 PASS | 71 PASS |
| Real localhost HTTP | 1 combined scenario PASS | 1 combined scenario PASS |
| Real Chromium | 3 groups PASS, 1 FAIL | 6 groups PASS |
| Freeze integrity | 13/13 | 13/13 before and after |

W42-A01 = D01: closing an in-flight commit actively aborted its fetch before the server read the body. This did not prove a transaction had committed then rolled back. The original failing assertion was retained and passed on Freeze2. Freeze2 separates commit from cancellable read signals and preserves stale UI isolation. D01 is closed for the tested scope.

Freeze2 includes protocol/budget/failure injection/permissions/integrity/note/package checks, actual HTTP lifecycle and concurrent requests, actual browser local-file gate, double-click, XSS, lost-response read-only recovery, stale case/role/Back/reopen/evidence-selection results, in-flight close isolation, and actual 8MiB upload/save/download bytes with +1 byte rejection. Reviewed 1440/1920 panel screenshots; keyboard test covers entry focus+Enter, not a full accessibility audit.

Published evidence: `w42-independent-freeze1-results.json`, `w42-independent-freeze2-results.json`, `w42-independent-browser-freeze2.log`, `w42-independent-freeze2-precheck.log`, `w42-independent-freeze2-postcheck.log`; freeze manifests `w42-impl-hashes-frozen-v1.txt` (Freeze1) and `w42-impl-hashes-frozen.txt` (Freeze2). Original API warnings, failure stacks, server logs and screenshots remain local-only and are not repository attachments. Results copies retain the original red summary; no assertion was removed.

Limits: all synthetic temporary data; no real evidence/authenticity claim, extraction/registration times distinct; no cross-storage crash ACID or multiworker claim; browser/network closure may leave unknown outcome. W11 unpublished-main combination and W10/W8.4/full service/Web regression are outside these counts and coordinated separately. No re-test was performed solely for this documentation correction.
