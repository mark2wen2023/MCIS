# Conflict outer/member boundary candidate

Base0511bf8fb8fd848e9087ef220917c03e75eb20ce. Branch feat/conflict-archive-envelope.
Independent candidate on the unmerged archive/revision chain; no live wiring.

Implementation: new conflict_envelope.py checks whole expected checksum, bounded ZIP,
exact manifest inventory/role/size/member digest, case/default-policy/evidence/custody,
strict allowed member scope and exact conflict mirror. Supplies dependencies from that
same ZIP to the independently reviewed isolated member parser. Returns inspection
counts only with restore_ready=false. Experimental tag1.5.0-draft.conflicts.1 is NOT
accepted by ordinary intake; existing export and protection code remain unchanged.

Synthetic fixtures use normal conflict creates/updates and legacy evidence registration
against temporary SQLite/directories, then assemble an experimental test ZIP in memory.
This is NOT an actual conflict export from the product. Evidence text is invented.
Legacy unknown, original/captured data, declared version changes remain explicitly
unverified. No private case, browser, model, external OCR or restricted security/ECFC.

Verification commands:
```
service/.venv/bin/pytest -q service/tests/test_conflict_archive_envelope.py
service/.venv/bin/pytest -q service/tests/test_conflict_archive_envelope.py service/tests/test_conflict_archive_parser.py service/tests/test_conflict_archive_dependencies.py service/tests/test_package_intake_parser.py service/tests/test_contracts.py
```
Initial envelope tests:27 passed in4.54s. Final expanded group:127 passed in20.01s.
No failures; these are developer-side synthetic tests, not independent acceptance.
Includes expected-checksum mismatch, manifest sizes/roles/version/case/inventory,
missing member, stale mirror, changed supplied bytes, missing sources/audit/custody,
unsupported sections/working history, policy refusal, actual ZIP case aliases, legacy
unknown and replaced-original-history refusal. Valid inspection still has restore_ready
false; actual intake preview/commit remain422 and source export409 without writes.

Rollback test uses a test-only monkeypatch around the existing import_case: it imports
an ordinary supported empty-case package, asserts case row exists in the active
transaction, then invokes the inspector with an invalid synthetic envelope. It asserts
500, exact pre-call database/files unchanged, no published case or staging directory,
then removes injection and confirms normal same-package commit succeeds. No protections
are disabled; the experimental package is never passed as an accepted restore input.
This validates exception rollback plumbing, not conflict-history restoration, post-
publication crash recovery or unknown-commit guarantees. These remain untested.

Remaining: full version allocation/combined profile contract, historical sources'
current permission gate, exact immutable revision restoration, original audit prefix
retention, successful two-store/two-export roundtrip, legacy unknown preview and
unsupported-combination closure. The seam explicitly rejects working/timeline/HFACS/
track-history combinations. Hashes do not prove external truth, trustworthy identity
or availability of old original files. No browser, production or independent acceptance,
full-system suite, merge/deploy/push this turn.
