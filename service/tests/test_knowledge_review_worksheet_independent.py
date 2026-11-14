"""Independent synthetic safety tests; no LLM evaluation."""
import copy
import importlib.util
import json
import socket
from pathlib import Path
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session
from mcis_service.knowledge.router import digest

spec = importlib.util.spec_from_file_location('mcis_service.knowledge.independent_worksheet', Path(__file__).parents[1] / 'mcis_service/knowledge/review_worksheet.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def payload():
    c = dict(kind='Method', title='fixture', summary='synthetic', body='fixture only', tags=['test'], applicability='protocol only', source=dict(type='Synthetic', title='fixture', locator='p1', excerpt='fixture', rightsNote='test'))
    return dict(content=c, expectedDigest=digest(c))


@pytest.mark.parametrize('key', ['cardId', 'role', 'operator', 'db', 'sourceVerified', 'rightsVerified', 'releaseApproved'])
def test_cannot_supply_access_or_approval_controls(key):
    p = payload()
    p[key] = 'anything'
    with pytest.raises(HTTPException) as e:
        m.build(p)
    assert e.value.status_code == 422


def test_no_database_or_network_access(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('external access forbidden')
    monkeypatch.setattr(Session, 'execute', forbidden)
    monkeypatch.setattr(Session, 'get', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    p = payload()
    p['content']['source'].update(type='Public', url='https://example.invalid/source')
    p['expectedDigest'] = digest(p['content'])
    r = m.build(p)
    assert not r['approvalGranted'] and not r['persisted']
    assert r['sourceClassification'] == 'Public'


def test_html_remains_plain_json_not_safe_html():
    p = payload()
    attack = '<img src=x onerror="alert(1)"><script>notExecutableHere()</script>'
    p['content']['body'] = attack
    p['content']['source']['excerpt'] = attack
    p['expectedDigest'] = digest(p['content'])
    r = m.build(p)
    assert r['content']['body'] == attack
    assert json.loads(json.dumps(r))['content']['source']['excerpt'] == attack
    assert r['distribution'] == 'internal_review_only'
    assert all(c['status'] == 'pending' for c in r['checks'])


def test_fresh_pending_objects_and_deep_copies():
    p = payload()
    before = copy.deepcopy(p)
    first = m.build(p)
    first['checks'][0]['status'] = 'approved'
    first['checks'][0]['contentPaths'].append('evil')
    first['requiredReleaseApprovals'][0]['status'] = 'approved'
    first['content']['tags'].append('injected')
    second = m.build(p)
    assert p == before
    assert all(c['status'] == 'pending' for c in second['checks'])
    assert all(c['status'] == 'pending' for c in second['requiredReleaseApprovals'])
    assert 'evil' not in second['checks'][0]['contentPaths']
    assert len({c['id'] for c in second['checks']}) == 6
    assert {a['field'] for a in second['requiredReleaseApprovals']} == {'sourceVerified','rightsVerified','releaseApproved'}


@pytest.mark.parametrize('field', ['title', 'excerpt', 'locator', 'rightsNote'])
def test_missing_source_field_never_generates_worksheet(field):
    p = payload()
    del p['content']['source'][field]
    p['expectedDigest'] = digest(p['content'])
    with pytest.raises(HTTPException) as e:
        m.build(p)
    assert e.value.status_code == 422


def test_rights_change_requires_new_version():
    p = payload()
    p['content']['source']['rightsNote'] = 'changed'
    with pytest.raises(HTTPException) as e:
        m.build(p)
    assert e.value.status_code == 409


@pytest.mark.parametrize('value', [float('nan'), '\ud800', 'x' * 40000])
def test_bad_json_or_budget_rejected(value):
    p = payload()
    p['content']['body'] = value
    with pytest.raises(HTTPException) as e:
        m.build(p)
    assert e.value.status_code == 422


def test_export_escapes_script_terminator_and_roundtrips():
    p = payload()
    raw = '</script><script>alert("&")</script>中文\u2028'
    p['content']['body'] = raw
    p['expectedDigest'] = digest(p['content'])
    before = copy.deepcopy(p)
    out = m.export_json(p)
    assert all(c not in out for c in '<>&')
    assert out.isascii()
    assert json.loads(out)['content']['body'] == raw
    assert p == before
    assert json.loads(out)['approvalGranted'] is False


def test_export_stale_digest_also_fails():
    p = payload()
    p['content']['summary'] += ' changed'
    with pytest.raises(HTTPException) as e:
        m.export_json(p)
    assert e.value.status_code == 409
