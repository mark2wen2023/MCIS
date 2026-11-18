# Clear cached summaries on selection changes
Base: cf6ed532279e9f87cd12134523f67e1d7bf753fc.
Five individually reviewed synthetic input-event tests reproduced old list/task/source summaries remaining visible: 5 failed before, 5 passed after. Draft DOM and dirty state retained, zero requests. Applies to list panels/task output and audio source-context; does not clear loaded evidence editor or its historical metadata.
`node --test tests_acceptance/media-stale-summary/audio.test.cjs tests_acceptance/media-stale-summary/image.test.cjs`
Adjacent `node --test tests_acceptance/media-list-selection/audio.test.cjs tests_acceptance/media-list-selection/image.test.cjs tests_acceptance/image-list-context/page.test.cjs tests_acceptance/audio-task-cache/page.test.cjs`: 22 passed. Existing late-response assertions now compare post-selection-clearing state, preserving their stale-response check.
Developer DOM doubles only, no browser/backend/model, real data, paused/security/write-refusal tests. Clearing UI cache does not delete server records/cancel tasks. No claim of full async-path audit.
