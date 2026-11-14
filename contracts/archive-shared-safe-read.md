# Archive/history read prerequisite and restore boundary

Scope: shared safe file reader, not new saved-run tables, generation IDs or
human approval. No archive format, manifest, importer, restore, role policy,
activation, database table or historical authority behavior is changed.

The descriptor-relative bounded reader is extracted to common/safe_files.py.
Both registered intake and archive/history reads use it, eliminating the old
archive path-check/leaf-open parent race and fdopen directory-failure leak.
Intake wrapper retains MAX_BYTES8MiB and existing integrity rejection semantics.
Archive passes its own per-call budget, normally16MiB; existing caller budgets
(1MiB/256KiB track files and32MiB package provenance) remain unchanged. A typed
ReadBudgetExceeded preserves ARCHIVE_BUDGET413; missing/unsafe files remain409.
Missing descriptor capability returns ARCHIVE_SAFE_READ_UNAVAILABLE503 without
unsafe fallback. The existing archive path and symlink checks remain in place.
Oversize status/code remain413/ARCHIVE_BUDGET; message now says current read
budget instead of a misleading fixed16MiB for every caller.

Linux is actually tested. Other operating systems are not certified. Directory
read/search permission requirements and lack of atomic file/database storage
remain as documented in intake-descriptor-relative-read.md. Writer paths and
legacy assembler reads not routed through read_blob are not claimed repaired.
No filesystem permission changes or privilege escalation performed.

## Restore/generation boundary verified rather than invented
A new isolated case registers actual CSV bytes, exports a real working-record
archive, previews/commits it into a separate empty service, then reads the original
through authorized archive-history content. Bytes are identical; Public denied403.
Attempting registered timeline preview on the restored evidence returns409
ARCHIVE_HISTORY_ONLY, not an active receipt. This tests existing history isolation;
it does NOT implement a general local generation/receipt lifecycle for stageA.

## Primary tests
New5 local archive reader tests cover per-call budget/413, directory FD cleanup,
parent replacement after open, unsupported platform503, and default archive read
larger than8MiB (so shared helper cannot inherit intake's limit). Actual archive
roundtrip1 passes. Earlier primary5/independent9 reader checks also rerun.
No browser/LLM/CI/full-system claims. Native implementation/review. No merge/deploy.
Final independent/regression results below.

Independent12 new tests plus primary/restore/earlier reader tests pass32/32,
zero skips. Cover exact256KiB/1MiB/16MiB/32MiB and+1-byte limits, missing capability,
FIFO/read-failure cleanup, zero budget/short reads and path escape rejection.
Large regression147/147 pass, zero skips, including actual W2 and legacy package
roundtrips. After the final budget-message wording correction, all32 directly
related checks reran and passed. Counts overlap; existing Starlette warning only.
No new generation or active restored receipt is introduced.
