#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/../../service"
.venv/bin/python -m pytest -q -rs \
 tests/test_safe_read_budget_preflight.py tests/test_archive_safe_read.py \
 tests/test_archive_read_independent.py tests/test_intake_descriptor_read.py \
 tests/test_intake_descriptor_independent.py tests/test_legacy_safe_delivery.py \
 tests/test_recorded_digest_delivery.py tests/test_content_visibility.py \
 tests/test_package_export_policy.py tests/test_policy_write_busy.py \
 tests/test_evidence_intake_w42.py tests/test_report_bundle_attachment_access.py
