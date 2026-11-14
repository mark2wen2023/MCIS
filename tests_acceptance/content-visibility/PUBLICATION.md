# Content visibility review branch publication

The coordinator explicitly authorized publishing this isolated GET repair after independent
review. Earlier no-push statements describe the local-only stage. Intended sole parent:
099185719d01e31e440b3473310f30a3aa74157a (main-package-policy review), itself directly based
on real main3aba2bf03e393909c611489ae573a887087637ac. No97-commit stack is imported.

This branch and Base64 branch codex/legacy-evidence-base64-review at
70f7067e8831a4d79eff8f613b7e45f349cc9b0c are SIBLINGS with common parent0991857. Neither
includes the other's fix. They touch separate areas of the same evidence/router.py: this
branch adds two GET visibility lines; Base64 changes POST decoding. A future combined
candidate needs explicit integration review; none was merged here.

Product hash remains frozen. Synthetic cases/bytes only. Regression112 passed/1 missing-.NET
skip; independent10 passed. Prior broader5 baseline failures and2.NET skips are not claimed
resolved. Role headers remain spoofable, not real authenticated identity or SSO. Long SQLite
write locks, aggregate memory, recorded-source authenticity and offline snapshot revocation
limits remain. This is policy consistency repair, not production security acceptance.

Publication creates a review branch only; no PR creation, merge or deployment.
