# Expected checksum review branch publication

Coordinator authorized publishing this local candidate after validation. Earlier no-push
statements describe the local-only stage. Sole intended parent:
1759643db18951afa150eaa6bcb2662a8e3c2f2a, verified against remote content-base64-integration-review.
One new commit; no unrelated history. Product code delta is only the expected checksum
validation in evidence/router.py; OpenAPI and supporting contracts/tests/review evidence
are included. Frozen product and OpenAPI hashes remain unchanged.

Dual-field SHA enforcement is a NEW contract: contentBase64 previously took precedence
and ignored SHA. Content-only/SHA-only and matching dual inputs remain compatible; old
mismatching or placeholder SHA callers now receive422 before writes. Repository web/demo
callers use new Intake and no used legacy mismatch dependency was found. Unknown external
old callers may be incompatible; no deployment telemetry or universal compatibility claim.

Actual expanded622 passed/5 existing baseline failures/2 missing-.NET skips; focused220
passed/2 skips; independent40 passed (overlapping suites, not additive). Five failures
match the parent baseline. Unauthenticated/spoofable role headers, real identity/SSO,
full-duration write locks and memory limitations remain. Checksums do not prove source
truthfulness. This is not production readiness. Synthetic fixtures only; no secrets,
private case records or .env files included. No PR creation, merge or deployment.
