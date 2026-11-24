# W7: same-root round selection and slow consultation refresh

This new standalone check uses fixed source blobs from
`7dfb3261522ff6241b9f5b44f809dd405b28ffde`. It mounts the actual consultation
panel, lifecycle form, and round editor in one ReactDOM root using Happy DOM.
Only CSS is omitted. The production API client is bundled unchanged, with
a strict test fetch: only 8 expected GETs on 2 synthetic case IDs; no
fallback, mutations, or external network requests. The policy reply is
a synthetic form-visibility fixture, not an authorization result.

Use an existing web dependency directory (tested with React/ReactDOM 19.3.1
and esbuild 0.28.2) and the absolute path to an existing Happy DOM entry
(tested with 21.0.4). Supplying these paths does not install dependencies.
Use Node 24 and an isolated snapshot made only from the manifest:

```sh
set -eu
base=7dfb3261522ff6241b9f5b44f809dd405b28ffde
testdir="$PWD/tests_acceptance/W7"
src=$(mktemp -d)
trap 'rm -rf -- "$src"' EXIT
awk '{print $2}' "$testdir/consultation_dom_sources.sha1" |
  xargs git -C "$PWD" --literal-pathspecs archive --output="$src/closure.tar" "$base" --
mkdir "$src/source"
tar -xf "$src/closure.tar" -C "$src/source"
node "$testdir/check_consultation_dom.cjs" "$src/source" "$WEB_NODE_MODULES" "$HAPPY_DOM_INDEX"
```

The test holds A's first consultation-round response and B's first
consultation-round response while rendering A again on the same root. It
changes actual form controls, selects an older round, refreshes, verifies
that removed rounds and old drafts are not retained, then lets the old A
success and old B failure settle after the newest round and draft are on
screen. A second click on refresh is unavailable while a same-session read
is pending. It does not simulate two overlapping refresh-button GETs in one
session. No user-action mutation is invoked; reading does not cause a write
callback and no unlisted request is allowed.

This is ReactDOM and a **DOM simulation**, not Chromium/real-browser UX,
real HTTP, policy/security, actual dispatch, or persistence verification.
Existing browser tests and product source files are unchanged.
