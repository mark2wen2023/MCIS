# Bow-tie path navigation (synthetic browser acceptance)
Base: MCIS `99b3b4bb8e88cbd390ac0c3e7a519ed533a890f3`. Apply only the listed source changes to the matching base. No model, service, archive, production permissions, fixture data file or CI required.

From the repository root, with existing esbuild, Playwright and sandboxed Chromium:
```sh
out=$(mktemp -d)
NODE_PATH="$PWD/web/node_modules" web/node_modules/.bin/esbuild web/tests/bowtie-path-browser/fixture.tsx --bundle --platform=browser --jsx=automatic --outfile="$out/fixture.js"
NODE_PATH="$PWD/web/node_modules" node web/tests/bowtie-path-browser/check.cjs "$out/fixture.js" /absolute/path/to/chromium
```
If Playwright lives elsewhere append its installed `node_modules` path to NODE_PATH; do not install or disable the sandbox to make this gate pass. Delete the temporary bundle afterward; do not commit or publish it. Runner mounts the real form using one in-browser synthetic preview response; the intercepted assets do not require a network, server or proxy. No core computation is accepted. Both viewport records and process exit 0 are required for browser success; SSR/callback, bundle and syntax checks are not browser success. Keep the earlier UI/path regression separate. This does not change Diagram or the W15.4/other workflows.
