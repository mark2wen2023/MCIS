"""Offline wording regression only. No app, policy probe, or original file reads."""
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[2]


def test_contract_distinguishes_registry_gate_from_file_verification():
    text=(ROOT/'contracts/conflict-revisions-v1.md').read_text()
    for phrase in ('same-case evidence registration existence','visibility under the current policy',
        'Missing or policy-invisible evidence registrations fail closed',
        'does not open source files','detect missing/modified original files',
        'bytesVerified=false','does not certify source-file integrity'):
        assert phrase in text
    assert 'referenced originals fail closed' not in text


def test_implementation_report_does_not_promote_registry_checks():
    text=(ROOT/'research/trajectory/CONFLICT_REVISION_CAPTURE.md').read_text()
    for phrase in ('registration\n  existence and current policy visibility only',
        'Source files are not opened','bytesVerified=false remains false'):
        assert phrase in text
    assert 'Missing/inaccessible referenced originals refuse' not in text


def test_openapi_has_visible_explicit_scope_limit():
    spec=yaml.safe_load((ROOT/'contracts/openapi.yaml').read_text())
    description=spec['paths']['/api/v1/cases/{caseId}/conflicts/{conflictId}/revisions']['get']['description']
    for phrase in ('仅限同案登记存在及当前策略可见性','不读取原件',
        '不检测文件缺失或字节变化','bytesVerified=false'):
        assert phrase in description
