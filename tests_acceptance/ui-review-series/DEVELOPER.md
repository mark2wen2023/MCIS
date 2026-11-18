# Review-only UI series integration — NOT FOR PRODUCTION / DO NOT MERGE

Tested merge: `661d73ff62a981af5ed64751c606b8e5129d42c0`.
Branch: `integration/ui-review-series`.
Parents: `13d7311f9fb370ddafbba4ba27e29d48a1eab3f6` and `23d347a6df90edec6d1ec6f1934c6865836f759f`.
Common ancestor: `9cc3ecee7251b6f19a739c14ce316740c048594e`.
`be1c887421ecc06a77330a1f118808562af20ae4` is NOT an ancestor (checked on merged HEAD). Both complete pinned parent histories are retained. Main and source branches unchanged. This record is a documentation-only follow-up to the tested merge.

## Important unresolved risks

**Code-review candidate only, not production-ready.** Excluding be1c887 does NOT remove all React interrupted/discarded-render risks: 23d347a still assigns `Detail.latestProgress.current` and `useBoardLoad.source.current` during render. Synthetic hooks do not prove concurrent React scheduling or event replay safety. A→B→A source change protection is unresolved. No server revision/CAS or durable operation receipt was implemented. The included operation-receipt document is an older design proposal, not an implementation or the latest complete specification. Unknown progress remains locked with manual copy/check guidance; reloading is not proof of request outcome or an atomic board/audit snapshot.

## Preservation checks

Only ROADMAP conflicted; REQUESTS auto-merged. Both documents were explicitly reconstructed as the exact current 13d7311 bytes plus the complete 23d347a suffix after the common ancestor. This preserves earlier middle insertions and all existing text. The new status row follows separately. All 70 non-shared changed files relative to the common ancestor match their supplying head byte-for-byte; inputs.json records their sources/hashes. Report/Recommendation code and updated tests come from 23d347a, #99/#101 from the current combination. InterviewPage retains record/id alias and case/outer/inner identity checks. No product edits. New freeze covers 84 retained/current paths, including shared Layout; old freezes are historical and are not all expected to match this combination.

## Development-only limited checks (2026-11-18)

Isolated worktree, existing node_modules copied; no new installation. Exact commands, exit codes and output in results.json. Commands run from web, fail-fast, each Node test a separate process. The temporary preload was:

```js
// /tmp/mcis-review-series-no-fetch.cjs
 globalThis.fetch=()=>{throw Error('fetch forbidden in selected synthetic checks')};
```

Each Node command includes `--require` for that file; generated SSR bundles are not committed. All selected tests were statically reviewed, including changes to older recommendation fixtures. Memory API/Promise responses only; ordinary communication/callback errors are frontend synthetic cases, not backend fault injection or permission/refusal tests. No application imports, real cases/seeds/media, services, model, HFACS, browser, paused/write-rejection tests or backend tests were run. Python standard-library orchestration/hash checks do not import MCIS. A repository checkout is not data sanitization.

Passed individually:
- report-refresh-section: 12 synthetic scenarios;
- recommendation pending-context, progress-flight, progress-snapshot, read-lifecycle, read-state, case-read-label, reload-action-window;
- updated recommendation form-save, transition-note and missing-citation;
- two interview lifecycle scripts and three environment form scripts;
- two source SSR scripts;
- interview-report-link, GISIS stale/parent/feedback scripts, report-review-pending and inherited-citation SSR;
- TypeScript `-b --force` and Vite build, with existing >1500 kB chunk warning.

No failures or skips in selected commands. Do not add scenario counts or historical results into a full-suite total. No full UI wrapper, original full report-render/refusal file or full suite ran. Prior independent evidence is version-specific; this integration awaits independent review.

Not validated: actual React reconciliation/concurrency, browser/visual/accessibility, HTTP, backend identity/permissions, multi-user consistency, clean dependency installation, full CI, Word, archive recovery. Backend startup/archive checks remain paused for seed-module import risk. Historical LibreOfficeDev evidence is not Word or this head's visual acceptance. Historical 558/560 selections are not rerun permissions. This branch does not include media-demo candidates, be1c887 or later unselected repairs. Do not merge main or deploy.
