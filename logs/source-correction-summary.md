# YANGZE public report canonical-source correction

## Verified identity
Canonical upstream `reports/yangze22/report.txt` at commit c6113bee85d25bf97d805fb2d264fb6ab138b2e2 is62607bytes, Git blob d5a6b5fc79ad0371c8ccc372b40ca9110d5c30c4, SHA256 bca8f8b8ba04a5d0669a121bc6c9380c8cd6f8397f67be2d0b30b38871c22ef2. Initial local materialization appended one LF, yielding62608bytes and SHA2567adad5bb499c28eb3985b79411c61dad593797e0d2a8aa64feb203077e43ee2b. That erroneous local digest was pinned in three places. The canonical upstream report never changed.

Root recovered canonical bytes and retained the erroneous copy outside the repository. This implementation did not edit the report. Only seed pin, excerpt pin and template citation digest changed. No normalization or dual-hash allowance added.

## Verification
New test expectations hardcode upstream SHA256, byte count and Git blob independently of production constants. Canonical loads and yields excerpts; one/two LF or CRLF suffixes are strictly rejected by both source loading and excerpts. Fresh app/DB creates EV-201 with canonical raw bytes/hash and custody registration. Tests also construct an isolated legacy bad-pin DB and prove restart does not mutate its evidence, blob, custody lines or audit.

Self-tests and affected regression25/25 passed: logs/source-correction-selftest.txt. First attempt had2 test implementation errors (treated SQLAlchemy custody rows as dicts and compared ORM identity across sessions), corrected to attribute reads and immutable line values; original failed log retained at source-correction-selftest-first.txt. This was not a change to acceptance criteria. Independent canonical red baseline supplied by root remains separately preserved. Final independent clean-snapshot/full-service verification pending.

## Historical qualification and migration boundary
Old logs/freeze manifests remain untouched. Their checks performed against the erroneous local report cannot establish canonical source identity, canonical fresh-startup readiness or canonical excerpt/source-ref validity. Tests unrelated to report bytes are not automatically invalidated, but combined historical green totals must not be represented as verification of the corrected canonical source. Existing remote main/PR source report bytes were already canonical, so restoring local bytes is not a remote report modification.

Existing databases are deliberately not migrated: seed returns before reimport when the case exists. Legacy EV-201 may retain the wrong hash/raw blob and its historical append-only custody chain. It must not be silently rewritten to pretend that the original registration used canonical bytes. Fresh-DB correctness and a future reviewed historical evidence-correction/migration workflow are separate deliverables; no migration is implemented here.

Manifest logs/source-correction-impl-hashes-frozen.txt contains4 changed implementation/test files and1 canonical report verification input. The report must not be treated as a new remote modification. Structured source metadata is in source-correction-provenance.json. No old logs overwritten, no push.
