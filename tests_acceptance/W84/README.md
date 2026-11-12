# W8.4 independent acceptance

All fixtures are synthetic, loopback-only, with fresh temporary databases. No deployment, real incident edits, or publishing occurs. Implementation files are not edited by this suite.

## Commands

From repository root:

```sh
sha256sum -c logs/w84-backend-hashes-frozen-v2.txt
sha256sum -c logs/w84-ui-hashes-frozen-v2.txt
service/.venv/bin/python -m pytest -q tests_acceptance/W84/test_metadata_independent.py service/tests/test_contracts.py
MCIS_PLAYWRIGHT_MODULE=playwright MCIS_BROWSER_BIN=/path/to/chromium bash tests_acceptance/W84/run-browser.sh
MCIS_PLAYWRIGHT_MODULE=playwright MCIS_BROWSER_BIN=/path/to/chromium MCIS_W84_BROWSER_SCRIPT=legacy_blank_browser.cjs bash tests_acceptance/W84/run-browser.sh
```

Use installed trusted Python, Playwright, and Chromium equivalents via the environment overrides when reproducing elsewhere. Screenshots and server logs stay in a temporary directory, not published acceptance artifacts.

## Results and boundaries

- Backend first run: 39 pass / 1 fail. D01 retained: established package serialization normalizes missing optional strings; exact cross-package snapshot equality was an incorrect compatibility expectation. Contract v2 now explicitly covers normalization and rejects old revision tokens after changed snapshots.
- Backend v2: 43 independent tests + 4 contract tests passed. Full original text and audit reason preservation, explicit clear semantics, roles/policy, immutable fields, concurrent writers, ABA, operation uniqueness, rollback, restart and package reconstruction covered.
- Browser first completed run: 36 assertions passed, actual service and browser. Only loss/tampering scenarios intercept responses; ordinary save/reopen/conflict operations use the real service. 1440, 768 and 390 pixel screenshots manually reviewed. Knowledge is intentionally global; returning restores case context.
- UI v2 rerun: 39 real-backend assertions passed, including delayed PATCH response after case navigation, shell isolation, and confirmation that leaving does not undo a dispatched mutation.
- D02 corrected and independently closed: existing whitespace/empty titles remain readable, show 未填写, preserve editable originals; new whitespace writes rejected, legal UI repair survives reload. Original red reproduction retained.
- Backend v2 and UI v2 freezes checked before and after acceptance, all hashes match.
- Test-harness corrections: exact textarea label included its value (changed to prefix matching); knowledge navigation awaited URL before React committed (now waits actual heading); testing unchanged empty title triggers no-op rather than blank-write validation (now changes empty to whitespace). These are not product defects.

This acceptance is not production authentication, certification of source truth, complete report regeneration, or comprehensive W19/W10/W9 reacceptance. Navigation smoke checks do not imply downstream simulation integration.
