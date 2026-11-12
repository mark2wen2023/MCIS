# W10.1 independent acceptance — 2026-11-12

## Decision
**Accept the desktop-only, read-only stored-track inspection slice after D01–D03 repairs.** Not W10 import/edit/cleaning completion, mobile acceptance, production deployment, model or Unity validation.

| Check | Result |
|---|---|
| Actual HTTP + persisted DB comparison | 15/15 |
| Real Chromium | 40 passed + 1 existing shared-shell mobile KnownDefect |
| Independent model/parser/math tests | 38/38 |
| Independent navigation event lifecycle | 7/7 |
| Final implementation SHA-256 freeze | 9/9 exact |
| Runtime Python main source baseline | 80/80 exact, no differences |

Main baseline: `b64812bd9ed3a856a31c1e8df9b3ce843b2af659` (W20 included). Default model remains unconfigured: runner explicitly blanks agent base URL/model, performs no agent call, and asserts every observed UI API request is GET. No production service source changed.

## Findings retained and retested
- **D01:** independently reproduced a delayed old tracks result after rapid navigation/Back. Original failure assertion retained. Repaired navigation invalidation now suppresses it and allows a fresh read immediately, not a permanently disabled loading state.
- **D02:** independent 1001-vessel metadata budget assertion failed on the original version. Final parser separately bounds vessels and track buckets at 1000. Tests retain exact 1000/1001 boundaries; browser verifies rejection without partial data.
- **D03:** first D01 repair wrongly cancelled initial requests in a newly reached case when arrival hashchange fired after subscription. Reproduced twice through actual same-document navigation; captured page text showed the new case plus cancellation warning. Dedicated navigation unit assertion was red. Final repair binds history events to subscription URL; normal case change, original fast Back, recovery read and Back/Forward all pass without loosening the assertions.

Full history and K01: DEFECTS/W10.1.md. Pre-fix browser/model/navigation result evidence retained separately.

## Actual behavior verified
Real HTTP reads compare all **2051 synthetic persisted points byte-value-for-JSON-value** to database rows: no interpolation or silent edits, including negative relative time, zero speed, 360° angle, poles and ±180° longitude. Inclusive 0–100s window returns original point objects only. Empty non-fictional-flag case and registered vessel without tracks remain honest empty states. Six default role policies read successfully according to actual gateway settings. Case overview/audit and stored JSON remain unchanged after reading.

Real browser: no blank screen/overlay; UTC exact text; real two-vessel selection; source filter including unknown/empty type; 100-row pagination; keyboard point selection; refresh resets selection/filter/page; field edits do not issue requests until submit; invalid window does not issue network. All track requests omit stepSec. Plot shows 2000 actual indexed samples from 2051 points with explicit warning. A mocked 50000-point upper-bound payload retains all 500 table pages; choosing the final plotted sample selects exact point 50000. 50001 points, wrong case/vessel, invalid UTC/coordinates, 403/404/500 and excess metadata fail closed. Delayed navigation, cross-case and identity responses do not leak prior data. Malicious source/name strings render as inert literal text, not scripts/images.

Failure, malformed, budget and delayed-response scenarios use deliberate endpoint doubles in the real browser; they are not claims about live-service error generation. Pure-function tests are separate from browser counts.

## Layout and accessibility
1440×900 and 1920×1080 screenshots were inspected, including scrolled scatter/table surfaces. Labels, source cautions, chart limits and tabular records are legible with no overlaps or outer horizontal overflow. Table headers have column scopes, the horizontal table region is labeled/focusable, and point buttons work with keyboard Enter and expose pressed state. Interactive SVG circles have a keyboard-accessible table alternative.

Known mobile limitation: at 390×844 full document is 934px wide; hiding all W10 content leaves 934px, proving existing shared shell/topbar width. No new W10 outer overflow. Mobile is not marked passed. Scatter appearance is deliberately not a geographic/nautical map: axes and disclaimers preserve the original read-only scope; dense synthetic collinear dots can visually resemble a line but no connecting path/interpolation is generated.

## Environment and reproduction
Use README commands. Existing Playwright and existing official Chrome headless shell; no software installed. Service, Vite and browser launched in one process tree with loopback 18810/15810; new temporary DB/blob storage; only explicitly synthetic QA fixtures and fictional Lily/Mary. The runtime copy used here contains all 80 Python files exactly matching the main commit (service-baseline.json). It isolates concurrent work, not a forked API implementation. CUA loopback access had previously failed; continuing engineering-test authorization covered the existing local test harness. Final servers are stopped by runner finally.

## Evidence/publication boundary
Commit only test sources, README, this review, DEFECTS and selected final/pre-fix text/JSON evidence plus freeze check. Do not commit runtime copies, generated .tmp bundles, database, browser binaries, fixture files or screenshots. Local screenshots: track-1440.png / track-1920.png, track-chart-1440.png / track-chart-1920.png, track-mobile.png, goto-failure.png. Exact commands/overrides are documented in README; default runner operates in a normal full checkout.

Remaining unaccepted: NMEA/CSV ingestion and mapping, cleanup/recovery, editing/saving/audit, Hermite/ENU/antenna corrections, simulator launch, authenticated production access, backend resource budgets, model inference and mobile shell repair. Whole-service aggregate regressions are reported separately by implementation coordinator, not inferred from this slice.
