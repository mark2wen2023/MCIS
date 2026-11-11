# W8.1 independent contract/SSR acceptance

Run from repository root:

```sh
NODE_PATH=$PWD/web/node_modules web/node_modules/.bin/esbuild tests_acceptance/W8/contracts.test.tsx --bundle --platform=node --format=cjs --outfile=tests_acceptance/W8/.tmp.cjs --jsx=automatic --loader:.css=empty
node tests_acceptance/W8/.tmp.cjs
sha256sum -c logs/w8.1-impl-hashes-frozen.txt
```

Result: 16 independent assertions passed. Four frozen implementation files match both before and after the run. Covers escaped case text, encoded case identifiers, fiction labels, five supported navigation routes preserving case, malformed/duplicate summaries, empty list, error rendering, and keyed case/role boundary inspection.

Not covered by these SSR assertions: effect timing, real browser history, transport, actual backend permissions or production authentication. The separate browser.py harness was prepared but Chromium launch failed in this environment (`socket() Operation not permitted`) both in regular and approved escalated execution. No browser checks in that harness reached execution. Separate browser review is in progress. No implementation files were changed by acceptance.
