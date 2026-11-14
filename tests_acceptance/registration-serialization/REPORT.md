# Minimal legacy registration serialization candidate

Basea38d7485f2e2a50496d3c624de6ddcc081967720; isolated local/legacy-registration-serialization
in /workspace/mcis-registration-serialization. Separate from unchanged-product aggregate
study tree; no commit, push, merge or deployment. Synthetic local files/requests only.

Aggregate TCP repeats exposed500 UNIQUE evidence_items(case_id,key), successful responses
sharing overwritten metadata, and orphan files. Before diagnostic three rounds each had
three201/one500,4 files but metadata counts1,1,3 and custody/audit3. tcp-before.jsonl retains
actual observations. A deterministic overlap regression on the unchanged base returned four
201 responses all EV-001 (baseline.txt,1 failed in0.40s). This was not capacity refusal.

The only product delta wraps the entire existing register_evidence session in WRITE_LOCK
and calls existing begin(s) before case/policy/next_id/file writes. SQLite writer reservation
protects ID allocation across processes, while policy is read under that same reservation.
No shortened transaction, new business cap, source decoding change or attachment permission
change. Existing strict Base64/SHA and metadata-only/empty-file semantics remain.

Actual self regression196 passed/2 missing-.NET skips in34.79s (results.txt):

    cd service
    .venv/bin/python -m pytest -q -rs tests/test_registration_serialization.py tests/test_legacy_evidence_checksum.py tests/test_legacy_evidence_base64.py tests/test_content_base64_integration.py tests/test_content_visibility.py tests/test_package_export_policy.py tests/test_evidence.py tests/test_evidence_intake_w42.py tests/test_policy_write_busy.py

Three same-workload fresh-server TCP after-runs (4x8MiB POST) all returned four201, no DB
errors, and counts4 evidence/4 files/4 custody/4 audit. tcp-after.jsonl preserves observations;
measure_diagnostic.py is copied unchanged from the baseline harness and imports this tree's
product through service PYTHONPATH. This is behavioral reproduction, not throughput evidence.

Independent86 passed in15.41s (8 new independent cases+78 regressions, overlapping self suite).
Two actual loopback server processes share one SQLite DB:8 concurrent successful registrations
have8 distinct IDs and matching metadata/files/custody/audits. Same-path requests yield201/409
without overwrite; prior revoke denies without write, strict invalid input releases reservation,
empty/nonUTF8/uppercase expected SHA remain compatible. Product freeze unchanged. See separate
registration-serialization-independent/REPORT.md for commands and evidence.

Limits:JSON/Base64 requests may already be buffered/decoded before the lock; this is NOT
aggregate memory/admission control and may increase waiting. Source RSS/load results must
not be labelled improved production performance. Full writer lock can block policy update;
a blocked update has not committed revocation. No automatic retry or unknown-commit reclassification.
SQLite reservation guarantee is not an assertion for other database backends. Filesystem/DB
are not crash-atomic: later failure may leave a file, and this patch does not add potentially
unsafe deletion cleanup. Unauthenticated/spoofable roles, true source identity and deployment
performance remain unresolved. Earlier5 baseline failures/.NET skips remain historical;
this narrower196-case run does not claim a complete product suite pass.
