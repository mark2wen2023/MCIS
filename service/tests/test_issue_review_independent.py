"""Independent synthetic security/consistency review; no models or live evidence."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from sqlalchemy import select
from tests.test_investigation_issues import c,new,hypo,begin,verify,event,H,BASE,CID
from mcis_service.investigation_issues import router as mod
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from mcis_service.evidence.models import EvidenceRow
from mcis_service.db import put_doc

def read(c,i):return c.get(BASE+'/'+i+'/review',headers=H)

def test_review_keeps_permission_revocation_serialized(c,monkeypatch):
    i,_=new(c);entered=Event();release=Event();committed=Event()
    original=mod.view
    def pause(*args):
        result=original(*args);entered.set()
        assert release.wait(5)
        return result
    monkeypatch.setattr(mod,'view',pause)
    def revoke():
        with c.app.state.db.session() as s:
            p=default_policy();p['matrix']['LeadInvestigator']['report_draft']='Deny'
            put_doc(s,AccessPolicyRow,CID,'policy',p)
        committed.set()
    with ThreadPoolExecutor(2) as pool:
        future=pool.submit(read,c,i);assert entered.wait(5)
        writer=pool.submit(revoke)
        early=committed.wait(.3)
        release.set();response=future.result(5);writer.result(5)
    assert not early, 'policy revoke committed while response used old allowed policy'
    assert response.status_code==200
    assert read(c,i).status_code==403

def test_review_allows_readonly_content_role(c):
    i,_=new(c)
    with c.app.state.db.session() as s:
        p=default_policy();p['matrix']['LeadInvestigator']['report_draft']='ReadOnly'
        put_doc(s,AccessPolicyRow,CID,'policy',p)
    assert read(c,i).status_code==200

def test_historical_only_removed_source_fails_closed(c):
    i,_=new(c);h=hypo(c,i,sources=[{'evidenceId':'EV-001','sha256':'a'*64}])
    hypo(c,i,h,1,[])
    with c.app.state.db.session() as s:s.delete(s.scalar(select(EvidenceRow)))
    r=read(c,i);assert r.status_code==403;assert r.headers['cache-control']=='no-store'

def test_reversed_reference_order_still_joins(c):
    with c.app.state.db.session() as s:
        put_doc(s,EvidenceRow,CID,'EV-002',{'caseId':CID,'evidenceId':'EV-002','title':'Synthetic','sha256':'b'*64,'confidentiality':'Normal'})
    i,_=new(c);h=hypo(c,i);begin(c,i)
    refs=[{'evidenceId':'EV-002','sha256':'b'*64},{'evidenceId':'EV-001','sha256':'a'*64}]
    event(c,i,'RecordVerification',{'hypothesisId':h,'hypothesisVersion':1,'activity':'  a\n b  '.strip(),'result':'not determined','outcome':'Inconclusive','sourceRefs':refs})
    r=read(c,i);assert r.status_code==200
    assert r.json()['rows'][0]['verificationEvent']['payload']['sourceRefs']==refs

def test_does_not_normalize_recorded_text(c):
    i,_=new(c);h=hypo(c,i);begin(c,i)
    text='约 3.4 海里\n另一时刻约 3.5 海里；不能直接判矛盾。'
    event(c,i,'RecordVerification',{'hypothesisId':h,'hypothesisVersion':1,'activity':'synthetic text preservation','result':text,'outcome':'Inconclusive','sourceRefs':[]})
    assert read(c,i).json()['rows'][0]['verificationEvent']['payload']['result']==text
