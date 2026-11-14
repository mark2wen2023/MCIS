"""Independent synthetic safety/protocol tests; no model quality claims."""
import copy
import importlib.util
import socket
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('independent_freshness', Path(__file__).parents[1] / 'mcis_service/knowledge/freshness.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


def payload():
    s = dict(type='Public', title='Synthetic fixture', locator='p1', excerpt='fixture only', rightsNote='test only', url='https://example.invalid/report')
    c = dict(source=s, privateMarker='DO_NOT_ECHO')
    return dict(profile=f.PROFILE, candidateContent=c, expectedContentDigest=f.digest(c), candidateSourceCapturedUtc='2026-11-14T08:00:00Z', observation=dict(status='provided', source=copy.deepcopy(s), capturedUtc='2026-11-14T09:00:00Z'))


@pytest.mark.parametrize('field', sorted(f.FIELDS))
@pytest.mark.parametrize('side', ['candidate', 'observation'])
def test_each_missing_required_public_source_field_fails_closed(field, side):
    p = payload()
    target = p['candidateContent']['source'] if side == 'candidate' else p['observation']['source']
    del target[field]
    p['expectedContentDigest'] = f.digest(p['candidateContent'])
    with pytest.raises(f.InvalidFreshness):
        f.preview(p)


def test_no_network_no_input_mutation_no_source_body_echo(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('network forbidden')
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    p = payload()
    before = copy.deepcopy(p)
    result = f.preview(p)
    assert p == before
    assert 'DO_NOT_ECHO' not in str(result)
    assert p['observation']['source']['url'] not in str(result)
    assert result['comparisonScope'] == 'exact_supplied_source_fields'
    for key in ('networkUsed', 'modelUsed', 'persisted', 'approvalChanged', 'captureTimesVerified', 'sourceCurrentnessVerified'):
        assert result[key] is False
    assert result['reviewRequired'] is True


def test_all_changed_fields_stable_sorted():
    p = payload()
    for key in ('title', 'excerpt', 'locator', 'rightsNote', 'url'):
        p['observation']['source'][key] += ' changed'
    result = f.preview(p)
    assert result['changedFields'] == ['excerpt', 'locator', 'rightsNote', 'title', 'url']
    assert result['recheckRequired'] is True


@pytest.mark.parametrize('key', ['profile', 'expectedContentDigest', 'candidateSourceCapturedUtc', 'observation', 'candidateContent'])
def test_missing_top_level_field_rejected(key):
    p = payload()
    del p[key]
    with pytest.raises(f.InvalidFreshness):
        f.preview(p)


@pytest.mark.parametrize('value', [float('nan'), float('inf'), {1, 2}, '\ud800'])
def test_non_json_candidate_content_rejected(value):
    p = payload()
    p['candidateContent']['extra'] = value
    with pytest.raises(f.InvalidFreshness):
        f.preview(p)


def test_budget_checked_before_digest_error():
    p = payload()
    p['candidateContent']['extra'] = 'x' * 32769
    with pytest.raises(f.InvalidFreshness, match='CONTENT_BUDGET'):
        f.preview(p)


def test_unavailable_no_timestamp_invention():
    p = payload()
    p['observation'] = {'status': 'unavailable'}
    result = f.preview(p)
    assert result['comparison'] == 'unavailable'
    assert result['observedSourceCapturedUtc'] is None
    assert result['observedSourceDigest'] is None
    assert result['recheckRequired'] is True


def test_older_snapshot_not_presented_as_verified_current():
    p = payload()
    p['observation']['capturedUtc'] = '2000-01-01T00:00:00Z'
    result = f.preview(p)
    assert result['comparison'] == 'unchanged_snapshot'
    assert result['observedSourceCapturedUtc'] == '2000-01-01T00:00:00Z'
    assert result['sourceCurrentnessVerified'] is False
    assert result['reviewRequired'] is True


def test_explicit_unknown_times_remain_unknown():
    p = payload()
    p['candidateSourceCapturedUtc'] = None
    p['observation']['capturedUtc'] = None
    result = f.preview(p)
    assert result['candidateSourceCapturedUtc'] is None
    assert result['observedSourceCapturedUtc'] is None
    assert result['comparison'] == 'unchanged_snapshot'
    assert result['sourceCurrentnessVerified'] is False
    assert result['captureTimesVerified'] is False
    assert result['reviewRequired'] is True
