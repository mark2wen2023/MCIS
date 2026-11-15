# Offline ZIP v2: limited developer validation

Base1cc8d2932f825410eea04fd7ad54015a0b9f0faa. Added independent research envelope
based on a812d38 conflict_envelope.py, using already reviewed v2 member parser.
No product runtime/parser/permissions/allowlist change; no active receipt importer.

Command from service/:

    PYTHONPATH=.. .venv/bin/pytest -q tests/test_conflict_archive_envelope_v2.py tests/test_conflict_archive_receipts_v2.py tests/test_conflict_restore_current_compatibility.py

Final49 passed in9.02s:27new envelope +21member +1old-schema diagnostic. Earlier25
passed before unused-receipt and legacy-unknown coverage; final run supersedes it.
All developer-side synthetic tests, not independent acceptance.

Fixture: actual ordinary APIs register synthetic raw/source.txt bytes and conflict,
issue/consume a registry receipt, retain another unused receipt; retrieve synthetic
rows and raw audit/custody into explicit in-memory ZIP members. No private/original
materials read, network OCR/model or restricted security/ECFC tests. Filesystem writes
are ordinary synthetic fixture creation in temporary dirs; envelope accepts only bytes.

Validated v1 legacy creation-history ZIP and v2 full receipts ZIP, exact unpacked
member preservation and re-envelope/reparse (not DB restoration). Manifest omissions,
duplicates, case/format/version/role/size/digest mismatch; unknown/mixed profiles;
wrong evidence bytes/missing registry or audit/custody; mirror mismatch; missing or
active receipt; unsupported content; unknown legacy history remain refused/preserved
as applicable. Production parse_package rejects both experimental profile versions.
No authorization or restored active receipt created by inspection/build.

Limits: no product restore, continued-work roundtrip, file publication/readiness,
import receipt/source lineage DB mapping, failure rollback or crash recovery. No
production supported1.0-1.4 full regression beyond unchanged product rejection of
these experiment tags. No browser/real identity or genuine original verification.
Envelope is supplied-snapshot consistency, not proof that an external submitter gave
all authentic history. Replacement-original histories/default-policy restrictions
inherited, not expanded. Product remains blocked until complete restore and independent
review. No merge/deploy.
