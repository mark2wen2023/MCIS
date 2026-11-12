# Report output A independent disposition

Design pre-review identified two contract gaps: the old report helper did not itself enforce per-source access, and browser ZIP/request/identity validation was underspecified. The revised contract explicitly adds conservative full-case source gating and a strict bounded package protocol. These were design gaps, not alleged runtime exploits. Two-phase transaction and original audit reason binding preserve the existing action shape; no new retention promise is made.

Final frozen scope: 20 implementation hashes matched; 49 independent API/DB tests passed; real-browser two-format downloads, deliberately faulted committed responses and late identity response isolation passed. See `tests_acceptance/REPORTOUTPUT/REPORT.md` for exact coverage, limitations and reproduction.

No confirmed unresolved product defect in the exercised scope. One early pre-freeze browser timeout had no isolated cause and is not called a reproduced/fixed defect. A subsequent test-only wrong403 label was corrected to the actual message while retaining no-download and audit-count checks. Neither is hidden or counted as a product fix.

Acceptance does not promise server original retention, guaranteed client save, idempotent regeneration, trusted identity, a signed audit chain, professional approval or complete source provenance. Unknown delivery can leave an export event committed; explicit regeneration can add another event. Non-exhaustive mutation/concurrency and actual-vs-scaled budget limits remain documented, not silently promoted to coverage.
