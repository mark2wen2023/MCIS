# Independent acceptance — legacy dual-field expected checksum

2026-11-14. Isolated /workspace/mcis-evidence-checksum, base1759643.
Reviewer changed only independent tests and this report; no product edits, commits, push,
merge or deployment. Router and OpenAPI frozen hashes verify OK after tests.

## Executed checks

From service/:

```sh
.venv/bin/python -m pytest -q --import-mode=importlib \
 ../tests_acceptance/legacy-evidence-checksum-independent/test_independent.py \
 tests/test_legacy_evidence_checksum.py
```

**40 passed in5.72s**, no skipped cases:12 independently authored tests plus28 implementation
cases. Actual output: tests_acceptance/legacy-evidence-checksum-independent/results.txt.

One independent case uses a temporary uvicorn listener on127.0.0.1 and actual http.client
TCP requests; malformed Base64 is diagnosed before checksum, valid-schema Public request
is denied before checksum details, empty-content mismatch returns422 with zero writes,
and uppercase matching empty checksum registers201. Listener/thread are stopped afterward.
Other cases use ASGI HTTP with real temporary SQLite and real file contents, no mock decoder,
writer or database. No deployment, external API/model, SSO or real accident data is involved.

Independent additions also demonstrate:
- Mixed-case ASCII SHA matches empty, nonUTF8 binary and2MiB+1 decoded bytes; recorded SHA
  normalizes to lowercase and exact bytes/GET hash remain correct.
- Expected checksum is compared with INCOMING decoded bytes, not an existing pathname's
  file digest. A mismatching request targeting an existing file yields422 and zero mutation.
  A matching new-content checksum still cannot overwrite that old file:409 BLOB_EXISTS.
- Lone-surrogate SHA and trailing CR are rejected as INVALID_SHA256. Nonstring checksum
  types retain framework422; schema validation may precede handler authorization, unlike
  valid-schema request diagnostics. All tested failures leave rows and file tree unchanged.
- SHA-only request remains metadata-only: no fabricated file, later content404. Implementation
  rerun additionally covers content-only/null-SHA/null-content, empty SHA, lengths, nonASCII
  hex, mismatch and invalid Base64 before checksum.
- Parsed OpenAPI is3.1.0; contentBase64/sha256 nullable types are valid3.1 arrays. The newly
  advertised422 Problem reference resolves to the existing response definition and its
  description explicitly identifies the new dual-field contract.

## Source/contract review

Checksum validation occurs immediately after strict canonical Base64 decode and before
path selection/write_blob/persistent evidence/custody/audit changes. re.fullmatch with
[0-9A-Fa-f]{64} rejects trailing newline, Unicode lookalikes, trim and partial-match cases.
Comparison uses normalized supplied SHA against decoded immutable bytes. Current digest
creation, GET policy gate, safe reads and byte verification are not removed or weakened.

This is a NEW contract. Previous dual-field callers were allowed to supply ignored hashes;
old placeholder/mismatch/malformed callers now intentionally fail422. No silent fallback
restores ignored-mismatch behavior. Prior independent binary test was explicitly renamed
and changed to supply matching SHA, with a new-contract comment; mismatch now has dedicated
zero-write rejection tests. Historical prior acceptance reports remain accurate for their
old revisions and must not be presented as current ignored-checksum behavior.

Source inspection confirms the named EvidenceIntakePanel and tools/stage-demo/run.py call
new evidence-intakes APIs; this is not a full external-client audit or production telemetry.
Unknown external legacy callers may rely on old precedence and need contract communication.
Content-only, matching dual-input and SHA-only paths retain the documented intended semantics;
not every historical caller is backward compatible with this deliberate validation change.

## Bounded conclusion

No blocking issue found within this expected-checksum change. Bad or unequal expected SHA
returns422 before writes; exact match preserves bytes and existing file protection. No
full-suite, browser/.NET, performance or production identity acceptance is implied by40
focused passes. Broader implementer results remain separate evidence.

Checksum consistency does not establish source authenticity, signer identity or acquisition
provenance. Metadata-only SHA remains declared rather than verified content. Role headers
are not production authentication. Full GET writer-lock duration, JSON/file memory buffering
and absence of new aggregate size limits remain unchanged. No push/merge/deployment approval
is implied by this independent verdict.
