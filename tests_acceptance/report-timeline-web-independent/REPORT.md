# Timeline 1.4 frontend — independent scoped review

Tree `/workspace/mcis-report-timeline-web`, branch `feature/report-timeline-web-v1`, parent `fe36587`. Read AGENTS/handoff, six frozen files and frontend diff. No reviewer implementation changes, push, merge or deployment. Backend product diff is empty. **No browser was launched by this reviewer; browser acceptance remains blocked.**

## Actual independent checks

1. Ran the frozen real_api.py logic with only its output-directory literal relocated into this independent directory (`real_api_relocated.py`; no behavioral/test changes). Real temporary source/target API/SQLite workflow: 1.4 preview200/commit200/lookup200, exact timeline rows restored, Investigator preview403, mixed track-version preview422 with zero target cases. Output: `api-results.txt`.
2. Bundled and executed the supplied `package-timeline-v14.test.tsx` with MCIS_REAL_TIMELINE_RESPONSES pointing to these freshly generated actual responses. Synthetic negative cases, actual preview/commit/lookup parsing and SSR all passed (`frontend-results.txt`). This is real ASGI/TestClient API data passed through the frontend model; it is not an in-browser HTTP workflow.
3. Added `extra.tsx`: **25 independent assertions passed** (`extra-results.txt`) using actual-response-derived mutations. Covers absent/wrong/extra working extension fields, nonfinite/out-of-range counts, receipt case/size/version/hash/count mismatches, malformed HFACS identity/receipt/version/count/extra-field combinations, escaped synthetic script-like title and correct1.4/no-track-history SSR labeling.
4. Ran `web/node_modules/.bin/tsc -b --force`: exit0, no diagnostics (`typecheck.txt`). An initial independent runner used an incorrect source-relative output path; corrected that harness only and retained `initial-runner-path-error.txt`. No product failure hidden by that correction.
5. `sha256sum -c logs/report-timeline-web-impl-hashes-frozen.txt`: **all six OK** (`hash-check.txt`).

Fresh JSON/ZIP responses and bundled .cjs executables are local generated artifacts, not intended review/commit files. Sources, reports and text logs provide the reviewable evidence. The relocated API script differs only in the artifact output path.

## Code / binding assessment

The allowed version list adds exactly1.4, retaining rejection of unknown versions. For1.4, workingRecordsExtension must have the exact existing working-v1 keys, archive-only receipts and unverified-self-reported identity; working-v2 or trackReceiptCount is rejected. Optional HFACS still follows its prior strict version/shape/count checks. Receipt parsing retains preview-bound case/title/profile/size/version/hash/counts and working/HFACS extension comparison; mismatches do not become confirmed success.

Both preview and receipt pass packageVersion into WorkingRecordsSummary, preventing1.4 from being mislabeled1.2 solely because its working profile is v1. Text describes the256-event limit, unsupported track-history mixture and other nonempty excluded states, historical confirmation/source flags, default-Investigator denial and same-case/new-case-only restore. The model does not independently inspect archive bytes; backend validators remain responsible for actual timeline members, source closure and permissions. UI version recognition is not permission elevation or evidence authenticity.

Export/import scope text does not promise universal/full-system backup and retains restrictions. Existing commit/unknown-state control-flow was not changed by this diff. No new retry/delete or permission editing was introduced. SSR text escaping passed the independent title probe, but SSR is not proof of hydration, navigation or interactive state correctness.

## Browser and broader validation limits

Coordinator reported sandbox-enabled Chromium startup failure involving SUID helper ownership and read-only uid_map. This reviewer honored the boundary: **no --no-sandbox attempt, no browser bypass and no browser acceptance claim**. Page launch, actual file picker, confirmation/button interactions, browser console/overlay, reload or late response/identity behavior, keyboard/mobile/visual rendering and screenshots remain unverified in a browser.

Coordinator's W83/W85/HFACS/track tests and production build results are separate evidence, not independently rerun here. Their build chunk-size warning remains; it is not resolved by this work. No full-suite, production performance or real SSO validation. Existing backend scope/long-lock/memory/FS–DB crash-atomicity limitations remain unchanged.

## Disposition

**Code/model/SSR/real-API-response scoped checks pass; complete browser UI acceptance remains BLOCKED by the recorded environment limitation.** No new implementation defect found within executed checks. This supports1.4 frontend model and explanatory wiring review, not a claim that the end-user browser workflow has been successfully exercised. A sandbox-capable environment is still required for that remaining acceptance.
