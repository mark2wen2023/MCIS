# W4.2 preview digest wrap at 390 px and 1440 px

The source baseline is MCIS `3ae5166b7522f63bf39827a02341c856e394a0c9`.
The only product change is the scoped CSS rule
`.image-pane #preview-status{overflow-wrap:anywhere}` in the image-review
host. The DOM and JavaScript stay byte-for-byte unchanged, so this does not
change digest values, preview selection, canvas pixels, read authorization
or auditing. The entire 64-character digests remain in the status text.

Use two exact files, the original from the fixed commit and the candidate
after this rule. Example for the static gate from the candidate checkout:

```sh
node tests_acceptance/w42-preview-digest-layout/check.cjs \
  --baseline /path/to/3ae5166/service/mcis_service/image_review/review.html \
  --candidate service/mcis_service/image_review/review.html
```

For browser-layout validation, add all of the following flags to that command:

```sh
--playwright /path/to/existing/node_modules/playwright \
--chromium /path/to/working/sandboxed/chromium \
--out /path/to/new-screenshot-directory
```

Use a currently working Chromium with its normal sandbox. The test does not
install anything, start a listener, access a service, or allow browser
network activity. It loads the actual full template markup and CSS without
its scripts and substitutes the exact status format with two distinct
synthetic digests. It checks that the narrow original still reproduces the
overflow, the candidate keeps digest fragments within the status box,
the 64-character PNG digest wraps only at the narrow width, the desktop
does not gain overflow, and both canvases and the status role remain.
It can save four PNGs to the optional new directory. It does not invoke
the file decoder, compare canvas pixels, assert API policy behavior or
supersede the actual W4 browser entry.

A static-only pass asserts the exact baseline Git blob and rejects any
candidate difference other than this one CSS insertion. An unavailable
Chromium binary, sandbox startup error, or failed browser assertion is not
a browser pass.
