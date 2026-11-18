# Three UI groups — DO NOT MERGE / pending combined independent acceptance

This candidate combines only the three exact heads in inputs.json: navigation 076eec1, recommendations 2064675, reports 81a308c, on main 94d5e38. All are ancestors. PR104, PR67, media, Pi and other candidates are excluded. No new functional edits.

## Source preservation and dependencies

Each pair has main as merge base and only REQUESTS.md / ROADMAP.md as common changed paths. Both document conflicts were resolved by retaining the main prefix and every complete group append in order (one, two, three), checked byte-for-byte. Every non-document input file matches its exact source blob; complete changed-path union was verified before integration evidence was added. inputs.json records the per-file source mapping. Prior group documents/freezes remain historical evidence for their respective heads.

Shared Toast dependency was reviewed: group one changes provider expiry identity and live-region structure, but useToast.run return/error contract is unchanged. Recommendation tests evaluate the actual combined useToast.run with synthetic hooks; they do not mount the provider together with the complete page. COLREG uses a toast stub. Report feedback has its own state. No semantic conflict was identified within these inspected boundaries; this is not complete UI interaction certification.

## Developer execution on combined code

Exact per-command outputs in selected-results.json. Nineteen distinct selected test scripts passed (12 navigation, 3 recommendations, 4 reports), zero failed/skipped. These are repeats of bounded existing synthetic checks, not nineteen end-to-end workflows or additional unique coverage over earlier runs. Only these previously individually reviewed scripts were selected, no glob/full suite.

From web/: node commands listed in selected-results.json; three TS/TSX scripts first bundled with existing local esbuild into temporary files. npm run build passed (tsc -b and Vite 8.3.8, 767 modules). JS 1,861.39 kB / gzip 601.44 kB; existing >1500 kB chunk warning remains. Installed dependencies reused, no fresh-install verification.

Tests use synthetic data, hooks, promise responses, pure routing and SSR. No real HTTP/backend, service, browser, models, production data or permission/refusal probes. No paused or write-refusal tests ran. Builds and temporary bundles are not delivered.

## Required acceptance and limitations

- This combined head has developer regression/build evidence only; earlier independent group reviews do not certify the three-group combination. Browser, visual, accessibility, complete CI, real backend, cross-page interactions and production permissions remain unverified. No main merge/deployment.
- PR104 is NOT included; its report source/export repairs and acceptance cannot be attributed to this candidate. Later integration must inspect report-file overlap explicitly.
- Toast repeated-identical announcement and unmount timer behavior remain unverified in real assistive technology/browser.
- Interview/current recommendation links do not certify historical versions or sentence-level traceability. Missing items are not proof of deletion or access denial.
- COLREG ignored replies may already have generated output; drafts use current server context, not a historical selected run. Local retained work is not persistent recovery or cancellation.
- Missing analysis scenario has an explicit baseline exit but hides local case/source controls; real clicks/navigation remain untested.
- Recommendation draft counters protect selected in-page completion cases, not backend concurrency or cross-page persistence. Parent reload/unmount lifecycle is not fully exercised.
- Report review is tested after busy render, not queued pre-render edits or complete parent close lifecycle. GISIS ordinary late errors are tested synthetically; 403 and structured error mapping remain static-only, not executed. No backend version or safe retry guarantee.

Use the combined freeze for code review (includes Layout); all group-specific restrictions remain applicable. DO NOT MERGE until normal independent acceptance and required checks.
