# Independent persistent-review UI acceptance

The coordinator independently inspected the strict port and component, then requested two usability fixes before acceptance: decision-only edits must count as dirty, with explicit discard; unknown writes must permit an explicit read-current-state escape without claiming cancellation or resending a new operation. The implementer added both and tests. A separate backend reviewer requested trusted fixture-provider expectation binding; the port and fixture integration now pin that expectation.

Independent port tests: **9 passed**, in `web/tests/extraction-working-independent.ts`. They reject fact activation, an Approved original proposal, fact-verified history, extra author injection in a decision, changed citation, foreign record, rewritten historical opinion, revision rollback, and a consistently forged local-mode response when the trusted host expects a fixture. No signatures or verified model identities are claimed.

Coordinator rerun of final frozen implementation:
- strict TypeScript check passed;
- 24 primary component/port assertions passed;
- actual React/HappyDOM + Node stdio + Python + same-database authorization + temporary SQLite integration passed: two fictional proposals, first complete review, remount UI, list/read, append second revision while retaining first opinions and original quotations.

Hashes:
- `ExtractionWorking.tsx`: `3ab33a2779e21ddc3e7f7286db9cd5538768e90af9d25f65ff40056bb3737f21`
- `hostPort.ts`: `76e4f4805770b811901728aa4bfac2c5e31546d079b34c3d5d3c633ff008c467`

This is not actual browser/native IPC or visual-layout acceptance. It uses fixed synthetic outputs, not real model inference. The trusted fixture keeps its credentials inside Python and creates a temporary database deleted at normal process exit. UI remount recovery within a running host is tested; fixture restart does not preserve its temporary data. No deployment or production identity flow is included.
