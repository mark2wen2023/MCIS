# Human judgment source-version intent gap (ordinary functional assessment)

Remote main observed94d5e38. Separate branch research/conflict-source-intent-gap
based onbe93cfa (existing conflict history/version/draft candidate), not the expert
budget branch. No product/permission changes, file-original access or restricted tests.

Existing revisions.py captures before/after and audit references, retains original
source binding for unchanged observations, marks old missing history unknown, and
sets bytesVerified=false. This already solves forward history preservation; do not
implement it again. write_version hashes conflict document and revision digest,
not the then-current evidence registry. bindings captures current registered digest
when observation content changes. This is documented capture-time behavior, not a
claim that the human read that version. Header actor identity is still unverified.

New synthetic ordinary HTTP test demonstrates:
1. Create conflict linked to registered digestA; obtain editable conflict token.
2. Append normal synthetic custody Change to registered digestB (no original file).
3. Token remains unchanged. POST changed observation with original token succeeds201.
4. History retains A preimage and binds new observation to B, bytesVerified=false.
No history loss or proven permission bypass. This is NOT source tamper/security
reverification; it establishes the contract gap between capture time and read time.

No sufficient current contract to safely infer human-confirmed source version.
GET conflicts:editable uses timeline policy; history requires full-content and
source visibility checks. Adding source metadata to editable without that gate would
change disclosure semantics. New writes require explicit source-read snapshot/token
binding per changed observation, issued under existing source permissions and checked
in the same write transaction; absence must be honest unknown or explicit rejection,
not silently mark current digest as reviewed. Caller claiming a digest is not proof
of reading original bytes. UI/source read path and legacy-client tightening must be
specified together. Existing resolution-only edits should retain their historic
binding, not silently rebind to newest evidence. Old history must not be backfilled.
A whole-current-registry hash added to conflict token would only reject changes;
it still would not prove which source the reviewer actually read.

Decision: stop at reproducible assessment, no speculative production fix or new
permission route. Next scoped implementation needs a source-view receipt contract
(registry observation vs actual same-read bytes clearly separated), client handling,
missing/changed/stale response semantics and reviewed policy integration. Do not
reuse previously restricted history/file-integrity probes to establish this.

Command from service:
.venv/bin/pytest -q tests/test_conflict_source_intent_gap.py tests/test_conflict_revisions.py::test_source_version_kept_when_only_resolution_changes tests/test_conflict_revisions.py::test_legacy_baseline_is_unknown_not_invented
Result3 passed in0.51s, all developer synthetic registry tests. One new gap test,
two existing regressions. No public PDF bytes, real model, browser, production or
independent acceptance. No merge/deploy/push. This test records existing behavior,
not an assertion that stronger human source-verification is implemented.
