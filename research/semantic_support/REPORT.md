# Offline provisional semantic-support slice acceptance

Native implementation and separate native independent code/source reviewers, not Codex application sessions and not maritime experts.

Implemented a runnable research CLI and 11 public-report-derived cases. Exact quotation location is deterministic and separate from external unreviewed semantic proposals. Source page/column checks were performed against the pinned original PDF and independently repeated by an AI reviewer (SOURCE_REVIEW.md). Suggested semantic labels remain provisional; two cases have no suggested label. No human expert opinions have been supplied.

Final local combined test run: **44/44**, zero skips, 0.34s (16 primary + 28 independent). Independent rerun44/44,0.33s. Tests cover strict bounded JSON, duplicate keys/types/nonfinite numbers/depth, corpus binding, Unicode code-point coordinates and repeated quotes, reference mismatch, source hash failure, missing/duplicate predictions, fixture origin, malformed review data, distinct IDs without identity certification, scripted reviewers, preserved disagreements and no fact activation. Independent actual CLI test forbids Python socket creation; no network/model invocation.

Actual CLI on yangze22-provisional.json + fixture-predictions.json + empty-review-template.json:11 items,10 exact and1 deliberately altered quote not_exact,2 not_labeled,0 reviewer records,all prediction origins scripted_fixture,realModelCalled=false,factActivated=false. This exercises the program, NOT model quality. The fixed predictions largely follow the suggested labels and MUST NOT be reported as model accuracy or expert agreement.

No production service/Pi loop/UI connection, semantic fact engine, signed reviewer identity, validated expert gold standard or real-model acceptance. No broad production regression claimed because no production files changed. Selected GitHub Draft only; no merge/deployment.
