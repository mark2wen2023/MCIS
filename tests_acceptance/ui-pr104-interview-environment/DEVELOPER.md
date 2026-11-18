# UI + PR104 + interview/environment — DO NOT MERGE

Branch: `integration/ui-pr104-interview-environment`.
Tested merge: `82e01b0e9774bf6debed24f095f29ec4f1d4e86a`.
Full parents: `e22079dc06e12490cb28ea51662646d75e6bcf51` and `9cc3ecee7251b6f19a739c14ce316740c048594e`.
Common main: `94d5e38c926fda232bb987b60fa9145e4bcf01a7`.
This evidence is a documentation-only follow-up; it does not change tested product code. Original branches/main are not updated.

Only REQUESTS.md and ROADMAP.md conflicted. Both are strictly append-only relative to the common base. Resolution preserves base + complete first-parent suffix + complete second-parent suffix byte-for-byte. The later integration status row is additional. All 212 non-shared changed files matched their supplying head; exact sources and SHA-256 are in inputs.json. Product changes are disjoint: InterviewPage comes from UI/PR104 (record ?? id alias and existing case/outer/inner record identity checks); InterviewView/SourceDisclosure come from #99; environment form/model/guidance come from #101. No product edits, selective reimplementation or lost source commits. Shared dependencies and lockfiles are unchanged. Freeze list covers 75 code/contract/test/dependency paths including shared Layout. Historical freeze lists retain original-version meaning.

## Development execution, 2026-11-18

Isolated worktree; copied existing frontend node_modules, no installation/download. Node 24.22.1. Exact command, exit status and complete output for each selected invocation are in results.json. Tests are separate Node processes, fail-fast. A temporary preload disables real fetch:

```js
// /tmp/mcis-combined-no-fetch.cjs
 globalThis.fetch=()=>{throw new Error('network fetch forbidden in selected synthetic checks')};
```

Each Node command in results.json uses `--require` for that file. Run paths are relative to `web`; generated SSR bundles under tests/.tmp-combined-* and /tmp/mcis-combined-* are not committed. The record lists esbuild commands before their Node execution. No whole-suite wrapper is needed or authorized.

Selected checks:
- Two interview lifecycle scripts: independently reported 4 and 5 synthetic scenarios.
- Three environment form scripts: independently reported 3, 4 and 6 scenarios.
- Interview source disclosure and environment origin guidance: two synthetic SSR scripts passed.
- Original 19 UI scripts from the reviewed ui-pr104 selection passed; interview-report-link is included ONCE (6 actual-parent selection cases), not counted again. Covers layout/toast, COLREG, recommendation, report-review and GISIS synthetic scopes plus case-context/SSR checks.
- Inherited-citation SSR passed in three languages (15 assertions).
- TypeScript `-b --force` and Vite build passed. JS 1864.80 kB/gzip 602.63 kB; existing >1500 kB warning remains.

All selected commands exited 0; no failed/skipped commands. Counts overlap and are NOT a full-suite aggregate, historical cumulative total, or independent acceptance. The code heads' previous independent evidence remains version-specific. This combined head awaits independent review.

## Safety and limits

Scripts were statically reviewed before execution. Memory API/Promise/hook/JSX doubles do not issue requests; VM modules whitelist frontend dependencies. Ordinary error fixtures are not HTTP permission/refusal probes. Source SSR malformed strings only exercise display logic, no file/URL access. Case-context test includes existing case ID literals as URL strings; it does not read any case/seed material. No backend/Python application, HFACS core, model, real case/media content, browser, permission/refusal or paused/write-rejection tests ran. The orchestration uses Python standard-library subprocess/JSON only, without importing MCIS.

The recorded API-like calls are memory doubles, not real writes, exports or model execution. Synthetic key/cleanup and callbacks are NOT React reconciliation, concurrent rendering or event replay. SSR is not browser/visual/assistive-technology acceptance. Toast repeat announcement, full HTTP/save/readback, production identity, multi-user consistency and archive recovery remain unverified. Environment unknown readback retains existing semantics and is not a durable operation receipt.

Backend startup/archive checks remain PAUSED due seed-module import risk; seed_demo=False is not proof of no case-module loading. Do not run historical full selections: 558 belongs to the old head; the later 560 included a previously paused node. No backend formatting test was rerun here. Historic LibreOfficeDev rendering is not Word or this merge's visual validation. No new clean installation, full CI, service, model or production acceptance. A checkout is not sanitization: do not open/use real materials. Does not include later report/recommendation follow-ups or media-demo branches outside these two exact histories. Do not merge to main or deploy based on this record.
