# Task start response context
Base: 0ecf86165512a74ee47efd80750617cb598c6629.
16 new individually reviewed ordinary synthetic nodes, fake fetch only: changes away/back to case/run/task/source receipt/confirmation, new draft while waiting, late transport failure, unchanged success on both pages. No actual task/model/process launched. Baseline 13 assertion failures, 3 passed; final 16 passed.
`node --test tests_acceptance/media-task-start-context/image.test.cjs tests_acceptance/media-task-start-context/audio.test.cjs`
Adjacent `node --test tests_acceptance/image-task-query-context/page.test.cjs tests_acceptance/media-programmatic-selection/audio.test.cjs tests_acceptance/media-programmatic-selection/image.test.cjs`: 10 passed.
Developer synthetic only; no browser/backend/independent acceptance, real data, paused/security/write-refusal probes. Start result is ignored when editing/context changed, not canceled. Task may have run; preserve its ID and query manually, never infer non-submission. Image stale-error test asserts task-status only, not global status; current code handles start errors locally. Audio status/list ordering is separate follow-up, not proved here.
