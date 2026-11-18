# Programmatic task selection epoch
Base: 8cf97c30306c6f50d0402087897b83ace55ff1cc.
Two new statically reviewed ordinary synthetic nodes reproduce pending reread accepting a response after programmatic task selection to same run. Baseline 2 failed; after incrementing selection epoch at audio open-task and image showTask success, 2 passed.
`node --test tests_acceptance/media-programmatic-selection/audio.test.cjs tests_acceptance/media-programmatic-selection/image.test.cjs`
Adjacent `node --test tests_acceptance/image-task-query-context/page.test.cjs`: 8 passed. No real task, model, browser/backend, data, paused or write-refusal/security tests. Synthetic direct image showTask call represents task-response application, not real task completion. No claim of comprehensive task-start/list validation.
