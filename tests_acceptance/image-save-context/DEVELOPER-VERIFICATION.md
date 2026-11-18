# Image save selection guard

Base: 67e323ddef686a586ea77dcb1f5dcdd92eb55816.
Synthetic delayed successful response reproduced a stale revision update after case selection changed (1 failure before fix).

Developer commands: `node --test tests_acceptance/image-save-context/page.test.cjs` (4 passed); targeted image-saved-draft-state (3 passed) and image-read-race (5 passed), as recorded in their verification files. New nodes cover changed case, changed run, away/back, unchanged selection. Each node statically reviewed: DOM/HTTP doubles only, no security or write-refusal probes.

Selection changes preserve drafts and do not apply late responses. The request may have saved on the server; message requires manual result checking, no automatic retry. No real browser/backend, image bytes, model, or independent acceptance. Existing pending-edit unknown-result behavior retained.
