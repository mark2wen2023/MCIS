# Independent W10.2 acceptance

Run from repository root: `python tests_acceptance/W102/run.py`.
Global Python needs existing Playwright; service uses service/.venv. Does not install software. Ports 18822/18823/15822, all 127.0.0.1. Synthetic fixtures live under a fresh /tmp/w102-independent-* directory. Servers and browser are children of the runner; it terminates services/Vite in finally. Logs/screenshots/results go only to logs/w102-independent-*.

server.py creates isolated synthetic cases directly and adds test-only request-scoped file-2 / final DB commit / cleanup fault injection. It does not change implementation source or reuse implementation tests. Actual tests call real HTTP, not TestClient. Browser tests use actual Chromium and Vite proxy.

KnownDefect D01 is retained as a strict failing assertion; a failing scene yields exit 1. Result counts are independent scenes, not individual assertions. See DEFECTS/W10.2.md for current disposition and coverage limits.

Set `MCIS_BROWSER_BIN` to the executable of an already-installed compatible Chromium browser. If unset, Playwright uses its configured browser installation. Required existing dependencies: global Python with Playwright, service/.venv with project service dependencies, Node and web/node_modules. No browser or dependency download occurs in the runner. Set the environment variable before invoking the command above; runtime absolute paths are not embedded in the test source.

Run the independent W8.4 shared-wiring preservation check from the repository root:

```bash
PYTHONPATH=service service/.venv/bin/python tests_acceptance/W102/check_w84_preservation.py
```

The service import path and service virtual environment are required for this check.
