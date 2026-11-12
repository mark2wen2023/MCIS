"""Opt-in W16.2 selected old business assertions, synthetic seed=False only.

Reuses original test function bodies/parametrizations without deleting assertions.
Old implicit Investigator success cases execute under Lead; security assertions
for default Investigator are in test_reports_w162_access. Public-case tests and
source-backed original-report tests are deliberately NOT selected.
"""
from types import SimpleNamespace
import pytest
from mcis_service.main import create_app
from mcis_service.seed.lily_mary import seed
from .conftest import make_settings, H as original_H
from . import test_reports_w16 as http_tests
from . import test_reports_w16_direct as direct_tests
from . import test_reports_w16_export as export_tests
from . import test_reports_w161_snapshot as snapshot_tests

@pytest.fixture
def app(tmp_path):
    app = create_app(make_settings(tmp_path, seed=False))
    with app.state.db.session() as s: seed(s, app.state.settings.blob_dir)
    return app

@pytest.fixture
def ctx(app):
    return SimpleNamespace(db=app.state.db, role='LeadInvestigator', operator='报告直调员',
                           settings=app.state.settings, request=SimpleNamespace(app=app))

@pytest.fixture(autouse=True)
def qualifying_old_success_role(monkeypatch):
    def H(role='LeadInvestigator', operator=None): return original_H(role, operator)
    monkeypatch.setattr(http_tests, 'H', H)

# Preserve old test objects, including pytest parametrization and original assertions.
HTTP = {
 'test_templates_languages_draft_contract', 'test_confirm_dismiss_reject_every_new_value_even_null',
 'test_reason_required', 'test_no_change_and_missing_text',
 'test_audit_reason_full_original_new_operator_and_regenerate',
 'test_sentence_review_keeps_section_and_sentence_generated_text',
 'test_colreg_draft_entry_and_templates_glossary', 'test_validation_unknown_and_only_loopback_unchanged',
 'test_export_stream_hash_status_and_audit', 'test_gisis_api_missing_validation_exports_and_audit',
}
DIRECT = {
 'test_direct_all_templates_languages_and_schema', 'test_direct_confirm_dismiss_reject_new_fields_even_null',
 'test_direct_reason_required', 'test_direct_review_originals_full_reason_operator_and_regeneration',
 'test_direct_modify_same_and_missing_text_and_sentence_originals',
 'test_direct_malformed_sentence_identifier_is_422', 'test_direct_not_found_errors',
 'test_direct_colreg_draft_has_sources_and_audit', 'test_direct_colreg_draft_regeneration_keeps_chapter_scope',
 'test_direct_report_export_headers_hash_and_audit', 'test_direct_gisis_missing_validation_and_download_audit',
 'test_direct_validated_gisis_export_temporary_values_do_not_change_case',
 'test_direct_review_audit_failure_rolls_back_report_and_snapshots',
 'test_direct_external_roles_cannot_read_restricted_report_content',
 'test_direct_generate_audit_failure_rolls_back_new_report', 'test_direct_w16_openapi_routes_have_no_drift',
 'test_direct_colreg_draft_data_sources_match_chapter_scope',
}
SNAPSHOT = {'test_build_line_without_snapshot_ref_is_byte_identical',
 'test_snapshot_ref_round_trip_retains_full_reason_values_and_chain',
 'test_snapshot_missing_is_404_and_case_scoped', 'test_snapshot_restricted_roles_are_403',
 'test_to_doc_only_adds_snapshot_ref_when_line_contains_key',
 'test_legacy_report_snapshot_gets_reference_without_rewriting_audit_line'}
for module, names in [(http_tests, HTTP), (direct_tests, DIRECT), (snapshot_tests, SNAPSHOT)]:
    for name in names: globals()[name] = getattr(module, name)
# Pure exporter tests build inline synthetic documents; no real report files.
for name in dir(export_tests):
    if name.startswith('test_'): globals()[name] = getattr(export_tests, name)
