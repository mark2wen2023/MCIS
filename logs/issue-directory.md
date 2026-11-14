# Find and continue existing issue cards

Added protected host list projection and an explicit unreviewed card directory. Investigators can find a saved card, open and read its full history, then append further verification/discussion records. Opening a summary alone cannot enable writes. New cards remain separate. Nonempty drafts, busy and unknown saves block navigation; per-card known history prevents backward read acceptance when reopening.

Independent reviews covered backend scope/metadata limits and UI draft preservation, blocked summary-only editing, two cards, same/cross-card history regression and late-context isolation. Actual React/HappyDOM→trusted stdio→protected ASGI→temporary SQLite now saves five entries with pinned source EV-001, discovers/reopens via directory and appends a sixth after full read. Still synthetic temporary host, not durable user storage, production login, native browser acceptance or deployment.

Final backend307/307, zero skips; UI directory24 and all related regressions/strict TypeScript passed. Independent directory scenario and true temporary-host six-record continuation passed. Counts overlap individual suites; no CI claim.
