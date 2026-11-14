# Registered comparison coverage display

Result area now describes checked registered file count, never independent evidence
count. Single registered source explicitly cannot yield cross-source comparison.
Multiple extracts declaring the same parent show their IDs and shared parent ID;
this does not certify their actual content relation. Different/unlinked files are
also explicitly not assumed independent. Import diagnostics and clock warnings
remain visible; this adds no source-quality score or fact approval.

The component uses only already-validated sourceSnapshots/reportSnapshots. No
backend, permissions, persistent data or evidence changes. No LLM involvement.

Primary11 static React render assertions, existing53 HappyDOM/control-fetch
regressions and TypeScript/Vite build passed. Browser validation was attempted:
available system Chromium failed process_singleton socket creation with Operation
not permitted, both ordinary and approved escalated launch. No security setting
changed or limitation bypassed. No actual browser visuals/E2E claim. Existing
bundle-size warning remains. CI not claimed; no merge/deploy.

Separate native reviewer added10 grouping/render checks (multiple parent groups,
duplicate extract de-duplication, missing parent links and React escaping) and57
integration checks (includes prior53 plus4 visibility/clear checks). Both passed.
Initial SSR test invocation used incompatible ESM; CJS invocation passed, not a
product defect. Reproduce SSR tests using esbuild --bundle --platform=node
--format=cjs --jsx=automatic then node; integration uses existing HappyDOM bundle
setup. These overlapping suites must not be added as unique check totals.

Integration base fa94bd6 preserves concurrent same-case CSV candidate filtering.
Latest component fetched from that commit, then only coverage import/render added;
no older source selector or fixture overwrote the concurrent change. Primary53,
coverage integration57 and build reran successfully on combined code.
