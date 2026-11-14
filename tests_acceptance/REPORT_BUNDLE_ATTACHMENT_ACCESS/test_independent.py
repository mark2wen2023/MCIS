"""Independent HTTP/policy/SQLite checks; synthetic case and opaque ZIP fixtures."""
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'service'))
from tests.test_report_output import origin, H, CID
from tests.test_report_bundle_attachment_access import register, download, access_count, INVESTIGATOR
from mcis_service.db import put_doc
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy, CATEGORIES
from mcis_service.report_output import attachment_access


def policy(c, change):
    p = default_policy()
    change(p)
    with c.app.state.db.session() as s:
        put_doc(s, AccessPolicyRow, CID, 'policy', p)


@pytest.mark.parametrize('route', ['intake','legacy'])
@pytest.mark.parametrize('category', CATEGORIES)
def test_every_permission_required(origin,route,category):
    c,_,_=origin
    receipt=register(c,b'PK truncated synthetic zip')
    policy(c,lambda p:p['matrix']['LeadInvestigator'].__setitem__(category,'Deny'))
    before=access_count(c)
    response=download(c,receipt,route,H)
    assert response.status_code==403
    assert response.headers['cache-control']=='no-store'
    assert access_count(c)==before
    assert b'PK truncated' not in response.content


@pytest.mark.parametrize('route',['intake','legacy'])
def test_field_rule_blocks_otherwise_readable_investigator(origin,route):
    c,_,_=origin
    receipt=register(c,b'PK synthetic')
    policy(c,lambda p:p['matrix']['Investigator'].update({k:'ReadOnly' for k in CATEGORIES}))
    before=access_count(c)
    assert download(c,receipt,route,INVESTIGATOR).status_code==403
    assert access_count(c)==before
    def allow(p):
        p['matrix']['Investigator']={k:'ReadOnly' for k in CATEGORIES}
        p['fieldRules']=[]
    policy(c,allow)
    result=download(c,receipt,route,INVESTIGATOR)
    assert result.status_code==200 and result.content==b'PK synthetic'
    assert access_count(c)==before+1


@pytest.mark.parametrize('route',['intake','legacy'])
def test_policy_write_reserved_during_container_check(origin,route,monkeypatch):
    c,_,_=origin
    receipt=register(c,b'PK transaction fixture')
    original=attachment_access.protect_container
    observed=[]
    def guarded(session,case_id,role,raw):
        dbpath=session.get_bind().url.database
        # Separate physical SQLite connection simulates another process, bypassing Python WRITE_LOCK.
        with sqlite3.connect(dbpath,timeout=0) as other:
            with pytest.raises(sqlite3.OperationalError,match='locked'):
                other.execute('BEGIN IMMEDIATE')
        observed.append(True)
        return original(session,case_id,role,raw)
    monkeypatch.setattr(attachment_access,'protect_container',guarded)
    assert download(c,receipt,route,H).status_code==200
    assert observed==[True]


@pytest.mark.parametrize('route',['intake','legacy'])
def test_no_access_on_gate_exception(origin,route,monkeypatch):
    c,_,_=origin
    receipt=register(c,b'PK synthetic')
    before=access_count(c)
    def broken(*a,**kw):
        raise RuntimeError('SYNTHETIC_PRIVATE_FAILURE')
    monkeypatch.setattr(attachment_access,'protect_container',broken)
    result=download(c,receipt,route,H)
    assert result.status_code==500
    assert b'SYNTHETIC_PRIVATE_FAILURE' not in result.content
    assert access_count(c)==before
