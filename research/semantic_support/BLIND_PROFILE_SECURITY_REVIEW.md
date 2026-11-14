# Independent second-profile safety review

Disposition: **no blocking issue; safe prerequisites satisfied for one separately authorized real run of `jiangxin9-v1`**. No real model request was made during this review. No automatic retry is authorized by this conclusion.

Frozen host SHA256: `b333ef10159de37ab4cd1b6bb65fea72c27eda23fc83f8fdde3a26976c2e5650`.

## Binding

The new profile is a code-owned enum, not a user path/URL or arbitrary corpus. It resolves to the fixed `jiangxin9-provisional.json`, raw SHA256 `f7a1a69f2f2bf51236ecfc734952c8249e87b0bbaf0e8913b006167900bff782`, exact count 8. Profile filename, hash, count, projected input and original-ID mapping are checked. Unknown/unregistered profiles fail before credential reading/provider startup. Runtime profile/input/mapping mutation fails closed, including after a provider response.

Two distinct hashes must not be confused:
- Frozen `jiangxin9-blind-input.json` whole-file SHA256: `56e09066bf71aa74eb786d4f6fd534458493f1122d525dd3f7427efb1a33352d`.
- Host's canonical cases digest: `a754aaeb1ff5a2d2852186bc513542356a3c93f44e00831ae7a686f4c6383c96`.

The initial independent test used the former where the latter was required. After independent recomputation, that test assertion was corrected. This was a reviewer test expectation error, not a source change.

## Validation

New independent suite: **16/16 passed**. Combined with existing independent protocol and primary profile/host suites: **61/61 passed**, zero skipped, 2.24 seconds. Node's two existing scripts also passed (six runner scenarios plus CLI coordination).

Coverage includes fixed projection equality; no original semantic IDs or answer-label/rationale fields in model cases and complete captured provider histories; arbitrary path/URL rejected without file loading; corrupted fixed filename/hash/count rejected; exact profile prediction coverage; cross-profile count mismatch; post-request profile/mapping/input mutation; actual official Pi fixture bridge with 3 simulated model cycles, 2 tools, 8 predictions and zero real requests; matching profile-specific receipt hashes and cleanup.

Default `yangze22-v1`, its old corpus/input digest and frozen manifest/prompt remain unchanged. Node code is unchanged. Previously reviewed canonical history/call IDs, latest-validation completion marker, secret only in Python memory, receipt fsync before provider ACK, fixed endpoint, bounded calls/deadline and no retry continue to pass.

## Interpretation boundary

This second case consumes assistant-transcribed public source text, not direct image/video/PDF model perception. A combined source package is not a claim that its excerpts occur together on a single original page. This security review does not certify source transcription or semantic labels; source-page review is separate. Suggestions remain provisional, prediction validation is schema/coverage only, and no accuracy, expert truth or fact activation is established by fixture tests.

## Appendix: independently checked real-run artifacts

Run `33acba11-3c47-48d3-9ab5-64f103ce0c64` is internally consistent and suitable for submission as a limited research observation. The reviewer did not invoke the model again.

Checks performed against `jiangxin9-real-run.json`, predictions, comparison, receipt, original provisional corpus and frozen blind input:

- Offline `evaluate.evaluate` recomputation exactly equals the saved comparison object.
- Saved predictions exactly equal the accepted host predictions, with 8 unique original IDs covering the host's complete opaque-to-original mapping, no omissions/extras.
- Raw corpus hash, canonical cases digest and manifest digest match the fixed profile and receipt. Frozen input cases exactly match fresh projection; this file contains cases/coordinate convention only, while the manifest is bound separately by code and receipt.
- All receipt entries carry the same run ID, with exactly three sequential real-request attempts 1/2/3, then validation, cleanup and Node protocol completion. Accepted host output records 3 completed real requests, 3 model cycles, 2 tools and Node completion, non-mocked transport and real Pi. No additional attempt, failure or retry is present in these artifacts.
- Reviewed code emits accepted output only after Node exit 0. Parent coordinator reported observing Python exit 0; the artifact alone does not externally attest shell status, provider model identity or the absence of activity outside this recorded run. Receipts are unsigned operational records.
- All `jiangxin9-*.json*` artifacts passed API-key/bearer/private-key pattern scanning. This does not constitute a universal secret detector.

These are actual upstream provider-run artifacts, unlike the earlier fixture safety tests. `realModelCalled:false` in the comparison identifies the offline evaluator, not the upstream run; prediction origin remains `model_output_unverified`, with empty reviewers and no expert certification or factual activation.

There is one difference from provisional suggestions: `distance_false_precision` is model `conflicted` versus provisional `insufficient`. It is a judgment distinction for expert review, not a certified error count or accuracy measure. No cases are unlabelled in this second provisional set. The material remains AI-transcribed text from public report pages, not a visual-model performance test or a full accident investigation.
