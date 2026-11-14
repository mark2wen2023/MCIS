# Independent validated-reference completion review

This is a new explicit completion protocol, not a relaxation of the default
`exact` protocol. The completion mode is bound into the disclosure and approval
digest. In reference mode the only final output is the exact fixed completion
marker. The trusted Python host checks its own canonical terminal reply,
no pending call/model, current source/session/scope, previous source read and
the latest successfully validated candidate. It then revalidates that stored
candidate; the marker itself is neither a credential nor an evidence payload.

Independent review found Node retained a prior validated candidate until the
next validation call completed. A thrown tool call could therefore leave that
old candidate eligible for final dispatch on Node's side (Python still rejected).
This was fixed by clearing the Node slot before invoking validation. Both
invalid-return and thrown-error cases now independently reject final dispatch.

## Offline results

- `test_pi_reference_independent.py`: **12/12**, zero skips, 12.86s.
- `reference-independent.test.mjs`: **8/8**, zero skips.
- Updated `test_pi_working_probe_independent.py`: **4/4**, zero skips, 3.85s.

Coverage: exact-mode/marker refusal, reference-mode/candidate refusal, whitespace,
newline and JSON-wrapped marker rejection, latest failed validation invalidates
previous success, completion-mode approval mismatch, source-read requirement,
source/session revocation, immutable server-candidate working save, and actual
mock-protocol/SQLite temporary cleanup before final success output. Node tests
exercise actual Pi runtime with mocked host/provider responses; Python uses real
trusted-host state and SQLite with mocked remote transport.

No remaining blocking issue in this reviewed scope. No real model/API request,
credentials, production UI, CI, merge or deployment were used or verified. The
existing exact-mode limitation documented earlier remains true for that mode;
reference-mode evidence must be labeled separately. Temporary success cleanup is
verified, not cleanup after SIGKILL or host/container failure.
