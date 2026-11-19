# Internal generation-only report snapshot candidate

Baseline: 97133a468020e5e7ab9f2f3d9246c3db63f4331a. This narrow parser addresses the full-generation exception to the broader history-replay blocker in report-sentence-media-binding-draft.md. It does not implement that binding.

Evidence: reports/service.py create_report validates the complete report, stores it and calls append_operation with report.generate/report.regenerate and full afterValue; append_operation deep-copies it into ReportAuditRow, with auditSeq and a report-snapshot:RA-* audit link. audit/service.py to_doc exposes that link. get_snapshot supplies snapshotId. Review and export snapshots are not full-generation sources and are outside this parser. report.colreg.draft is also deliberately outside this first slice.

`generation_sentence` consumes a caller-selected get_snapshot-shaped document and audit.to_doc-shaped event, plus exact case/report/section/sentence identities. The caller must supply existing contracts.validate('report', value) semantics; the parser does not import the application, open schemas or read storage. In the offline check that callback uses the actual local report.schema.json with Draft202012Validator. Complete report validation precedes anchor lookup; regeneration also validates its full parent snapshot. Identity, action, audit sequence/link, null operation anchors, family/parent/version and unique section/sentence addresses must agree. There is no current/latest fallback or history replay. Failures raise; no raw body appears in parser's own error message (caller must also sanitize schema exceptions).

Output contains RA identity, audit sequence, report family/version, section/sentence address and a deep-copied complete sentence, including its existing generatedText, citations and review fields. It does not add media IDs, invent trusted hashes, alter report formats or claim the sentence cites a saved media revision. Existing schemas, report generation, export and digest calculations are unchanged.

The word frozen means the explicitly selected generation value, not an immutable Python object or proof of immutable storage. Input provenance, snapshot authenticity, hash-chain validation, permission intersection and a consistent read view are caller prerequisites, not properties proven by these dictionaries. No production caller is connected. Current report version alone still cannot identify reviewed content; legacy reports without a selected valid full-generation RA must not be guessed. Later review state is not replayed.

## Development check (normal synthetic only)

`python tests_acceptance/report-generation-snapshot/check.py`

Two handmade, schema-valid full generations; old/new exact sentence text and identities; simulated edits to separate current report objects leave selected generation results unchanged; consumer edits to returned copy do not mutate original input. Uses standard library plus existing jsonschema, loads only the standalone parser and non-case report schema. No application/package startup, network, database, Save, audit writes, permissions, recovery, media or models. No negative permission/fault probes. This is development verification, not independent acceptance, real generation, ORM or service testing.

Next gate remains trusted server selection of RA and same-view audit/media data after established authorization intersection. A durable sentence-to-media binding is absent. This candidate does not relax startup/archival pauses.
