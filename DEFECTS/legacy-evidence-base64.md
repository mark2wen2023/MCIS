# Independent acceptance — legacy evidence strict Base64

2026-11-14. Isolated /workspace/mcis-evidence-base64, base0991857.
Reviewer added only tests and review records. No product edits, commits, push, merge or
deployment. Frozen evidence/router.py hash verifies OK after all tests.

## Actual execution

From service/:

```sh
.venv/bin/python -m pytest -q --import-mode=importlib \
 ../tests_acceptance/legacy-evidence-base64/test_independent.py \
 tests/test_legacy_evidence_base64.py
```

Final **46 passed in5.73s**, no skips:15 independent cases and31 implementation cases.
Final-results.txt is the authoritative result; earlier45-case run predates addition of
real loopback HTTP verification and must not be added to the count.

One independent test starts uvicorn on an ephemeral127.0.0.1 TCP listener and sends actual
HTTP via http.client. Noncanonical pad bits return422 with zero mutation; following empty
content request returns201 with SHA256(empty). Server thread shuts down and socket closes.
This is a bounded local test, not deployment. Remaining cases use explicit ASGI HTTP
transport and actual temporary SQLite/blob files, with no mocked database/decoder/writer.

## Independently checked boundaries

- Existing file/tree and all evidence/custody/audit row counts stay identical for invalid
  pad bits, concatenated encodings, CRLF/NUL, emoji, lone surrogate and excess padding.
  Lone surrogate is sent as valid escaped JSON; it returns422 rather than encoder/server500.
- Valid duplicate-file registration still returns409 BLOB_EXISTS and cannot overwrite old
  bytes or add partial rows. Invalid encoding returns422 before any filename/path write.
- Canonical empty bytes, nonUTF8 binary and2MiB+1 bytes store/retrieve exactly with computed
  SHA256. Implementation suite adds0/1/2/3/255/64KiB/1MiB/1MiB+1 cases. These finite tests
  support compatibility, not a universal maximum-file or memory guarantee.
- Unauthorized role receives403 before Base64 diagnostics; invalid encoding plus unsafe
  relative path has no filesystem or DB mutation. Input is not echoed in INVALID_BASE64.
- Missing/null content digest-only and nonstring schema cases pass in rerun implementation
  tests. Metadata-only registration remains a declaration, not verified source content.

## Explicit double-field compatibility boundary

Three independent valid-content tests also send sha256='0'*64. Registration succeeds and
records the actual decoded-byte digest. This demonstrates the legacy supplied-sha256 field
is STILL IGNORED when contentBase64 is present; this patch has not implemented expected
checksum matching. Those assertions preserve current behavior and do not claim a mismatch
was securely checked. The separate contracts/legacy-evidence-expected-checksum-proposal.md
is evaluation only, not part of frozen implementation.

Proposed future double-field validation would change behavior for stale/placeholder hashes
and needs its own contract/tests. It must not be inferred from strict Base64 decoding or
from the returned actual-byte hash. Neither current nor proposed behavior authenticates
source, signer, operator identity or evidence origin.

## Verdict / retained limitations

No blocker found in this narrowly scoped strict canonical Base64 patch. Strict decoder plus
canonical re-encode closes ignored-junk/padding/pad-bit acceptance; error classification is
before write_blob or persistent evidence/custody/audit writes. Existing authorization and
raw file sizes/empty-file support stay intact. JSON request buffering and aggregate memory
are unchanged; no new cap or bounded-memory claim is made.

The known evidence content GET ignoring evidence.restricted Remove is NOT repaired here and
remains a separate security blocker. Existing local header roles are not production SSO.
No .NET/browser/full-system acceptance is implied; implementer's broader63passed/1.NETskip
result is separate evidence, not an independent full-suite rerun. This acceptance does not
authorize push/merge/deploy or overall security release.
