# List/source late transport errors
Base: a0a5cec418f904ed69cc7d7c1500b83d5f5c5973.
Eight new individually reviewed ordinary synthetic transport tests: audio list/source and image run/task lists, late vs current errors. Baseline 4 failed / 4 passed; after success/error use identical context predicates, 8 passed.
`node --test tests_acceptance/media-list-errors/audio.test.cjs tests_acceptance/media-list-errors/image.test.cjs`
Adjacent `node --test tests_acceptance/media-list-selection/audio.test.cjs tests_acceptance/media-list-selection/image.test.cjs tests_acceptance/image-list-context/page.test.cjs`: 15 passed. Current errors still explicit/no retry; stale errors no longer overwrite new public status. Not all async errors audited. Developer DOM/HTTP doubles only, no browser/backend/model/data, paused/security/write-refusal tests, permission changes or archive opening.
