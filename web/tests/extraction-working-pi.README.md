# Pi per-item working-review UI trial

The existing extractionWorking port now parses an explicit Pi remote-deepseek
union without relabeling it local or fixture. It keeps exact quotation strings,
source binding, configured model and completion mode, and a bounded fixed-enum
protocol trace. Unknown fields, credential-bearing/arbitrary trace payloads,
wrong source/provider assertions, altered immutable history, invalid trace order,
wrong totals, invalid proposal kinds and duplicate citations are rejected.

The UI displays model/runtime identity as unverified. Review-origin labels keep
scripted_test separate from user_submission_unverified; missing old metadata is
legacy_unspecified, never inferred as a human review. An authenticated submission
is not proof of a human identity. Existing unknown-save exact retry, navigation
locks, late-context guards and append-only history checks remain.

## Local verification
- New parser + HappyDOM test:30 checks pass (mocked responses).
- Prior per-item UI24 and independent port9 checks pass.
- Strict TypeScript for both modified product files passes.
- Prior actual fictional React/stdio/Python/RPC/SQLite integration passes.
- New actual Pi-format integration passes: mock transport drives PiWorkingHost
  and SQLite, creates scripted revision1; real PersistentExtractionRPC -> stdio
  -> React HappyDOM lists/opens original proposals, appends per-item user-input
  revision2, remounts/reopens, appends revision3, preserves original+all versions.

The test-only pi-working-rpc-fixture.py never contacts DeepSeek; its wire shape
remains remote-deepseek to exercise the actual Pi schema, explicitly labeled
mock-pi-provider-not-real-model in test setup. This is not real inference,
production authentication, mounted browser UI, CI or deployment.

Reproduction (from web/): bundle each test using node_modules/.bin/esbuild with
--bundle --platform=node --format=esm --packages=external and createRequire ESM
banner. Set MCIS_HAPPY_DOM_PATH to installed happy-dom/lib/index.js. Integration
also requires MCIS_HOST_PYTHON and MCIS_HOST_SERVICE pointing to the chosen test
Python and service checkout. Tests do not acquire credentials or fallback to any
provider. Existing unknown-outcome retry behavior remains scoped to original
operation IDs and must not be interpreted as canceling an already-saved record.

Independent review added27/27 negative/protocol checks, reran primary30,
previous24/9 and strict TypeScript, all passing. It identified missing proposal
kind enum and unit:null rejection; these were fixed before final review. The
strict Pi parser is exported for archive UI reuse; archive history must retain
its own untrusted/no-activation labeling and format-version gate.
