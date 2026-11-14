"""Independent current-policy routing and real SQLite final-access reservation checks."""
import base64
import json
import sqlite3
import pytest
from tests.test_evidence_intake_w42 import local, CASE
from tests.conftest import H
from mcis_service.db import get_doc, put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.evidence.models import EvidenceRow, CustodyEventRow
from mcis_service.audit.models import AuditEventRow
from mcis_service.redaction.policy import default_policy
from mcis_service.evidence import service


def url(case=CASE): return f'/api/v1/cases/{case}'


def register(client,case,raw,restricted=True):
    r=client.post(url(case)+'/evidence',headers=H('LeadInvestigator'),json={
        'title':'Independent synthetic','source':'Synthetic','extractedBy':'Independent',
        'extractedUtc':'2026-01-01T00:00:00Z','relativePath':'evidence/same-name.bin',
        'confidentiality':'Restricted' if restricted else 'Normal','category':'Other',
        'contentBase64':base64.b64encode(raw).decode()})
    assert r.status_code==201,r.text
    return r.json()


def hide(client,case):
    policy=default_policy()
    next(rule for rule in policy['fieldRules'] if rule['field']=='evidence.restricted')['appliesTo'].append('Investigator')
    assert client.put(url(case)+'/access-policy',headers=H('LeadInvestigator'),json=policy).status_code==200


def counts(app):
    with app.state.db.session() as s:
        return s.query(AuditEventRow).count(),s.query(CustodyEventRow).count()


@pytest.mark.parametrize('forge_binding',[False,True])
def test_target_case_policy_not_same_id_or_embedded_case(local,forge_binding):
    c,app=local;other=CASE+'-SECOND';a=b'first case independent';b=b'second case independent'
    with app.state.db.session() as s:
        doc=get_doc(s,CaseRow,CASE,CASE);put_doc(s,CaseRow,other,other,{**doc,'caseId':other})
    first=register(c,CASE,a);second=register(c,other,b)
    assert first['evidenceId']==second['evidenceId']=='EV-001'
    hide(c,CASE)
    if forge_binding:
        # Simulated inconsistent trusted-store metadata must not select other case's policy.
        with app.state.db.session() as s:put_doc(s,EvidenceRow,CASE,'EV-001',{**first,'caseId':other})
    before=counts(app)
    denied=c.get(url()+'/evidence/EV-001/content',headers=H())
    assert denied.status_code==403 and 'content-disposition' not in denied.headers and counts(app)==before
    allowed=c.get(url(other)+'/evidence/EV-001/content',headers=H())
    assert allowed.status_code==200 and allowed.content==b and allowed.content!=a


def test_remove_rule_does_not_hide_normal_item(local):
    c,app=local;raw=b'normal independent';item=register(c,CASE,raw,restricted=False);hide(c,CASE)
    r=c.get(url()+'/evidence/'+item['evidenceId']+'/content',headers=H())
    assert r.status_code==200 and r.content==raw


def test_reserved_until_actual_access_append_then_next_read_denied(local,monkeypatch):
    c,app=local;raw=b'final access boundary';register(c,CASE,raw)
    original=service.append_custody;checked=[]
    def append(session,*args,**kwargs):
        if kwargs.get('kind')=='Access':
            assert session.connection().connection.driver_connection.in_transaction
            writer=sqlite3.connect(app.state.settings.data_dir/'test.db',timeout=.02)
            try:
                with pytest.raises(sqlite3.OperationalError) as error:writer.execute('BEGIN IMMEDIATE')
                assert error.value.sqlite_errorcode==sqlite3.SQLITE_BUSY
                checked.append(True)
            finally:writer.close()
        return original(session,*args,**kwargs)
    monkeypatch.setattr(service,'append_custody',append)
    r=c.get(url()+'/evidence/EV-001/content',headers=H())
    assert r.status_code==200 and r.content==raw and checked==[True]
    hide(c,CASE);before=counts(app)
    assert c.get(url()+'/evidence/EV-001/content',headers=H()).status_code==403
    assert counts(app)==before and checked==[True]
