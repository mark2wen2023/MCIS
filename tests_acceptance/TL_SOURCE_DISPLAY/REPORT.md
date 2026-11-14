# TL-SOURCE-DISPLAY

Native subagent implementation. Base main `3aba2bf03e393909c611489ae573a887087637ac`; unrelated to PR63 backend route.

## Change
EvidencePage timeline event tooltip now shows every recorded evidence ID in original order (including duplicates), source label, separate presumptive and confirmed workflow flags. Missing flags remain unknown; false presumptive means only not marked as presumptive, not established truth. All server-controlled text is HTML escaped. No source fetching/resolution, authentication change, state write or new AI reasoning. Tooltip is confined, enterable, wrapped and scrollable to keep long reference lists available.

## Verification
- 14 author + 6 independent pure tooltip cases passed. Covers all 9 flag combinations, legacy nulls, injection attempts in every dynamic field, 1001 references, frozen input unchanged, and no inference.
- Helper scoped strict TypeScript passed.
- Full `web/node_modules/.bin/tsc -b --force` passed after materializing main source/config/schema dependencies. Earlier build lacked report.schema.json and vite.config.ts in isolated workspace; fixed materialization, not production code.
- Independent source review confirmed EvidencePage wiring and no new network requests. Frozen two implementation hashes matched.
- Browser attempt: cloud CUA opening isolated ECharts fixture at `http://127.0.0.1:8793` failed `net::ERR_CONNECTION_REFUSED`. No browser screenshot, hover, scrolling or responsive behavior has been verified. No full application E2E, Vite production bundle, CI, live model or public-case capability validation claimed.

## Remaining validation
Draft only until actual EvidencePage hover, long-list scroll, narrow viewport, keyboard/accessibility and CSP behavior are checked in a reachable application. This is tooltip-only presentation, not a complete multi-source comparison table or time uncertainty model. A flow confirmation label is not an automated finding of fact. Existing server/source authorization limitations are unchanged.
