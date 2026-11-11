# Canonical-source independent green review

Actual run location: canonical-source-snapshot-8680, not previous mcis-work. PYTHONPATH explicitly points to snapshot/service; MCIS_CANONICAL_SNAPSHOT absolute path asserted in independent fixture. Imported PROJECT_ROOT and seed/public_text module filesystem paths checked to be inside that snapshot. Shared .venv is dependency reuse only. Independent test file copied byte-for-byte from original worktree; both SHA256=1e06629bd700a9a85830ffa240a02466c129e7ccbe041521ae6172dca7417cfc. Five corrected frozen file hashes match snapshot (snapshot-hash-check.txt).

## Execution
`service/.venv/bin/python -m pytest tests_acceptance/source_correction/test_canonical_independent.py service/tests/test_yangze_canonical_source_correction.py service/tests/test_yangze22_seed.py service/tests/test_reports_w161_public_text.py service/tests/test_reports_w161_public_templates.py service/tests/test_reports_w161_public_flow.py -q`

**32 passed, 0 skipped, 10.37s**. Five newly authored independent tests plus27 implementation/existing regressions, not32 wholly new independent cases. TestClient/temp databases, not external HTTP/browser. Environment: PYTHONPATH=<snapshot>/service; MCIS_CANONICAL_SNAPSHOT=<snapshot>; MCIS_DOTNET/DOTNET_ROOT persistent SDK8.0.428; persistent DOTNET_CLI_HOME. Raw log canonical-green.txt.

- Exact62607 source bytes, SHA256 bca8f8b8ba04a5d0669a121bc6c9380c8cd6f8397f67be2d0b30b38871c22ef2, Git blob d5a6b5fc79ad0371c8ccc372b40ca9110d5c30c4 independently hardcoded.
- Fresh app initializes; EV-201 stored blob exactly canonical, metadata and custody event digest canonical, audit chain valid.
- Real bounded excerpts exist, correct digest and physical line ranges reconstruct exact quote. No normalization to accept altered source.
- Appended singleLF rejected by load_source and excerpts. Existing frozen correction tests additionally cover doubleLF/CRLF and old DB with bad pin.
- YANGZE all three templates create authorized-public reports and produce actual PDF/DOCX bytes with matching export digest. Existing Haili flow also executes report review/regeneration/export and GISIS checks.
- Historical wrong-pin DB fixture is deliberately constructed in isolation, then corrected seeder returnsFalse with evidence/audit/custody/blob untouched. This proves no silent migration, NOT that old data has been repaired. Persistent historical DBs require separate authorized handling.

## Qualification
This verifies corrected canonical-source behavior on a source-complete-for-this-suite snapshot, NOT a complete git clone or the whole remote PR. Parent's manifest has722included/633missing entries; no independent assertion that absent historical logs/Unity scenes/screenshots/PDF/OTF are irrelevant to every project test. This suite does not replace new full-service/provenance/browser validation. Previous363 old-local-input pass remains revoked as evidence of clean-PR green. Old red evidence preserved. No source text alteration, push, screenshot upload or deployment by this reviewer.
