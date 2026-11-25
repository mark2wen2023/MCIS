# W17 archive export diagnostic (synthetic only)

Product baseline: MCIS `871db66badc6566d82239ee701958c0ef8feb558`. This directory adds diagnostic and regression code only, not archive support.

The built-in fictional case `CASE-2026-DEMO-LILY-MARY` returns HTTP 409 `ARCHIVE_RESTORE_UNSUPPORTED` via the working-archive preflight. The synthetic diagnostic seeded only this fictional case and confirmed that the inner refusal is `WORKING_ARCHIVE_INVALID` for business state outside the supported restoration set. In this fixture, the unsupported nonempty sets are agent drafts (2), COLREG analyses (1), consultation rounds (2), recommendations (7), timeline conflicts (4), and timeline events (12). Export is correctly refused; database rows and source bytes stay unchanged. Do not remove records or bypass the guard to produce a partial package.

The positive control uses one synthetic registered original: API export creates a v1.2.0 package, a clean SQLite instance imports it, and the archive-history read returns the exact original bytes and SHA-256. The old active receipt is not replayable after restore. The negative control adds an untracked synthetic file and requires the exact 409 with no attachment or data changes; denied users receive the usual access refusal. This does not imply full fictional-demo restore, Unity integration, production identity, or complete work package acceptance.

In an isolated checkout of this diagnostic candidate, using the existing service dependencies:

```sh
cd service
PYTHONPATH=. .venv/bin/python -B -m pytest -q -p no:cacheprovider \
  tests/test_working_record_archive.py \
  ../tests_acceptance/w17-archive-export-diagnostic/test_synthetic_archive_gate.py
PYTHONPATH=. .venv/bin/python -B \
  ../tests_acceptance/w17-archive-export-diagnostic/diagnose_lily.py
```

Runs use FastAPI TestClient and temporary SQLite, blob and restore directories. No listener, deployment, real data or external service. Grokbot's earlier loopback 409 is a separate receipt; the diagnostic does not run Grokbot's bundled code.
