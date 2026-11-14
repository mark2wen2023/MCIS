# Durable working review UI implementation report

Implementer report, not independent acceptance. 2026-11-14.

- Main suite: 24 checks, exit 0. Covers disconnected; simulated labeling; dirty decision/note guards and discard; initial review; UI remount/list/read; prior history and anonymous author identifier; unknown exact request retry; failure hides source; explicit stop-retry/read without another write; history rollback; forbidden request field; context late callback; expected fixture rejects local upgrade; no browser storage.
- Actual integration: React/HappyDOM -> TS callback -> Node stdio -> new Python persistent RPC/host -> temporary SQLite. Two fictional fixture proposals generated, individually reviewed, component disconnected/remounted, directory listed, proposal reopened, second review appended; original quotes and first revision preserved. Exit 0.
- Strict tsc on both products: exit 0.
- No real LLM inference, production login, browser/native IPC, route mount, deployment or multi-process persistence claim. Independent component + host port are verified, not a delivered complete web application.

Parent review corrections incorporated: dirty decision guard; explicit discard; unknown stop-retry/read with possible-saved warning; trusted expectedProvider binding; receipt fingerprint and complete history-prefix consistency. Independent review is separate.

SHA256:
- ExtractionWorking.tsx `3ab33a2779e21ddc3e7f7286db9cd5538768e90af9d25f65ff40056bb3737f21`
- hostPort.ts `76e4f4805770b811901728aa4bfac2c5e31546d079b34c3d5d3c633ff008c467`

Files: web/src/extractionWorking/{ExtractionWorking.tsx,hostPort.ts}; web/tests/{extraction-working.tsx,extraction-working-integration.tsx}; contracts/extraction-working-ui.md; this report. No push/merge/deploy.
