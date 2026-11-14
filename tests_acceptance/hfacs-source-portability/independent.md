# Independent HFACS source portability review

Verdict: PASS for SDK-free source-integrity portability; genuine C# execution/rebuild remains unverified in this review. Read AGENTS.md/handoff, frozen helper/tests and test_cli.py diff. No build.py, C# sources or service implementation changes are included.

Fresh independent execution:

```sh
service/.venv/bin/python -m pytest -q tools/mcis-hfacs/test_source_integrity.py
service/.venv/bin/python -m pytest --collect-only -q tools/mcis-hfacs/test_cli.py
sha256sum -c logs/hfacs-source-portability-impl-hashes-frozen.txt
```

**19 passed in0.06s**; **7 real CLI tests collected in0.01s, not executed**; **3/3 frozen hashes matched**. Logs: independent-tests.txt, independent-collection.txt, independent-hashes.txt. No SDK installation or fake core was used.

Independently extracted tests_acceptance/W184/verified-impl-sha256.txt with git show at its committed history5ca1261163f8fc4858a118072297f1e80f3a2b3c. All seven unity source pins equal the new helper constants and the historical record is unchanged (independent-history.json). This separately anchors them to committed history rather than trusting only a candidate's newly generated manifest. These are reviewed local-repository pins, not a cryptographic author identity or external signature.

The test removes only the hard-coded sibling checkout comparison. It now checks the seven mandatory pins and local bytes before manifest deletion, and again after real concurrent rebuild. Existing three-worker execution, output equality, complete before/after manifest equality and per-input local hash loop remain. Extra adapter input bytes are also still checked against receipt digests. Missing required pins/files, changed sources, and source+receipt jointly recomputed changes all fail under the SDK-free tests. Standalone temporary sources work without Git metadata, a sibling checkout or SDK. No original business/core assertion or real invocation was replaced with a simulated success or skip.

The helper is test-only and expects trusted local root/manifest paths. It is not a hostile-upload path validator, concurrency snapshot, physical immutability guarantee or approval for changing historical core; changed legitimate core pins would require explicit new review. Matching source hashes does not prove binaries/core behavior. The original seven test_cli cases still invoke the genuine wrapper when run; this review only collected them. Real SDK/build/protocol/archive validation remains separately required, and existing SDK/HFACS blockers are not resolved by portable source checks.

No frozen implementation edits, commit, push, merge, deployment or installation by reviewer.
