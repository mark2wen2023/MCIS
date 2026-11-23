# Isolated React single-seat readonly card

Parent 3d2424abc49175e80aceeb51e98467614ebe0a24. Only this new research directory is added. No web route, transcript-review integration, W9 changes, endpoint, authentication, persistence, model or business data. The existing web React/ReactDOM/esbuild SSR approach is reused without installation or configuration edits.

## Run
With existing web dependencies available, from candidate checkout:

    node research/single_seat_card/run.cjs

Or pass an explicit existing web directory as the sole argument. The actual run used that explicit dependency-root mode, exited 0, and produced result.json plus the SSR body in sample.html. No browser, screenshot or interactive accessibility test was run. esbuild transpilation/bundling is not a full TypeScript type-check. The runner writes its bundle only to an automatically removed temporary directory; it does not modify web files.

The parent research/single_seat_preview/result.json is reused directly, not duplicated in this commit. Before bundling, run.cjs requires its exact SHA-256 ab3543be14e7e2271790a1a0cb03d61a3a779adb0f3682ef56f32050317f3dc9. That artifact originated from the earlier actual fixed Python handoff/preview boundary. This SSR stage does not rerun registered reads or authenticate the source.

## Component contract and scope
SingleSeatCard accepts a prop preview: unknown, a plausible untrusted incoming UI value. Existing transcript parseDraft does not support this distinct preview type and is intentionally not reused or widened. Rather than duplicate the seat's semantic parser, this deliberately fixed-fixture card admits only structural equality with the entire pinned preview value. Unsupported, missing, changed or additional fields fail closed with a generic alert; no input content is echoed. After admission, rendering uses the frozen fixture, avoiding a second read of arbitrary supplied fields. This is a narrow developer demonstration, not a generic parser or security boundary for hostile in-process JavaScript objects.

The card uses separate Chinese headings for human pending/not confirmed/not saved and evidence gap/no exact observation/insufficient. Original English statements remain intact in details elements. A's gap pointer is plain code text marked synthetic, non-clickable, not an observation and not verified by actual authorized access; B retains no exact observation reference. No anchors, buttons, forms, inputs, callbacks, local storage, effects, mutation, fetch or source hashes are included. No action can confirm or save. The output stays T124.250 only, not T100 or general conflict review.

## Actual SSR acceptance
Positive assertions cover Chinese operator labels, A/B distinction, gap pointer, stable cloned-input rendering, no interactive authority link or form, and unchanged rerender after rejection. Twelve negative cases cover wrong case/time, confirmed/saved/wrong review status, conflicted label, borrowed B reference, missing A reference, extra private field, changed HTML-like statement, unsupported type and null. All reject without exposing source or injected/private-control text. No semantic truth, real human review, authorization, PDF/OCR or model performance is claimed. sample.html is static SSR evidence, not a deployed app or browser acceptance.
