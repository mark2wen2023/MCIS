# Main-only attachment access + restored filename candidate

Base main: `3aba2bf03e393909c611489ae573a887087637ac`.
Extracted exact parent-to-head deltas of PR64 `5d10b67db47e55b6352b559ec1d00ae61ede99c7` and PR61 `aad96d439d34d112cd07637fc341c06dbaf22978`, excluding their shared REQUESTS/ROADMAP additions. No PR56 ancestor commits imported. Existing contracts, tests and historical acceptance reports are retained; their prior results are not substituted for this candidate's validation.

Implementation: conservative ZIP full-content access gate on both live attachment read paths, within reserved transaction and before success audit; restored historical name is reconstructed from revalidated metadata/byte binding and RFC5987 encoded. No content rewriting, authenticated-author claim, source activation or automatic upload.

Additional combined test generates real PDF/DOCX report ZIPs for synthetic cases, explicitly registers each under a Unicode/emoji/percent filename, checks denial/no disclosure/no successful audit on both live paths, checks authorized bytes, then exports/imports twice and checks restored filename/hash/bytes, denied reads and inert historical receipt.

## Baseline and freeze caveat

The inherited PR64 freeze differs only for evidence_intake/router.py because main lacks PR56's shared descriptor-safe read helper, SafeReadUnavailable handling, intake incarnation allocation and commit-time reservation. Those are not silently imported. This candidate retains main's pre-existing intake registration/read behavior, while preserving the complete PR64 download-time reserved transaction and permission gate. It must not be described as providing PR56's stronger source-incarnation/safe-parent-descriptor guarantees. All PR61 frozen files and the other PR64 frozen files match their source freezes. Historical freeze files remain evidence of original branches; the new attachment-main-integration freeze is authoritative for this candidate.

## Limits

Role/operator headers are still caller-declared local identity. Production sessions/case membership and full route migration are not implemented. ZIP detection includes DOCX and arbitrary ZIPs but is not general DLP; transformed plain text/PDF is out of scope. Intake still has its existing8MiB limit. No new model call or claim of real-case/model acceptance.

Both the previous integration audit and this candidate's fresh sandbox-enabled Chromium probe failed before navigation (SUID helper/crashpad); no bypass is permitted. Node transport assertions do not prove native download or all platform filenames. No merge/deployment. The PR56 baseline TypeScript failures are absent on this main-based candidate; production build passes.

## Candidate validation

All Python commands use `PYTHONPATH=service:. service/.venv/bin/pytest --import-mode=importlib`.

- Source suites: service/tests/test_restored_attachment_filename.py, test_report_bundle_attachment_access.py and their two tests_acceptance suites: **77 passed**.
- Cross suites: test_attachment_main_integration.py, test_report_output.py, test_reports_w162_access.py, test_evidence_intake_w42.py, test_working_record_archive.py: **263 passed, 1 skipped, 1 failed**.
- Failure: test_working_record_archive.py::test_report_versions_full_review_gisis_and_hfacs_coexist raises HFACS_CORE_UNAVAILABLE503. Reproduced unchanged on a separate fresh main3aba checkout with the same environment: **1 failed**. No production/test code changed to hide it; .NET HFACS integration remains unverified.
- Skip: test_evidence_intake_w42.py::test_intake_csharp_custody_compatibility requires the existing .NET SDK. Not counted as pass.
- `npm ci` then `npm run build`: passed (large-chunk advisory only). Actual restored-filename transport/parser checks: **23 passed**, independently authored frontend assertions: **14 passed**, synthetic fetch.
- Frozen implementation is unchanged from the extracted deltas. The new cross test covers both PDF-containing and DOCX-containing real ZIPs, not model capability.
