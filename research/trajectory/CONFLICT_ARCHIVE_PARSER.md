# Isolated conflict archive member parser

Base04b793aa3e5f4faf9653e8906c1ee42be857f12e; branch feat/conflict-archive-parser.
Depends on unmerged archive/revision/CAS candidate stack. No runtime export/import
wiring or protection changes, new outer version allocation, migration or restoration.

## Deliverables

- contracts/conflict-archive-member-v1.md and closed conflict-archive.schema.json.
- working_records_archive/conflicts.py: pure member parsing plus explicit package
  dependencies, canonical chain/preimage/current-state checks, raw audit attributes,
  source registration and custody-anchor version checks, unknown legacy prefixes,
  bounded input and explicit exceptions. No case/source-file I/O, DB or network;
  checked-in schemas may be loaded by existing contract loader.
- Synthetic tests using ordinary API-produced conflict revisions plus constructed
  malformed payloads. These are not restricted historical-report integrity probes,
  ECFC operations, browser tests, private data or model calls.

Current writer schema, permissions, routes, table allowlist and existing mcase parser
are unchanged. Search of runtime source finds only the module's own schema reference;
no product call site invokes it. Ordinary export409 is explicitly retained in tests.

## Actual developer verification

```
service/.venv/bin/pytest -q service/tests/test_conflict_archive_parser.py service/tests/test_conflict_archive_dependencies.py service/tests/test_contracts.py
```
56 passed in14.87s, after adding update-only status/resolution enforcement. A subsequent
new regression specifically for this constraint passed separately:
```
service/.venv/bin/pytest -q service/tests/test_conflict_archive_parser.py::test_update_cannot_describe_an_observation_replacement
```
1 passed in0.41s. No runtime code changes after these checks. Earlier narrower sets:
44 passed, then52 passed (before the final PATCH constraint); do not double-count.
No failed tests in this parser turn. `git diff --check` passed.

Tests retain exact Unicode and null/absent data, three versions and original audit
links, both empty and partial legacy histories, explicit registered-version changes,
unknown historical registry preimage, missing dependencies/foreign case, malformed
versions/types/keys/UTF8/UTC, altered source anchors, missing/duplicate revision links,
omitted last captured revision, budget failure without truncation, no DB/file mutation
and continued unsupported export refusal. Version-change test alters only synthetic
registry/custody declarations, not original bytes. It does not claim actual evidence
replacement or a successful outer archive containing historical originals.

## Remaining prerequisites / limitations

Member consistency is not source authenticity. Original registry preimage may be absent;
registryDocSha256 is retained as a declaration, never relabelled byte verification.
All bytesVerified remain false. A supplied self-consistent forged history, or a missing
prefix relabelled legacy unknown, cannot be authenticated by self-contained hashes.
A future exporter must derive coverage/full inventory from trusted server records and
apply existing permission gates to all historical references. The parser does not
perform authorization. Actor headers remain untrusted declarations.

The enclosing current package parser rejects original-version replacement histories;
member parsing does not supersede that gate. An outer profile/schema, whole package
closure and mirror checks, exact transactional row/journal restoration, audit-prefix
preservation, rollback and two-restoration tests, import preview/UI contract remain
unimplemented. No conflict export→restore→export success is claimed. Other unsupported
business states are still refused. No full suite, actual browser, real case, production
or independent acceptance. No merge/deploy/push or restricted operation this turn.
