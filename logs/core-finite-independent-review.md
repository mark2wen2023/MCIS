# Independent acceptance: finite core response JSON (2026-11-12)

## Verdict
Accepted as a narrowly scoped response-decoding fix. No blocking defect found. The JSON decoder callbacks reject NaN, positive/negative Infinity and floats overflowing to infinity at every parsed position before downstream envelope use. Finite floating-point conversion still uses Python float, integer parsing is unchanged, and strings/preamble/extra fields are not normalized. Existing ValueError handling converts failures to CORE_BAD_OUTPUT/502; existing HTTP wrapper supplies a fixed safe message.

All three entries of `logs/core-finite-impl-hashes-frozen.txt` matched before and after independent verification. Reviewer did not edit implementation, contracts or implementation tests.

## Executed independently
- `tests_acceptance/CORE_FINITE/test_independent.py`: **43 passed**, 4.08 s. Output `logs/core-finite-independent.log`.
  - 30 HTTP cases: five invalid numeric tokens × nested result / extension / error-detail placement × version / align routes. Real FastAPI application through TestClient, synthetic subprocess output, fresh temporary SQLite with seeding disabled. Exact 502/code/message, no marker leak, and unchanged database file SHA256.
  - Six numeric boundary cases: negative zero, both largest finite doubles, smallest subnormal, negative underflow, large integer. Types, float hex representation and standard JSON decoding matched exactly.
  - One test contains **400 deterministic randomized finite-envelope comparisons**, preserving float hex, large integers, nested arrays, booleans/null, extension strings and Unicode. Preamble includes invalid-looking tokens, demonstrating only the final line is decoded. These are comparisons within one test item, not 400 test items.
  - Five valid domain-error mappings retain code/message/status and finite extensions.
  - One HTTP success case preserves strings resembling non-finite numbers and a large finite number.
- Prior independent/implementation HTTP safety suites, unmodified at `/workspace/shared/mcis-security-work/tests_acceptance/HTTP_CORE_ERRORS`, loaded with explicit candidate-service PYTHONPATH: **75 passed**, 2.93 s. Output `logs/core-finite-legacy-http.log`.
- Both runs emitted only the existing Starlette/httpx deprecation warning.

## Limits
This review tests the Python process-response boundary with synthetic process output, not actual malformed C# execution or browser/Unity behavior. It does not establish a global resource budget, production authentication, removal of raw align file-path support, or rejection of all malformed output shapes. Extremely deep JSON and oversized subprocess output are outside this slice. Full service and actual-core integration regression belongs to the coordinating implementation run and is not claimed here. No publication, merge or deployment was performed.
