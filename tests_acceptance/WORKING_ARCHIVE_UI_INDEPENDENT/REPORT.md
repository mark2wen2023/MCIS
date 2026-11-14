# Independent archive UI review

Coordinator independently inspected the component and strict callback port. Required corrections were implemented before final acceptance:
1. Download clicks re-export through the authorized host and compare both checksum and bytes to the prepared package, rather than delivering an old cached package after permission may have expired.
2. A delivery callback can write a file then throw. The UI now says download is unconfirmed and asks the user to inspect local results, never falsely asserting no delivery or automatically retrying delivery.
3. Unknown import clears the file input control while retaining the immutable pending package, so an explicit later reselection is not blocked by the browser retaining the same file.
4. The cross-language test originally used a fixed 150 ms pause before asserting delivery. Independent rerun exposed that timing assumption. It now awaits the actual download callback or an explicit failure, and still requires the real package bytes.

Final coordinator rerun:
- strict TypeScript passed;
- 27 primary component/port assertions passed;
- 13 independent port/boundary assertions passed (`web/tests/working-archive-independent.ts`), including activated/verified histories, wrong-case/authority/permissions, mismatched package identity, old-context replies, noncanonical Base64, oversize bytes and invalid UTF-8 rejection;
- actual React/HappyDOM file selection, explicit import, download callback, Node stdio, Python authorization, temporary SQLite archive export/import/list/read and UI remount passed.

Selecting a file does not upload it; the user must explicitly import. Context replacement suppresses late file reads and host replies. Unknown imports retain the original request/package for idempotent retry, with an explicit state-query escape that is not cancellation. Historical claims remain unverified and cannot activate source data, identities or facts.

Final hashes:
- WorkingArchive.tsx `8ae66e034a4b0012f0f3885fcd5e3fbd01cf5ee8cd2eb2a1ba16cff7886816d0`
- hostPort.ts `8273a5eff05b05a0f1475d96db070113d8585dc1018997ca2816ce705d0ba6ff`

No real-browser file landing, visual rendering, native IPC, production login, real model or external network acceptance is claimed. The callback test proves delivered bytes, not an actual browser download saved on disk. The fixture seeds fictional data but its bounded import protocol can accept explicitly supplied conforming archive bytes; tests used synthetic data only.
