# IQ-1A archive: experimental read-only validation slice

Checked 2026-11-13: Draft PR #47 remote head d90b17338eba5eacb436eaff161c3c416fd23380, base 3aba2bf. This workspace imports that source tree locally. `validate.py` is research-only, not installed or called by production; it cannot export/import/restore `.mcase`, change permissions or remove the existing blocking guard.

This validates a consistent synthetic snapshot by deterministic event replay, exact 1:1 event/receipt matching, reconstruction of append request digests (create digests remain opaque because original source order is lost), and explicit permission and byte/hash checks for the union of all historical references. Different hashes of the same evidence ID are distinct. Digest verifies internal consistency, not authenticity. Input must be from the same consistent DB snapshot; the validator itself does not obtain locks, parse a ZIP/JSON or enforce aggregate byte budgets. A production importer must strictly parse untrusted archives, independently validate all metadata, enforce size limits and normalize errors. Exceptions may include underlying validation failures internally; caller must not disclose them to unauthorized users.

Open architectural gates before a safe archive: versioned format and manifest under a new profile; exact historical evidence bytes and metadata (old bytes may no longer exist, so export must fail closed); source authorization including historical sources; per-case snapshot synchronization across database and evidence blobs; preserved immutable actor/history and request digests with old request IDs tombstoned under a new restoration generation; no rewrite of original history; staging + crash-safe atomic publish/recovery across filesystem and database, destination-only restore, and concurrency/idempotency tests; multi-issue/hypothesis >50-event tests, security/zip/resource limits, rollback at every failure point, duplicate-key/unknown version rejection; restore/re-export and independent integration/browser acceptance. Existing legacy and working-record export refusal remains mandatory until all gates pass. Explicitly no assertion that this prototype solves atomic restoration, identity, legal evidentiary authenticity or unrestricted export.

Additional work: `archive_candidate.py` is a bounded JSON research preflight (not .mcase), and `RESTORE-CONTRACT.md` sets out a proposed content-addressed, staged, fail-closed whole-case restore and generation-separated replay policy. These are not integrated into export/import. Descriptors in the prototype are deliberately minimal and cannot prove historical metadata completeness. Original byte registration may be hash-only, making even a current full-byte archive impossible. Do not equate a successful preflight with a valid or complete archive.

Independent review corrections: the preflight now rejects unknown role labels, unknown fields in its intentionally minimal two-field reference descriptor, and repeated request IDs even across different operators/roles. IQ-1A currently permits that last case, so this conservative research profile rejects some otherwise valid existing histories; it never discards or rewrites them. These restrictions do not prove actors were authorized, validate complete historical evidence metadata, or implement tombstones/generation separation. The two-field descriptor is not sufficient for production export. An independent review and a real complete schema and restore implementation remain mandatory.

## Reproduce research tests

From the repository root, using existing project Python dependencies (no installation required):

```sh
PYTHONPATH=service:research/iq-archive-proposal python -m pytest -q research/iq-archive-proposal/test_validate.py research/iq-archive-proposal/test_archive_candidate.py
```

The local author run reports 30 passing synthetic tests. Independent review previously reran 30 tests after follow-up changes; no claim of complete integration, CI or browser acceptance is made.
