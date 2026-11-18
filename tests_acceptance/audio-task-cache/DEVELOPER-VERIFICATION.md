# Cached task selection invalidation
Base: 9e1b06bf6c5e122c373ec40c475d7fa74f34f724.
Seven individually reviewed ordinary synthetic nodes change and restore receipt/form/task/case/run values, then attempt open-task with stale cached result. Exact parent HTML replay: 7 failed. Final `node --test tests_acceptance/audio-task-cache/page.test.cjs`: 7 passed; no requests issued after invalidation.
Adjacent `node --test tests_acceptance/audio-task-message-order/page.test.cjs tests_acceptance/media-programmatic-selection/audio.test.cjs`: 10 passed. Cache cleared only, draft fields preserved; requires requery, not task cancellation. Developer DOM/HTTP doubles, no browser/backend/model, real data, paused/security/write-refusal tests. Actual API normal-flow evidence on parent remains separate.
