# Legacy dual-field expected checksum, isolated candidate

Base1759643db18951afa150eaa6bcb2662a8e3c2f2a; local/legacy-evidence-checksum at
/workspace/mcis-evidence-checksum. No commit/push/PR/merge/deployment. No private case data,
production services or model calls. Only synthetic fixtures, real local API/SQLite/files.

## New contract and actual change

Previously contentBase64 took precedence and ignored supplied sha256. Original OpenAPI
only required SHA without content; no prior dual-input guarantee is claimed. New behavior
checks nonnull supplied SHA as exactly64 ASCII hex, compares case-insensitively with the
SHA256 of decoded bytes, rejects format422 INVALID_SHA256 or mismatch422
EXPECTED_SHA256_MISMATCH before file/evidence/custody/audit writes. Strict Base64 and
existing authorization still run first for schema-valid requests. Framework request-type
validation can return422 before route authorization, unchanged from the prior endpoint. Content-only and SHA-only behavior remain; null
SHA is absent, empty content is a real zero-byte file. Lowercase recorded digest retained.

Product delta: import re plus5 lines in evidence/router.py. OpenAPI describes nullable
content/SHA, empty bytes, dual-field checksum/new compatibility and422 Problem response.
New contract and old proposal status updated. No changes to GET policy, transaction scope,
container/digest protection, import/export, new Intake or resource caps.

## Client compatibility

See CALLERS.md for repository review. Existing web and stage-demo evidence upload use
new Intake; no used legacy dual-field mismatch client found in repository. One prior
independent test deliberately documented ignored-SHA behavior; changed to matching SHA
under the new explicit contract, with new mismatch regression instead. Its historical
committed reports are unchanged. Unknown external caller usage was not observable:
placeholder/mismatching dual-field callers now intentionally fail422. This is not universal
backward compatibility or a rollout authorization. No known used client break was found.

## Tests

New28-case baseline on1759643:14 failed/14 passed in3.32s. Failures retained in baseline.txt.
New contract now rejects these previously accepted mismatches and malformed expected SHAs.
Focused command (service/):

    .venv/bin/python -m pytest -q -rs --import-mode=importlib tests/test_legacy_evidence_checksum.py tests/test_legacy_evidence_base64.py tests/test_content_base64_integration.py tests/test_content_visibility.py tests/test_package_policy_roundtrip.py tests/test_package_export_policy.py tests/test_evidence.py tests/test_evidence_intake_w42.py tests/test_contracts.py ../tests_acceptance/legacy-evidence-base64/test_independent.py

220 passed,2 missing-.NET skips in43.86s. results.txt retains output.
Independent40 passed in5.72s:12 independent plus28 implementation (overlap, do not sum).
Real loopback HTTP checks authorization/encoding priority, empty mismatch zero writes and
uppercase empty checksum success. Also mixed-case, nonUTF8,2MiB+1, existing-file protection,
lone-surrogate/nonstring rejection, SHA-only metadata and OpenAPI3.1 nullable/422 refs.
Frozen implementation and OpenAPI hashes unchanged; independent evidence is separate.
Expanded command is run-regression.sh, result appended below when complete.

## Limits retained

Checksums establish byte consistency only, not source authenticity or trusted identity.
Role headers remain spoofable, not production SSO. Full SQLite write locks and aggregate
JSON/file memory use remain; no new upload cap/performance claim. Offline snapshot future
revocation and old missing-digest refusal remain. No .NET or browser acceptance. Previous
5 baseline failures/2.NET skips are not implied fixed by focused passes. No remote changes.

## Actual expanded result

622 passed,5 failed,2 skipped in146.11s (expanded.txt). Failure headings were compared
mechanically with1759643 tests_acceptance/content-base64-integration/regression.txt and
match all five: HFACS report archive plus test_interview_list_summary, test_redaction_by_role,
test_crosscheck_requires_confirmation and test_statement_add_and_review. Two skips require
.NET. No new failure in this compared scope; existing baseline is not fully passing.
