#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/../../service"
.venv/bin/python -m pytest -q -rs --import-mode=importlib \
 tests/test_content_base64_integration.py tests/test_content_visibility.py \
 tests/test_package_policy_roundtrip.py tests/test_legacy_evidence_base64.py \
 tests/test_package_export_policy.py tests/test_main_safe_integration.py \
 tests/test_policy_write_busy.py tests/test_recorded_digest_delivery.py \
 tests/test_legacy_safe_delivery.py tests/test_intake_authorization_transaction.py \
 tests/test_intake_descriptor_read.py tests/test_intake_descriptor_independent.py \
 tests/test_archive_safe_read.py tests/test_archive_read_independent.py \
 tests/test_safe_read_delivery.py tests/test_restored_attachment_filename.py \
 tests/test_report_bundle_attachment_access.py tests/test_evidence_intake_w42.py \
 tests/test_evidence.py tests/test_working_record_archive.py tests/test_package.py \
 tests/test_archive_export_safety.py tests/test_package_zip_boundary.py \
 tests/test_report_output.py tests/test_contracts.py tests/test_interviews_redaction.py \
 tests/test_access_workbench.py \
 ../tests_acceptance/RESTORED_ATTACHMENT_FILENAME/test_independent.py \
 ../tests_acceptance/REPORT_BUNDLE_ATTACHMENT_ACCESS/test_independent.py \
 ../tests_acceptance/legacy-descriptor-read/test_independent.py \
 ../tests_acceptance/recorded-digest/test_independent.py \
 ../tests_acceptance/policy-write-busy/test_independent.py \
 ../tests_acceptance/package-export-policy/test_independent.py
