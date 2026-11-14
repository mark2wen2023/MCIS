# Legacy evidence Base64 — local isolated candidate

Base099185719d01e31e440b3473310f30a3aa74157a; local/legacy-evidence-base64 in
/workspace/mcis-evidence-base64. Only product change: evidence/router.py adds binascii and
strict decode/canonical re-encode comparison before any blob write. Invalid encoded text
returns422 INVALID_BASE64 without reflecting the input. No product GET permission changes.

Actual HTTP TestClient and isolated SQLite, synthetic input only. Baseline:18 failed,
13 passed in3.56s. Bad alphabet, junk, whitespace, invalid padding, unused pad bits and
malformed values reproduce prior permissive decode or unhandled500 behavior. In particular
!!!! registered empty bytes and could overwrite an existing synthetic path; assertions are
retained. New regression:63 passed,1 existing missing-.NET skip in9.41s:

    cd service
    .venv/bin/python -m pytest -q -rs tests/test_legacy_evidence_base64.py tests/test_evidence.py tests/test_package_export_policy.py

31 new tests cover rejected encodings with unchanged filesystem and evidence/custody/audit
counts; existing-file no overwrite; nonstrings; valid binary exact lengths0,1,2,3,255,64KiB,
1MiB,1MiB+1; recorded digest and actual content GET; metadata-only registration. Explicit
empty Base64 remains a zero-byte file. No arbitrary new size limit: this is not a memory
budget or maximum-upload acceptance test. Tests do not need real external API/model services.

Implementation hash frozen in logs/legacy-evidence-base64-impl-hashes-frozen.txt. No push,
merge or deployment. Independent review results are recorded separately when available.
No claim about authenticated identities, truthful sources or production SSO. The inherited
legacy content GET field-rule omission remains an independent blocking issue documented in
/workspace/mcis-package-roundtrip; this input repair must not be treated as fixing it.
Dual-field expected SHA behavior is a separate evaluated proposal, not implemented here.
The previous broader5 baseline failures/2.NET skips remain historical limits; this narrower
run does not claim that those were fixed or rerun in full.

Independent review:46 passed in5.73s (15 independently authored +31 implementation
cases; overlaps implementation count). Includes real localhost TCP HTTP for invalid pad
bits422/no writes and empty-file201, plus real SQLite/FS tests including2MiB+1, nonUTF8,
Unicode/lone surrogate rejection, authorization precedence and existing-file preservation.
Frozen product hash confirmed unchanged. Dual-input test confirms supplied checksum is
still ignored in this limited patch; proposal is not falsely presented as implemented.

Coordinator-reported independent review of base0991857 (not rerun by this follow-up):
70 focused passes and288 expanded passes across two runs; original5 baseline failures
independently reproduced. Spoofable role headers, long locks, memory and real authentication
remain unresolved. This Base64 candidate is not production readiness or authorization signoff.

Evidence-file note: independent review reused results.txt for its45-case preliminary run.
To retain a complete separate implementation log, the same broader command was rerun:
implementation-regression.txt records63 passed/1.NET skip in9.84s. Do not sum reruns.
