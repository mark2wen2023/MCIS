# Chapter 04 / 12 — Engineering without an authoritative reply

## Reproducible engineering evidence
- Research decision module: 20d5642; blob c61eb8649239c3fd62aa62a30f5f0b96b2a0a622.
- Synthetic regression tests: d7160d5; blob 20ef5758b514cb599dbaf52b0b0da5c4d5771d47.
- Local isolated Python execution of the matching source and tests: 15 passed in 0.05 s. Full service and independent QA not run in this execution.
- Skill policy: 9b6f8c9. No production authorization.

## Synthetic scene data
Original cell: null; candidate A: 0.25 m; candidate B: 0.35 m; no selected value => unresolved.
Separate fixture: original cell null; derived candidate 0 m selected with explicit synthetic rationale => research hypothesis, original remains null, design approval false.
These are distinct synthetic test cases, not real vessel measurements.

## Narration
当外部确认无法取得，我们不能让研究无限停滞，也不能把自己的判断冒充设计事实。于是，我们把原始证据、候选解释和研究采用值分开保存。一个空白可以产生多个有依据的候选解释，但它仍然是原图上的空白。我们允许假设存在，也要求假设能够被追溯、被检验、被替换。

## Remotion plan
Reveal an empty source cell; animate two conflicting candidates; leave selected value null. Transition to a separate fixture with an explicitly selected derived zero; show original null remaining unchanged. Display research-only and no design approval. Later visualize sensitivity across plausible candidate models, only once actually computed.

## Limitations
This module records decisions; it neither selects a document revision nor validates source authenticity, coordinate transformations, uncertainty intervals or the underlying geometric derivation. Real case material remains private without explicit publication clearance.
