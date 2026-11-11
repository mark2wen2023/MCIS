# MCIS local browser acceptance, 2026-11-12 (UTC+8)

## Environment and provenance
Cloud Linux local headless browser, not the user's computer or mobile Safari. Backend, Vite preview and browser ran in one subprocess tree, bound exclusively to 127.0.0.1, with a fresh temporary data directory. No production services or deployment touched.

CUA cloud Chrome could not reach the exec-host localhost (`ERR_CONNECTION_REFUSED`). System full Chromium failed process singleton socket creation (`Operation not permitted`). With explicitly authorized project-E2E fallback, official Chrome for Testing headless shell worked without changing system security settings. Existing test browser flags were retained.

- Browser: **Chrome Headless Shell 157.0.8103.50**
- Official metadata: https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json
- Download: https://storage.googleapis.com/chrome-for-testing-public/157.0.8103.50/linux64/chrome-headless-shell-linux64.zip
- ZIP size: 128166087 bytes
- SHA256: `7bf0d41e424efd1d6281c4162993ab9dc5de92fac213c211614905a71c057d0f`
- Earlier Playwright-requested 151.0.7922.34 CDN URL returned a 195-byte HTML `Site Unavailable` response, not a ZIP. This does not establish whether the version exists upstream.

## Final results (2026-11-12, UTC+8)
1. Unmodified repository `tests_acceptance/W6/test_w6_e2e_browser.py`: **19 passed in 11.12s**, including 4 networking and 15 browser tests. A PATH wrapper selected official headless shell; test assertions unchanged. Final log: `logs/continued-w6-browser.txt`.
2. Cross-page final smoke: **35/35 checks passed**. YANGZE Chinese template generates 17 chapters; liability chapter has bounded public excerpt, no-new-liability disclaimer and exact locator `report.txt#L1026-L1033`. Haili generates 12 chapters. W12 scenario switching, derived-data label and Y1 critical result render. W5 interview person switching and transcript render. W6 Haili data/disclaimer render.
3. Actual case-linked UI interactions: report EV-201 link opens YANGZE evidence; hash verification POST targets YANGZE EV-201; switching to Haili selects EV-101 and verification POST targets Haili. New recommendation draft POST targets YANGZE; clicking report entry preserves YANGZE. All writes used disposable local data. Captured mutation URLs are in `logs/continued-browser-result.json`; none target the demo case.
4. Final capture: no JavaScript/console errors, warnings or HTTP >=400; no framework overlay. All 14 page/viewport pairs had document scrollWidth equal to viewport width (1440 or 1920). This is not comprehensive responsive/mobile/accessibility certification.

## Findings fixed and verified
- Report global Layout formerly showed fictional Lily/Mary while report was YANGZE. Fixed: header/sidebar and report now agree on real public case.
- Evidence and recommendation case-linked navigation/mutations were corrected by implementation owner; browser interactions verified above.
- Evidence page requested CPA without YANGZE tracks, yielding HTTP422. Fixed: checks current-case tracks first, avoids unsupported calculation, visibly states insufficient tracks / CPA not run and no timeline data. Final network and console clean.
- Initial smoke had a test readiness race after report generation; waits now use generated URL and enabled action before chapter selection. Intermediate failure artifacts are retained separately for audit, not final evidence.

## Repository artifacts
Paths below are relative to the repository root.
- `logs/continued-browser-result.json`: all 35 checks and five temporary local mutation URLs from the final run (ephemeral localhost ports are recorded evidence, not reusable endpoints).
- `logs/continued-w6-browser.txt`: original W6 suite, 19 passed.
- `tools/provenance/browser_smoke.py`: archived local Linux smoke harness. Requires installed Playwright, service Python environment, Node/web dependencies, .NET runtime and prebuilt real core DLL, plus an official headless-shell executable. Installation paths are supplied through environment variables; no machine paths are embedded. This is not a turnkey portable installer. See its module docstring for invocation and prerequisites. After replacing installation paths with environment configuration, the archived harness was actually rerun: 35/35 checks, no captured JS/console/HTTP errors (not merely syntax-checked).
- Local-only screenshot archive (not uploaded to this PR): 19 final JPEGs, quality80, original dimensions without scaling: report (YANGZE/Haili), evidence, recommendations, analysis, interview, COLREG at 1440/1920, one full-page report, and four original W6 screenshots. Source PNGs retained in the working test archive, not included in this repository subset.
- Official browser download URL, version, ZIP size and SHA256 are recorded above. Browser binaries are not included.

Visual inspection included final YANGZE evidence screenshot (correct case, public-source rows, hash verified, explicit missing-track/timeline notices), corrected report liability/source locator, and earlier same-layout analysis/interview/COLREG captures. Dense metadata sometimes wraps; no blocking overlay observed. Not every screenshot received independent pixel-by-pixel review.

Scope excludes mobile, user's computer, production, authentication/permissions, exhaustive report full-text correctness, accessibility and whole-project acceptance. No push performed by this test agent. Historical failed runs do not describe final status.

Screenshot upload was blocked by the approval layer because image sharing was not explicitly authorized. No retry or alternate upload was attempted; images remain local pending user approval. Code, text results and test harness are the PR deliverables.
