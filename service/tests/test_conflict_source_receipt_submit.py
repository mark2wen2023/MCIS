"""Ordinary synthetic HTTP/SQLite registry receipts; no originals/security probes."""
from copy import deepcopy
from datetime import timedelta
import pytest
from sqlalchemy import select
from mcis_service.db import put_doc
from mcis_service.evidence.models import EvidenceRow
from mcis_service.evidence.service import append_custody
from mcis_service.timeline import source_receipts,revisions
from .test_working_record_archive import client_at,ROOT,CID,HEAD
from .test_conflict_archive_readiness import body
from .test_consultation_archive_readiness import state
from .conftest import H


def seed(c):
    with c.app.state.db.session() as s:
        for k in ('EV-A','EV-B'):put_doc(s,EvidenceRow,CID,k,{'caseId':CID,'evidenceId':k,'sha256':'a'*64,'confidentiality':'Normal'})
    v=body();v['a']['evidenceId']='EV-A';v['b']['evidenceId']='EV-B'
    assert c.post(ROOT+'/conflicts',headers=HEAD,json=v).status_code==201
    return v


def token(c):
    r=c.get(ROOT+'/conflicts:editable',headers=HEAD);assert r.status_code==200
    return r.json()[0]['version']


def prepare(c,v,sides=('a',)):
    v=deepcopy(v)
    for side in sides:v[side]['valueText']='Synthetic proposed '+side
    t=token(c)
    r=c.post(ROOT+'/conflicts/C-01/source-receipts',headers=HEAD,json={'expectedVersion':t,'observations':{x:v[x] for x in ('a','b')}})
    assert r.status_code==201,r.text
    receipt=r.json()
    assert receipt['bytesVerified'] is False and receipt['humanReadVerified'] is False
    return {**v,'expectedVersion':t,'sourceReceiptId':receipt['receiptId']},receipt


def change(c,key,before='a',after='b'):
    with c.app.state.db.session() as s:append_custody(s,case_id=CID,evidence_id=key,kind='Change',operator='Synthetic',role='LeadInvestigator',sha256=after*64,previous_sha256=before*64,detail='Synthetic registry change')


def test_valid_durable_receipt_and_unchanged_side(tmp_path):
    path=tmp_path/'c'
    with client_at(path,True) as c:
        v=seed(c);request,receipt=prepare(c,v)
    with client_at(path) as c:
        r=c.post(ROOT+'/conflicts',headers=HEAD,json=request);assert r.status_code==201,r.text
        h=c.get(ROOT+'/conflicts/C-01/revisions',headers=HEAD);assert h.status_code==200
        rows=h.json()['revisions'];assert len(rows)==2
        assert rows[-1]['sourceReceiptId']==receipt['receiptId']
        assert rows[-1]['before']==rows[0]['after']
        assert rows[-1]['afterSources']['b']==rows[0]['afterSources']['b']
        assert rows[-1]['afterSources']['a']['bytesVerified'] is False
        with c.app.state.db.session() as s:
            assert s.get(source_receipts.ConflictSourceReceipt,receipt['receiptId']).consumed_revision==2
        before=state(c);assert c.post(ROOT+'/conflicts',headers=HEAD,json=request).status_code==412
        assert state(c)==before


@pytest.mark.parametrize('aba',[False,True])
def test_multisource_change_rejected_atomic(tmp_path,aba):
    with client_at(tmp_path/'c',True) as c:
        v=seed(c);request,receipt=prepare(c,v,('a','b'));change(c,'EV-B')
        if aba:change(c,'EV-B','b','a')
        before=state(c)
        r=c.post(ROOT+'/conflicts',headers=HEAD,json=request)
        assert r.status_code==412 and r.json()['code']=='SOURCE_VERSION_CHANGED'
        assert state(c)==before
        with c.app.state.db.session() as s:assert s.get(source_receipts.ConflictSourceReceipt,receipt['receiptId']).consumed_revision is None


def test_expired_and_different_proposal_refused(tmp_path,monkeypatch):
    with client_at(tmp_path/'c',True) as c:
        v=seed(c);request,_=prepare(c,v)
        other=deepcopy(request);other['a']['valueText']='Other synthetic proposal'
        assert c.post(ROOT+'/conflicts',headers=HEAD,json=other).status_code==409
        now=source_receipts.now_utc();monkeypatch.setattr(source_receipts,'now_utc',lambda:now+timedelta(minutes=10))
        before=state(c);assert c.post(ROOT+'/conflicts',headers=HEAD,json=request).status_code==409
        assert state(c)==before


