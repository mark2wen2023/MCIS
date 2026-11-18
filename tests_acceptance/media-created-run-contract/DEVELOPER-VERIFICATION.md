# New image/audio run response validation
Base: 2b77eb4831dce02a6c20c31509a7335e71a3a234.
Server evidence: image_review/app.py creates OCR- + uuid4().hex, revision 0 at lines 79–86; audio_review/app.py creates AR- + uuid4().hex, revision 0 at lines 118–123. Creation appends no human revisions. No server changes.
New 12 ordinary synthetic malformed-success/valid-success nodes individually reviewed. Final fixtures use canonical previous UUID IDs. Replayed against exact parent HTML via git show in a temporary directory: 10 assertion failures, 2 passed. Final implementation: 12 passed.
Commands:
- `node --test tests_acceptance/media-created-run-contract/image.test.cjs tests_acceptance/media-created-run-contract/audio.test.cjs`
- `node --test tests_acceptance/image-create-race/page.test.cjs tests_acceptance/audio-attach-race/page.test.cjs tests_acceptance/audio-attach-form/page.test.cjs` — 17 passed. Existing synthetic success fixtures corrected to return new canonical run IDs; assertions retained and expected created ID updated.
Checks reject same current/displayed ID, malformed ID, nonzero revision or pre-existing human history. They cannot prove global uniqueness or authenticity; malformed HTTP-success response is synthetic, not evidence of actual backend failure. Unknown result retains input, requests manual checking, no retry. This does not validate all source binding fields. Developer only; no browser/backend/model/real data, paused/security/write-refusal probes. Permissions/archive unchanged.
