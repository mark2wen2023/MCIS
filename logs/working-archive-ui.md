# Isolated archive file interface

Added a default-disconnected component and strict trusted callback protocol for supplemental history export, explicit local-file import, historical list and read. Selecting a file does not upload it. Raw package size is capped at 8 MiB, canonical Base64 carries it in a separately bounded 12 MiB RPC; filenames, arbitrary paths, tokens and provider settings are not accepted in RPC. Unknown import results retain the identical package/request for retry, with an explicit query-history escape that does not undo a committed import.

Download clicks re-authorize export and compare both the package ID and bytes against the prepared package before requesting local delivery. Changed/denied exports clear the cached download. Delivery errors are unconfirmed, not proof no file was written; no automatic duplicate download. Read-only imported history displays all original proposals, quotations, source declarations and human opinion revisions as unverified history, never activated facts/authority.

Independent backend review found stale export could escape if sources changed during response serialization. The initial full regression was stopped. The adapter was fixed to perform final live export validation after response materialization and permission checks; the original failing test passes. No older deployed behavior was changed; this adapter had not been pushed.

Final local acceptance:
- **558/558** related Python regression passed, zero skipped, 343.99s, one existing Starlette/httpx warning.
- **41/41** primary plus independent backend suite (14 primary, 27 independent) passed on final adapter.
- **27 primary UI checks**, **13 independent port/boundary checks**, strict TypeScript passed.
- Actual React/HappyDOM file selection + callback download -> TS -> Node stdio -> Python same-database authority -> temporary SQLite export/import/list/read/remount passed. The asynchronous download test waits for actual callback bytes, not a fixed sleep.

No actual browser disk download, visual rendering, native IPC, production login, full case backup, real model call, CI, merge or deployment is claimed. The temporary fixture seeds fictional records and deletes its DB on normal process exit; its bounded protocol accepts explicitly supplied conforming archive bytes, so it is not a technical prohibition on real inputs. Tests used only synthetic data. Supplemental archive excludes complete interviews/original media and does not reconstruct identities, permissions, live proposals or sources.
