# Independent review — combined content visibility and strict Base64

2026-11-14. Isolated /workspace/mcis-content-base64-integration based on
099185719d01e31e440b3473310f30a3aa74157a. Local combination of f3957e3 and70f7067 deltas;
no integration commit/push/merge/deployment by reviewer. No product edits by reviewer.

## Actual independent run

From service/:

```sh
MCIS_FIELD_RULE_OUTPUT=/workspace/mcis-content-base64-integration/tests_acceptance/content-base64-integration-independent/resolved-get.jsonl \
.venv/bin/python -m pytest -q --import-mode=importlib \
 ../tests_acceptance/content-visibility-independent/test_original_blocker.py \
 ../tests_acceptance/content-visibility-independent/test_additional.py \
 ../tests_acceptance/legacy-evidence-base64/test_independent.py \
 tests/test_content_base64_integration.py
```

**23 passed in5.16s**, no skipped cases. This reruns21 previously independently authored
cases plus2 new implementation combination cases; it does not claim23 newly designed
independent tests. Actual output: tests_acceptance/content-base64-integration-independent/results.txt.
GET source/restore JSON evidence: resolved-get.jsonl. Frozen router hash verifies OK:
b544f57ffe0b1936feafcdbc510d730eafd458887f15970c569bbfa7180c32e5.

## Composition / behavior inspection

Actual product diff against0991857 changes only evidence/router.py:
- imports binascii, strict Base64 decode(validate=True), canonical encode comparison,
  bounded generic422 INVALID_BASE64 before filesystem/evidence/custody/audit writes;
- after GET loads the item, existing filter_evidence on current target-case policy rejects
  hidden Restricted evidence403 before original-file read and Access event.

Both changes coexist. Existing authorization-before-decoding, GET WRITE_LOCK/BEGIN,
descriptor-safe read, recorded digest verification and container permissions remain intact.
No checksum-proposal enforcement, low-lock redesign or unrelated product change was inferred.

Test evidence:
- Prior source/restore Remove failures now both return403 with no payload/no new Access;
  current policy is preserved through real export/verify/import. Actual module path confirms
  the combined tree executed, not a standalone feature tree.
- Same evidence ID across cases with different bytes remains target-policy scoped; embedded
  case corruption cannot redirect permission to the other case. Normal evidence stays allowed.
- Actual second SQLite writer is blocked at Access append; committed later policy revoke
  makes the next read deny without Access. No shortened writer-lock interval introduced.
- Invalid canonical encoding variants leave existing file tree and all rows unchanged;
  existing valid file cannot be overwritten. Empty, nonUTF8 and2MiB+1 content round-trip exactly.
- Actual127.0.0.1 TCP HTTP test verifies422 invalid encoding then201 empty file; temporary
  uvicorn thread and socket shut down. Remaining requests use ASGI HTTP and real temporary
  SQLite/files, not mocked encoders/storage or production SSO.
- New combined workflows: invalid request has no effect; valid empty/binary upload succeeds;
  policy Remove blocks GET/export; Lead backup restores to a new DB with policy still denying
  Investigator, legal Lead bytes intact and audit/custody chains valid.

## Bounded verdict and retained limitations

No new blocker observed in this23-case focused combined run. It does not establish a fully
green product regression or grant release/merge/deployment permission. Coordinator's broader
suite was still running when this independent report was written. Historical baseline is
reported as5 failures and2 .NET-dependent skips; reviewer did not independently rerun that
wide suite. Preserve its actual final result/log separately; do not replace it with23 passed.

Caller roles are unverified request headers, not production authenticated identity. Current
policy consistency is not source authenticity. Source revocation after creation of an offline
backup does not propagate to a separate restored store.

Full file reads still hold the writer transaction; latency/contention costs are unchanged.
Request JSON and file bytes remain buffered in memory, with no new aggregate memory limit.
Finite size tests do not prove arbitrarily large-file behavior.

When contentBase64 and sha256 are both provided, the supplied sha256 is still ignored and
actual decoded-byte hash is recorded. Independent tests explicitly retain this old behavior;
expected-checksum comparison is only a proposal, NOT implemented by this combination.
Metadata-only digest declarations still do not prove observed original bytes.

No independent browser/.NET/full-system/production-identity/platform/performance acceptance
was performed. Old failure reports and frozen standalone records remain historical evidence;
this report applies only to the inspected local combined router hash above.
