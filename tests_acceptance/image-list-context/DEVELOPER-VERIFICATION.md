# Image list selection guard
Base: b866eff80034ec8b6136cab26f42874862768f1a.
New ordinary synthetic nodes statically reviewed: delayed successful GET doubles only. Initial harness missed initialization of runs element; corrected before reproduction. Corrected baseline: 2 assertion failures (late list replaced previous content after case switch/away-back), 1 normal pass.
After fix: `node --test tests_acceptance/image-list-context/page.test.cjs` 3 passed. Developer synthetic only, no real browser/backend, permission or security tests, data, models or write-refusal probes. Existing displayed list is not cleared by this change; late response cannot replace it after selection changes. Not a complete async-path audit.
