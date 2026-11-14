# Extraction review UI implementation checks

Implementer report, not independent acceptance. Date 2026-11-14.

- Primary HappyDOM + hostPort suite: 24 assertions/check groups, exit 0.
- Strict tsc, ES2022/bundler/react-jsx, both products: exit 0.
- Real local cross-language fixture: React/HappyDOM -> TS callback -> Node child stdio -> protected Python review host -> temporary SQLite-bound source reauthorization. Two fixed fictional proposals rendered and individually reviewed (working-adopted + needs-verification), explicit not-saved/not-fact receipt, exit 0.
- No external model/API, browser IPC, production login, persistent decisions or deployment tested/claimed.
- Tests cover disconnected default; simulated labeling; reason required; unknown hides sensitive display and preserves identical retry payload; stale callback after disconnect ignored; forbidden request fields; mismatched response correlation; invalid inference/fixture marker; proper Position lonDeg/latDeg/heightM; rejected legacy lat/lon shape; empty browser stores.
- Parent review corrections incorporated: useLayoutEffect scope reset; hide results/reasons on errors; geographic schema corrected to actual contract. Independent reviewer is parent, separate report.

Product SHA256:
- ExtractionReview.tsx f162e5611b10f7632f8b8c6b9897cc8874f0cfdd446a114d754f88c8383bed82
- hostPort.ts feab80b9bcfbeb1c2a4da598ac86b430f72b2b61cdd5dab5c46e59db043ee444

Files: web/src/extractionReview/{ExtractionReview.tsx,hostPort.ts}; web/tests/{extraction-review.tsx,extraction-review-integration.tsx}; contracts/extraction-review-ui.md; this report. No push performed.

Additional checks: per-item citations must match record/round/quote; four provenance digest shapes, false signature/audit markers; review checksum and same original binding/digests. Digest displays are identifiers, not cryptographic authentication. Wrong review binding rejected.

Final hardening: request/response limits measure UTF-8 bytes; not_connected clears prior bindings; per-proposal binding memory retains only four validated digests, not extra receipt fields. Primary 24, real two-proposal fixture integration and strict tsc rerun exit 0 after these changes.
