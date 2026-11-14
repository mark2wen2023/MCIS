# Independent restored-attachment filename review

Reviewed isolated changes in working_records_archive filename/router and evidenceIntake
history/panel against `contracts/restored-attachment-filename.md` (2026-11-14).
Reviewer did not modify implementation. No blocking defect found in this slice.

Executed independently:

```
service/.venv/bin/pytest -q -p no:cacheprovider tests_acceptance/RESTORED_ATTACHMENT_FILENAME/test_independent.py
web/node_modules/.bin/esbuild tests_acceptance/RESTORED_ATTACHMENT_FILENAME/frontend-independent.ts --bundle --platform=node --format=cjs --outfile=/tmp/mcis-restored-independent.cjs --log-level=warning
node /tmp/mcis-restored-independent.cjs
```

Results: **20 Python tests passed, zero skipped (0.32 s)**; **14 frontend assertions
passed**. All data is synthetic. Frontend fetch is simulated; Node executes actual
transport/parser functions, not a browser. Independent tests supplement, rather than
relabel, the implementer's report-generation, archive-restore and loopback tests.

Coverage:

- Unicode and 128-codepoint basename boundary; quotes/percent signs and extension preserved;
  URL-like percent text decodes exactly once, never into directory separators.
- Canonical binding rejects changed case, byte size, version, role, operator, digest,
  evidence identity, raw bytes, request key and extra unknown binding fields.
- Invalid metadata types, traversal name and isolated surrogate fail with controlled409.
- Client rejects controls, separators, overlong headers, duplicate/extra parameters,
  overlong or invalid UTF-8 sequences; legacy filename fallback remains sanitized.
- Aborted download rejects even when mocked fetch returns valid bytes and digest.

Code inspection confirms filename selection occurs after current authorization and byte
hash checks, before the existing Access audit; it rebuilds binding using existing intake
validation and compares canonical bytes/request digest. Response remains opaque octet-stream
with no-store; UI uses the validated transport filename and accurately says download initiated.

Limitations: no independent browser execution, no disk-save verification or external
network. Existing filename validation does not certify file contents, publisher identity,
platform-specific filename behavior or historical authenticity. Registration is explicit;
generated report bundles are not automatically retained. The implementation agent's
reported unrelated HFACS failure and browser sandbox startup failure were not independently
rerun here and are not counted as passing. No browser workaround, deployment or merge.
