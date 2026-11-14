# Main-based integration candidate (local only)

Base main3aba2bf; only cb04aa6→ee6071f→72269e3→13231d4 single-commit changes and
PR61 aad96d4, PR64 5d10b67, plus explicit integration gate below. No97-commit/PR56 stack,
PR69 multimodal slice or low-lock prototype. All access transactions remain full-lock A.

Conflict resolution: evidence GET retains safe recorded-digest read and its matching current
SHA, then checks ZIP/DOCX full-content access on those same bytes before Access. Intake
receipt and historical paths retain their respective digest/permission/filename checks.

Additional gap closure: legacy full-case export checks assembled byte members using PR64's
protect_container before generating ZIP, so old-style registered containers cannot bypass
the individual-download gate merely by exporting a case without report/intake/history rows.
No decompression/extension trust. Denial rolls back export audit in existing transaction.
Non-container bytes retain current semantics; working archive already requires full content.

Limits unchanged: whole-file memory use, long writer lock, local unverified role headers,
trusted database records vs source authenticity, missing legacy digest refusal/no silent
backfill, no automatic retry of unknown commit. No integration/deployment acceptance yet.
