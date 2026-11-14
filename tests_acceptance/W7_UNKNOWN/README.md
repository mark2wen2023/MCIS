# Local recommendation create/reply unknown protection

Run node tests_acceptance/W7_UNKNOWN/{create,reply}/{fixed-handler,independent}.test.cjs and cross.cjs. These run 53 actual-source-handler scenarios using synthetic hooks/transport, not a browser. PYTHONPATH=service python -m pytest -q tests_acceptance/W7_UNKNOWN/test_backend.py reproduces three existing backend limitations (identical create/reply retry duplicates, transition retry refusal after prior success), not backend fixes.

Main3aba2bf + PR67 head5069ba3 are preserved. Only RecommendationsPage adds the reviewed create and reply blocks and combined imports. PR67 body CAS files, imports, bodyRevision and mounts remain unchanged. Local independent integration review found exact composition and reran53 scenarios. PR67 HappyDOM46 checks, Python38 cases and tsc/Vite passed; no full repository/CI/browser acceptance.

Synchronous locks last only this component mount. Closing/reopening form, switching case/recommendation, refreshing or new tabs can lose unknown state. UI warns against replacing unknown requests with new submissions. No sensitive draft persistence, global deduplication or server idempotency added. Current identity headers are untrusted, not production authentication. No deployment/merge.

Success refresh/cancel callbacks are isolated from submission catch; callback failures do not relabel acknowledged writes as unknown. Independent red assertion preserved. Semantic approval/delivery is not claimed.
