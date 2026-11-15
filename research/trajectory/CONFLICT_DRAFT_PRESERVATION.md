# Conflict draft preservation

Parent:6e493f1a1699a6f6abe33cc0f526a4df5c9a4728. Branch fix/conflict-draft-preservation. Local only; no push/merge/deploy.

## Confirmed scope
Exact parent callbacks executed with synthetic setters demonstrate row reselect replaces unsaved note and original version, while any patch success closes editor. This is ordinary callback reproduction, not DOM/browser reproduction.

Drafts now live per conflict in mounted page memory. Row reselect/refresh preserves draft and captured token. Status success does not clear or close edits. Note success removes only the identical submitted draft object, so later typing or explicit comparison survives an earlier response. Other drafts remain. Failed requests leave drafts intact.
Current saved resolution remains visible for comparison. An explicit button adopts displayed version while retaining draft, without saving or retrying. Server CAS still rejects subsequent races. Row choice never implies comparison. No browser storage; navigating away, changing case/identity or reloading page can discard memory drafts, as visible notice explains. This is not a durable draft feature.

## Developer verification
Run from web:
```sh
node tests/conflict-drafts-parent-probe.cjs
./node_modules/.bin/esbuild tests/conflict-drafts.test.ts --bundle --platform=node --format=cjs --outfile=/tmp/mcis-conflict-drafts.cjs --log-level=warning
node /tmp/mcis-conflict-drafts.cjs
./node_modules/.bin/esbuild tests/conflict-version.test.ts --bundle --platform=node --format=cjs --outfile=/tmp/mcis-conflict-version.cjs --log-level=warning
node /tmp/mcis-conflict-version.cjs
npm run build
```
Parent3 assertions, candidate15 state/wiring assertions, previous8 version assertions passed. TypeScript/Vite build passed; existing >1500kB warning. Two initial command attempts used root-relative paths from web and failed file lookup; corrected working-directory-relative paths before successful tests.

No backend or permission code changes, backend tests not rerun. Previous backend125+1 belong to parent only. No actual browser, DOM event simulation, independent acceptance, SSO or production verification. No restricted security/ECFC operations. Versionless existing writes still428 and stale412; source registry checks remain bytesVerified=false.
