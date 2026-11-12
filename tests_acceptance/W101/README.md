# W10.1 independent acceptance

The tests do not modify production implementation or invoke any model.

## Run in normal checkout

```sh
web/node_modules/.bin/esbuild tests_acceptance/W101/model.test.ts --bundle --platform=node --format=cjs --outfile=tests_acceptance/W101/.tmp-model.cjs
node tests_acceptance/W101/.tmp-model.cjs
web/node_modules/.bin/esbuild tests_acceptance/W101/navigation.test.ts --bundle --platform=node --format=cjs --outfile=tests_acceptance/W101/.tmp-navigation.cjs
node tests_acceptance/W101/.tmp-navigation.cjs
MCIS_BROWSER_BIN=/absolute/path/to/installed/chromium python tests_acceptance/W101/browser_test.py
```

Python running browser_test.py needs the already installed Playwright package. The runner uses service/.venv/bin/python for the real service, starts service/Vite/browser in the same process tree, and kills only its own server groups afterward. Ports are **127.0.0.1:18810** and **127.0.0.1:15810**. No public bind, deployment, browser install or dependency install. Set MCIS_W101_PYTHON, MCIS_W101_SERVICE_ROOT and MCIS_W101_ARTIFACT_DIR to override interpreter, source and output directory (default outputs/data are fresh temporary directories). MCIS_BROWSER_BIN is mandatory. Agent base URL and model are explicitly blanked in the runner.

qa_app.py uses actual create_app with standard seeding disabled, then fictional Lily/Mary plus explicitly synthetic QA cases/points. QA-EMPTY has a non-fictional boolean only to test the honest label, not to claim a real report; all names/source strings identify fixtures. Fixture rows are created solely in the new temporary database. No track-write API exists or is invented. HTTP tests compare actual returned points to persisted fixture JSON, verify time windows, empty cases/vessels, all six default role policies, and no mutation/audit change.

Real Chromium tests use real HTTP for stored data, filtering, pagination, selection and empty/role behavior. Explicit route doubles cover malformed/error payloads, upper budgets and delayed/race responses. These doubles are not counted as server functionality. Model/navigation unit tests directly exercise production pure functions and deterministic event listeners, independently of implementation self-tests.

CUA browser previously could not reach exec-local loopback servers (ERR_CONNECTION_REFUSED). Under the continuing engineering-test authorization, reuse the installed Playwright/browser in one local process tree. This test harness does not evade website restrictions.

Only source tests, text/JSON results, freeze check and review/defect documents belong in commits. Do not commit the temporary runtime source copy, generated CJS, SQLite, screenshots, fixture blobs or installed browser. The service runtime used for acceptance is compared to the specified main commit, with exact Python source results in service-baseline.json.
