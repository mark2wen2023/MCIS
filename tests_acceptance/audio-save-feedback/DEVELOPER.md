# Audio save feedback — development evidence

Base: e835a9936a040f82294dfff54d3e15d53852872d.

Actual inline audio page callbacks, synthetic DOM and controlled in-memory `json()` Promises. New harness throws on fetch and checks zero fetch calls. No audio bytes, Python application, cases, models or browser. Test source reviewed before running.

Before fix: all seven new nodes failed expected feedback assertions, including stale success after oninput and ambiguous communication failure. After fix:

```
node --test tests_acceptance/audio-save-feedback/page.test.cjs
```

7 passed: success/edit/second waiting (duplicate click not queued); ordinary communication unknown followed by editing; submitted snapshot accepted while later draft remains; late success/failure after case/run changes. Current DOM inputs, dirty, revisions and request counts checked.

Separately reviewed neighboring synthetic tests (their fetch functions are memory doubles, no network):

```
node --test tests_acceptance/audio-saved-draft-state/page.test.cjs tests_acceptance/audio-save-context/page.test.cjs
```

7 passed. These are development results, not independent acceptance.

Per-segment feedback identifies loaded case/run/segment and distinguishes last confirmation, current draft, current waiting and unknown. Matching response still compares captured submitted content; later edits stay dirty. Existing selection and response checks unchanged. Pre-dispatch validation remains outside unknown catch. Communication/response failures after dispatch conservatively say possibly submitted. No automatic retry, cancellation claim, timeout unlock, or new server receipt. Existing busy gate remains; unknown does not add a manual retry lock. Drafts remain memory-only.

No real browser, playback, HTTP, backend, model or production acceptance. App startup/archive tests remain paused. No paused/refusal/write-probe tests run.
