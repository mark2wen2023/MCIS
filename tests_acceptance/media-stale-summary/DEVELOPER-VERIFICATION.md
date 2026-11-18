# Clear cached summaries on selection changes
Base: cf6ed532279e9f87cd12134523f67e1d7bf753fc.
Five individually reviewed synthetic input-event tests reproduced old list/task/source summaries remaining visible: 5 failed before, 5 passed after. Draft DOM and dirty state retained, zero requests. Applies to list panels/task output and audio source-context; does not clear loaded evidence editor or its historical metadata.
`node --test tests_acceptance/media-stale-summary/audio.test.cjs tests_acceptance/media-stale-summary/image.test.cjs`
Adjacent `node --test tests_acceptance/media-list-selection/audio.test.cjs tests_acceptance/media-list-selection/image.test.cjs tests_acceptance/image-list-context/page.test.cjs tests_acceptance/audio-task-cache/page.test.cjs`: 22 passed. Existing late-response assertions now compare post-selection-clearing state, preserving their stale-response check.
Developer DOM doubles only, no browser/backend/model, real data, paused/security/write-refusal tests. Clearing UI cache does not delete server records/cancel tasks. No claim of full async-path audit.

## Assertion correction after independent review
On runtime df36348e316b1f35fb1635e94469a8cd5cde30cd, replaced cached `s.boxes` comparison with fresh current container lookup, current child count, exact textarea text and reason values, plus existing dirty/zero-request assertions. The old cached-array assertion alone could not establish current editor preservation. Same exact two-file command above: **5 passed**, developer synthetic DOM only. This change is tests/documentation only, no runtime modification or browser claim.
