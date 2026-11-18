# Media unknown-save guidance — development evidence

Base e935ba086b6411d91904d12e7455252d13736b3d. This is frontend guidance, not operation receipts or retry safety.

Reviewed new pure Node harness: actual inline callbacks, synthetic DOM, controlled in-memory json; fetch throws. No media, cases, Python/application, model, browser or HTTP. Before change both nodes failed because no persistent unknown reminder existed (missing element in synthetic DOM). After change:

```
node --test tests_acceptance/media-unknown-guidance/page.test.cjs
```

2 passed (one lifecycle each for audio/image): unknown, actual synthetic oninput, cancelled read (no request/draft retained), accepted read (draft replaced/dirty cleared), reminder retained. Confirmation explicitly warns rereading cannot prove original result. Zero fetch calls.

Separately reviewed/run existing memory-only tests:

```
node --test tests_acceptance/audio-save-feedback/page.test.cjs tests_acceptance/image-save-feedback/page.test.cjs
```

12 passed. Development results only; no independent acceptance claimed.

Unknown reminders retain case/run/segment-or-line labels in a page-local Set, separate from transient status and rendered rows. No payload text is retained there. Later reads/saves cannot automatically resolve the reminder. Repeated unknown submissions to the same label are coalesced: this is not an operation inventory or identity proof. No new retry lock, automatic retry, timeout, cancellation, permission or receipt behavior. Existing dirty confirmation condition and request/response validation preserved. Reminder explicitly says copy drafts and manually check; reads replace input and cannot prove original request result; resaving may append a revision. Refresh/navigation loses this memory; cross-page persistence is not implemented. Browser/HTTP/backend semantics untested here. Startup/archive pause remains.
