# Independent review of the real-run artifacts

## Disposition

**Suitable for submission as a research result, with the limitations already stated in BLIND_RUN.md.** No blocking inconsistency found. This reviewer made no new model request and did not change the implementation or original run report.

Reviewed run: `36c8d113-e34c-458f-bb89-2cf66abe1486`.

## Independent checks performed

- Parsed fixed corpus and all result artifacts. Re-ran `evaluate.evaluate` offline with the saved predictions and empty reviewer template; the resulting object is exactly equal to `blind-real-comparison.json`.
- Saved predictions exactly equal the accepted run's predictions. All 11 original case IDs are present exactly once, with no extra or missing case. The frozen opaque-case input equals a fresh projection from the pinned corpus, and the host mapping restores original IDs only in final predictions.
- Recomputed corpus SHA, canonical input digest and manifest digest. The frozen input, accepted run and ready receipt agree:
  - corpus: `77cdbdf3f2656aa57b0772fadc909671bf5bbfbd7c480a3fcbb1cc79460ad19b`
  - input: `b8d5ae6ea1e6afbdf72c4dbfb0ccb99de03a518dae78b1c592e91c9833db4d85`
  - manifest: `5a553a8dca41f1cbd1242f261d535aa66e19070c09f3b11abea5ec53c889bc9a`
- Receipt has exactly one ready, sequential attempts 1/2/3, predictions validated, cleanup verified and Node protocol complete. Run IDs match throughout. Accepted result records 3 attempts, 3 completed real requests, 3 model cycles, 2 tools, real Pi, non-mocked transport and Node completion. No failed/unknown or additional retry entry appears in these artifacts.
- Reviewed the audited host path: accepted output is emitted only after child exit 0. The coordinator's observed Python exit 0 is reported by the parent; the saved JSON does not independently encode a shell exit status. Receipts remain unsigned operational records, not external attestations.
- Scanned the input/run/receipt/prediction/comparison/report files for API-key, bearer-token and private-key patterns; none found. The receipt contains only bounded operational metadata and hashes, not source text or model rationale. Pattern scanning alone is not a general proof of absence of every possible secret.

## Interpretation verified

The two differences from provisional suggestions are exactly `oil_false_precision` and `rudder_blank_means_order`, both model `conflicted` versus provisional `insufficient`. These are comparisons to assistant-constructed suggestions, not certified model errors or an accuracy denominator.

The two unlabelled items remain `not_labeled`: `oil_qualifier_omitted` receives model `supported`; `oil_quote_tampered` receives `conflicted`. The omission of the approximate qualifier needs adjudication. Exact-quote location is a separate axis from semantic support. No expert reviewers were supplied, and expert/factual verification and fact activation remain false.

BLIND_RUN.md correctly distinguishes actual upstream model execution from the offline comparator's `realModelCalled:false`, fixture engineering tests from model observations, methodological guidance from a zero-shot benchmark, and configured provider model identity from independent identity attestation. It does not report authoritative accuracy or expert consensus. This is an isolated research harness, not a production Skill deployment or expert-panel validation.
