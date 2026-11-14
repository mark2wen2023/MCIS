# Legacy content GET visibility repair, isolated local candidate

Base099185719d01e31e440b3473310f30a3aa74157a; local/evidence-content-visibility.
Product delta:2 lines in get_content reuse the same filter_evidence as metadata GET and
package preflight. A hidden item now returns403 before reading bytes or appending successful
Access audit/custody. Original category, archive, recorded digest and ZIP gates remain.
Base64 fix is NOT included; it is a separate branch based on0991857.

Before: independently reproduced exact synthetic byte delivery with source and restored
policy evidence.restricted Remove, metadata403 and export403 but content200; main inherited
same field-rule defect. Evidence is preserved in /workspace/mcis-package-roundtrip/
tests_acceptance/roundtrip-independent, two candidate and two pristine-main failures.
After: the SAME workflow expected-denial tests now pass, no assertion weakening.

Executed from service/:

    .venv/bin/python -m pytest -q -rs tests/test_content_visibility.py tests/test_package_policy_roundtrip.py tests/test_package_export_policy.py tests/test_recorded_digest_delivery.py tests/test_policy_write_busy.py tests/test_report_bundle_attachment_access.py tests/test_evidence.py

112 passed,1 missing-.NET skip in27.31s. Synthetic fixtures, real TestClient/SQLite and
filesystem. Four additional cases: rejection before file read/no audit, same evidence ID in
two cases with different policy, committed cross-connection revoke before reservation,
and read reservation blocking policy PUT then subsequent successful revoke/denial. Existing
policy suite retains rollback and export behavior; existing digest/container regressions pass.

Ordering unchanged: BEGIN IMMEDIATE precedes policy checks. If revoke commits first, read
sees it and denies; if read reserves first, concurrent policy write can return503 with
not_committed only at safe reservation failure, read completes under old policy, subsequent
committed revoke blocks next read and export. No claim that a blocked write already revoked
access; no weakened lock duration or automatic retry. Hash-frozen product unchanged.

X-MCIS-Role is caller-controlled, not trustworthy identity/SSO. This fixes existing policy
consistency only. Long writer lock, aggregate memory, old missing-digest refusal, no private
case/model calls, and offline older snapshot revocation boundaries remain. No production,
browser or all-endpoint acceptance. Broader5 baseline failures and2.NET skips are historical
and not claimed resolved by this narrower run. No push/merge/deploy for this candidate.

Independent revalidation:10 passed in2.37s; frozen hash unchanged. Original source/restore
expected-denial probes copied unchanged now return403 with zero Access audit/custody delta.
Additional cases cover same evidence IDs/different bytes across cases, untrusted embedded
caseId not redirecting target policy, Normal evidence not hidden by restricted rule, and
real second SQLite writer BUSY just before final Access append followed by committed policy
PUT and next-request denial. See tests_acceptance/content-visibility-independent/.
