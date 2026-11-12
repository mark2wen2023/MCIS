# W19.2 self-test (2026-11-12)
Base: f4ea8c4018548931e6d71df53e13e0a568f67052. Related source snapshot verified against GitHub blob SHA.
- W19.1 baseline: 37 passed.
- Final W19.1 + W19.2 API + schema/route contract (seed_demo=False): 67 passed.
- TypeScript build: passed. W19.1 UI:27 assertions passed. W19.2 response guards: passed.
- Changed-source oxlint: no warnings/errors.
- Real HTTP synthetic browser: preview double-click once, no database/audit writes before explicit save, exact source/body copy, Candidate-only save and hidden from Public, source/role invalidation, mobile public layout passed.
- Chromium wrapper failed in this runtime (socket restriction); existing Chrome headless shell via MCIS_BROWSER_BIN succeeded. No policy restriction was changed.
- Full seed-dependent contract run was not completed: reports/yangze22/case.json absent in intentionally source-only snapshot; reran OpenAPI route parity with seed_demo=False. No real report/production database was loaded.
- Full service/all-package regressions not claimed. No real model, vector retrieval or automatic knowledge interpretation. No deployment.
- Additional web regressions: npm test 18+58; test:w5 40; test:w16 148; W12 94 passed after materializing its existing synthetic W14.2 dump fixtures with baseline Git blob verification. Production web build passed (existing >1500kB bundle warning).
- W192-D01 preview-specific network retry wording fixed, re-frozen and independently closed. No open scoped defects.
- Rebased artifact contents onto main24db6d07d1d0bf36c84bc94467196a5d9886043c using GitHub blob verification; preserved all ARCHIVEA changes, appended shared notes only. Integrated W19+archive safety regression82 passed, web build+W19 UI rerun passed.
