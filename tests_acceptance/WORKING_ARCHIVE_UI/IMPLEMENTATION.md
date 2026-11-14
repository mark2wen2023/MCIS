# Supplement UI implementation report

Implementer report, not independent acceptance. 2026-11-14.

- Main `web/tests/working-archive.tsx`: **27 checks**, exit 0. Disconnected default; selecting File does not transmit; filename never RPC/path; import success; export local callback; prepare-then-host-denial prevents download and clears cache; sanitized failures; unknown canonical same-package/request retry; async File after scope change discarded; oversized File not read; invalid UTF-8/depth rejected; canonical Base64 and exact 8MiB byte roundtrip; history untrusted labels; no browser storage.
- `web/tests/working-archive-integration.tsx`: actual React/HappyDOM -> TS -> Node stdio -> Python archive -> temporary SQLite export/import/list/read/remount passes exit 0. Fixture includes two fictional statements and one historical review. File selection does not RPC; local download callback receives bytes. Not a real browser disk-download assertion.
- Strict tsc on both products: exit 0.
- Parent independently checks port/boundary cases; not counted here. Catalog reviewer independently checks DOM/security behavior.

Parent review fix incorporated: downloads no longer deliver stale prepared bytes without current authorization. Every click re-exports and compares SHA and bytes before delivery; changed content demands new confirmation.

SHA256:
- WorkingArchive.tsx `8ae66e034a4b0012f0f3885fcd5e3fbd01cf5ee8cd2eb2a1ba16cff7886816d0`
- hostPort.ts `8273a5eff05b05a0f1475d96db070113d8585dc1018997ca2816ce705d0ba6ff`

Files: web/src/workingArchive/{WorkingArchive.tsx,hostPort.ts}; web/tests/{working-archive.tsx,working-archive-integration.tsx}; contracts/working-archive-ui.md; this report. No route mount, production login, external inference, deployment, merge or push.

Final wording fix: a download callback can write locally and then throw; failure now says download unconfirmed/check local results, not “not delivered”. Five added checks verify callback called once, unconfirmed wording, no false nondelivery claim, cached download removed, and no automatic duplicate delivery. Primary suite rerun 26/26 exit 0. Port unchanged.

Integration synchronization corrected after independent run exposed a fixed 150ms assumption: now waits for actual download callback or explicit failure status before asserting callback bytes. No assertion weakened. Updated real integration and strict tsc rerun exit 0 on final product hash.

Final file-input usability fix: unconfirmed import clears input.value while preserving frozen pending bytes/request. Added empty-input assertion and retained exact original retry assertion. Main suite 27/27 exit 0 after this single-line product change.
