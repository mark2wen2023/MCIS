# Archive export safety A: independent acceptance

**18 synthetic API/DB tests passed**, actual-service browser passed, and **12 frozen hashes matched**. No acceptance implementation changes. This is a refusal safeguard, not a new archive format or restoration implementation.

## Original failure confirmed

Before the patch, a real synthetic report was generated through its API (201), exported (200), and imported through the old endpoint into a second empty database (201). The target contained neither a report document nor its operation snapshots. Thus nominal success did not mean a recoverable report backup. The private reproduction and original log are retained locally and not published.

## Independent API/DB coverage

- Actual report generation and actual legacy transcript creation cause whole-package `409 ARCHIVE_RESTORE_UNSUPPORTED`.
- Standalone orphan report snapshots and GISIS snapshots also block export.
- Residual report/interview audit actions, a report snapshot reference with otherwise generic audit fields, and an unclassifiable raw audit line block export.
- Default unauthorized identity receives 403 without the archive-state error. Explicit source-category revocation precedes the new 409. Transcript source disappearance and changed SHA retain the existing 403 / source-conflict 409 instead of masking them as archive limitations.
- Manual-entry receipts retain their dedicated 409, even after their original record is removed.
- Every denial/refusal compared all database tables and non-database files before and afterward. No mutations were observed. Additional traps prove report refusal occurs before file assembly or export-audit append.
- Plain synthetic basic-case export still returns a ZIP successfully.

HFACS format support is not independently revalidated by these 18 tests. Code comparison shows the HFACS assembly/restore path and old import function were not modified; this report does not substitute that observation for a full HFACS round-trip regression.

## Real browser, not API doubles

Using an empty temporary database and actual FastAPI server, the browser created a synthetic report through its API, opened its report page and verified the backup warning, then requested export from the lobby. The actual response was 409, explanatory text appeared, and no download event occurred. Switching to Investigator produced actual 403 and removed the prior archive-state response detail. The transcript page displayed its warning. No browser page errors occurred.

## Scope and unchanged components

Compared with the preceding W5.2b snapshot, the package-module diff consists only of the new post-authorization refusal block. The old import code was unchanged. Shared `reports/access.py` and `audit/service.py` were byte-identical to the previously accepted version, preserving the scoped lock-order fix.

Only synthetic data with `seed_demo=False` was used. No external model, W11, real reports, deployment or publication was exercised. No full-repository acceptance, complete restoration, universal archive coverage, authentication, redaction or legal-signature claim is made. Known unsupported records are now explicitly refused; other modules require their own recovery specification and tests. Database files are excluded from byte-level file comparison because read/transaction metadata may change; all logical table contents are compared.

## Reproduce

```sh
PYTHONPATH=service service/.venv/bin/pytest -q tests_acceptance/ARCHIVEA/test_boundary.py
MCIS_BROWSER_BIN=/path/to/existing/chromium python tests_acceptance/ARCHIVEA/browser_real.py
sha256sum -c tests_acceptance/ARCHIVEA/verified-impl-sha256.txt
```

Browser requires installed service/web dependencies, system Python Playwright and an existing Chromium. It performs no installation; temporary servers bind only to loopback. `server.py` uses the synthetic fixture helper in `test_boundary.py`.
