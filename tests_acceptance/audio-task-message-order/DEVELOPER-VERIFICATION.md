# Audio task message ordering
Base: 42a84ab4aa1ed294c55998370d3b315533a37c71.
Nine new statically reviewed ordinary synthetic nodes: status selection away/back; four start/status/list overlap orders; normal status; late transport error. After correcting list fixture to array, exact parent HTML replay in a temporary directory still 8 assertion failures, 1 pass.
`node --test tests_acceptance/audio-task-message-order/page.test.cjs`: final 9 passed.
`node --test tests_acceptance/media-task-start-context/audio.test.cjs tests_acceptance/media-list-selection/audio.test.cjs`: 17 passed.
Status/list now share task message guard with start, clear prior taskResult while querying and accept only current context/order. Current failures retain task ID and no-retry warning, stale failures do not overwrite current status. Does not cancel a request or prove task execution. Developer DOM/HTTP doubles only; no browser/backend/model/real data, paused/security/write-refusal probes. No permission or archive changes.