def test_original_note_permission_and_no_source_privilege_gain(tmp_path):
    with client_at(tmp_path/'c',True) as c:
        v=seed(c);request,_=prepare(c,v)
        ih=H('Investigator','Synthetic')
        r=c.post(ROOT+'/conflicts/C-01/source-receipts',headers=ih,json={'expectedVersion':token(c),'observations':{x:request[x] for x in ('a','b')}})
        assert r.status_code==403
        assert c.post(ROOT+'/conflicts',headers=ih,json=request).status_code==403
        assert c.patch(ROOT+'/conflicts/C-01',headers=ih,json={'expectedVersion':token(c),'resolution':'Synthetic pending verification'}).status_code==200


def test_unknown_source_and_no_receipt_stay_refused(tmp_path):
    with client_at(tmp_path/'c',True) as c:
        v=seed(c);v['a']['valueText']='Synthetic edit'
        assert c.post(ROOT+'/conflicts',headers=HEAD,json={**v,'expectedVersion':token(c)}).status_code==409
        v['a'].pop('evidenceId')
        r=c.post(ROOT+'/conflicts/C-01/source-receipts',headers=HEAD,json={'expectedVersion':token(c),'observations':{x:v[x] for x in ('a','b')}})
        assert r.status_code==409 and r.json()['code']=='SOURCE_VERSION_UNKNOWN'


def test_failure_after_receipt_consumption_rolls_back_all(tmp_path,monkeypatch):
    from sqlalchemy.orm import Session
    with client_at(tmp_path/'c',True) as c:
        v=seed(c);request,receipt=prepare(c,v);before=state(c)
        original=Session.flush;observed=[]
        def fail_consumption(s,*args,**kwargs):
            targets=[x for x in s.dirty if isinstance(x,source_receipts.ConflictSourceReceipt) and x.consumed_revision is not None]
            original(s,*args,**kwargs)
            if targets:
                observed.append(targets[0].consumed_revision)
                raise RuntimeError('Synthetic failure after receipt consumption flush')
        monkeypatch.setattr(Session,'flush',fail_consumption)
        result=c.post(ROOT+'/conflicts',headers=HEAD,json=request)
        assert observed==[2] and result.status_code==500
        monkeypatch.setattr(Session,'flush',original)
        assert state(c)==before
        with c.app.state.db.session() as s:assert s.get(source_receipts.ConflictSourceReceipt,receipt['receiptId']).consumed_revision is None
        # Explicit new user submission after proven rollback, not automatic unknown retry.
        assert c.post(ROOT+'/conflicts',headers=HEAD,json=request).status_code==201


def test_legacy_unknown_before_preserved_after_receipted_change(tmp_path):
    from mcis_service.timeline.models import ConflictRow
    with client_at(tmp_path/'c',True) as c:
        v=body();v['caseId']=CID;v['a']['evidenceId']='EV-A'
        with c.app.state.db.session() as s:
            put_doc(s,ConflictRow,CID,'C-01',v)
            put_doc(s,EvidenceRow,CID,'EV-A',{'caseId':CID,'evidenceId':'EV-A','sha256':'b'*64,'confidentiality':'Normal'})
        request,_=prepare(c,v)
        assert c.post(ROOT+'/conflicts',headers=HEAD,json=request).status_code==201
        h=c.get(ROOT+'/conflicts/C-01/revisions',headers=HEAD);assert h.status_code==200
        d=h.json();r=d['revisions'][0]
        assert d['coverage']=='unknown-before-capture' and r['beforeSources'] is None
        assert r['afterSources']['a']['sha256']=='b'*64 and not r['afterSources']['a']['bytesVerified']
        assert r['afterSources']['b']=={'evidenceId':None,'status':'unregistered','bytesVerified':False}


def test_one_receipt_concurrent_submission_commits_once(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    with client_at(tmp_path/'c',True) as c:
        request,receipt=prepare(c,seed(c))
        with ThreadPoolExecutor(2) as pool:
            responses=list(pool.map(lambda _:c.post(ROOT+'/conflicts',headers=HEAD,json=request),range(2)))
        assert sorted(r.status_code for r in responses)==[201,412]
        h=c.get(ROOT+'/conflicts/C-01/revisions',headers=HEAD);assert h.status_code==200
        assert len(h.json()['revisions'])==2
        with c.app.state.db.session() as s:assert s.get(source_receipts.ConflictSourceReceipt,receipt['receiptId']).consumed_revision==2
