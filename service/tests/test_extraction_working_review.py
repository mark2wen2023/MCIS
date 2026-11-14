"""Independent safety review: durable working opinions, never facts or UI authority."""
import copy,json,uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import select,func
from .test_host_extraction import extraction_case
from .test_agents_w20 import ITEM
from mcis_service.agents import extraction_working_store as w,host_extraction as h
from mcis_service.agents.persistent_extraction_review_host import PersistentExtractionReviewHost
from mcis_service.identity import local

@pytest.fixture
def setup_review(extraction_case):
    a,b=extraction_case;w.initialize(a[0])
    with a[0].session() as s:w.grant(s,local.authorize_read(s,a[2],a[3]).subject_id,a[3],enabled=True)
    def host(provider=True):return PersistentExtractionReviewHost(db=a[0],settings=a[1],session_token=a[2],case_id=a[3],record_id=a[4],provider=h.FixtureProvider(json.dumps({'statements':[ITEM]})) if provider else None)
    return a,b,host

def ds():return [{'index':1,'decision':'adopted_working','note':'仅作为工作意见，尚待核实'}]
def count(a,cls):
    with a[0].session() as s:return s.scalar(select(func.count()).select_from(cls))

@pytest.mark.parametrize('field,value',[('quote','forged'),('claim',{}),('authorSubjectId','forged'),('receipt',{}),('token','forged'),('factVerified',True)])
def test_client_decision_cannot_supply_proposal_or_author(setup_review,field,value):
    a,_,host=setup_review
    with host() as c:
        pid=c.generate(str(uuid.uuid4()))['proposalId'];payload=ds();payload[0][field]=value
        with pytest.raises(ValueError):c.review(pid,str(uuid.uuid4()),0,payload)
        assert c.read(pid)['revision']==0
    assert count(a,w.WorkingReview)==0


def test_no_provider_never_stores_fake_result(setup_review):
    a,_,host=setup_review
    with host(False) as c:
        r=c.generate(str(uuid.uuid4()));assert r['status']=='not_connected' and r['inferencePerformed'] is False
    assert count(a,w.WorkingProposal)==count(a,w.WorkingReview)==0


def test_read_returns_detached_copy_not_live_persisted_objects(setup_review):
    a,_,host=setup_review
    with host() as c:
        r=c.generate(str(uuid.uuid4()));pid=r['proposalId'];r['proposal']['result']['proposals'][0]['quote']='MUTATED'
        c.review(pid,str(uuid.uuid4()),0,ds());view=c.read(pid);view['reviews'][0]['decisions'][0]['note']='MUTATED'
        fresh=c.read(pid);assert fresh['proposal']['result']['proposals'][0]['quote']==ITEM['quote'];assert fresh['reviews'][0]['decisions']==ds()
        assert fresh['status']=='working_unreviewed' and fresh['factActivated'] is False
        assert fresh['proposal']['result']['fixture'] is True and fresh['proposal']['result']['proposals'][0]['reviewStatus']=='Draft'


def test_replay_requires_current_special_write_grant(setup_review):
    a,_,host=setup_review;generate_op=str(uuid.uuid4());review_op=str(uuid.uuid4())
    with host() as c:
        pid=c.generate(generate_op)['proposalId'];c.review(pid,review_op,0,ds())
        with a[0].session() as s:w.grant(s,local.authorize_read(s,a[2],a[3]).subject_id,a[3],enabled=False)
        for f in (lambda:c.generate(generate_op),lambda:c.review(pid,review_op,0,ds())):
            with pytest.raises(HTTPException) as e:f()
            assert e.value.status_code==403
    assert count(a,w.WorkingReview)==1


def test_binding_change_denies_all_history_and_replay_without_deleting_saved(setup_review):
    a,_,host=setup_review;op=str(uuid.uuid4())
    with host() as c:
        pid=c.generate(str(uuid.uuid4()))['proposalId'];c.review(pid,op,0,ds())
    from mcis_service.interviews.models import InterviewRow
    with a[0].session() as s:
        r=s.scalars(select(InterviewRow).where(InterviewRow.case_id==a[3],InterviewRow.key==a[4])).one();doc=copy.deepcopy(r.doc);doc['turns'][0]['sensitiveFragments']=['changed policy fragment'];r.doc=doc
    for f in (lambda:w.read(*a[:4],pid),lambda:w.list_records(*a[:4]),lambda:w.append_review(*a[:4],pid,op,0,ds())):
        with pytest.raises(HTTPException) as e:f()
        assert e.value.status_code==409 and '未保存' not in str(e.value.detail)
    assert count(a,w.WorkingProposal)==count(a,w.WorkingReview)==1


def test_closed_host_never_returns_cached_content(setup_review):
    a,_,host=setup_review;c=host();op=str(uuid.uuid4());pid=c.generate(op)['proposalId'];c.close()
    for f in (lambda:c.generate(op),lambda:c.read(pid),lambda:c.list(),lambda:c.review(pid,str(uuid.uuid4()),0,ds())):
        with pytest.raises(ValueError):f()


def test_trusted_method_has_no_ui_result_input(setup_review):
    _,_,host=setup_review
    with host() as c:
        with pytest.raises(TypeError):c.generate(str(uuid.uuid4()),result={'status':'Approved'})
        with pytest.raises(TypeError):c.review(str(uuid.uuid4()),str(uuid.uuid4()),0,ds(),quote='injected')


def test_reopen_generate_replay_never_reinvokes_provider(setup_review,monkeypatch):
    a,_,host=setup_review;op=str(uuid.uuid4())
    with host() as c:pid=c.generate(op)['proposalId']
    monkeypatch.setattr(h.FixtureProvider,'complete',lambda *args:pytest.fail('replay must not infer again'))
    with host() as c:r=c.generate(op)
    assert r['proposalId']==pid and r['replayed'] is True and count(a,w.WorkingProposal)==1


def test_close_during_inference_never_stores_or_returns_proposals(setup_review,monkeypatch):
    from threading import Event
    from concurrent.futures import ThreadPoolExecutor
    a,_,host=setup_review;c=host();started=Event();release=Event()
    def provider(*args):
        started.set();assert release.wait(10);return json.dumps({'statements':[ITEM]})
    monkeypatch.setattr(h.FixtureProvider,'complete',provider)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(c.generate,str(uuid.uuid4()))
        try:assert started.wait(10);c.close()
        finally:release.set()
        with pytest.raises(ValueError):future.result(timeout=10)
    assert count(a,w.WorkingProposal)==0


def test_membership_revoke_blocks_read_list_and_replay(setup_review):
    a,_,host=setup_review;op=str(uuid.uuid4())
    with host() as c:
        pid=c.generate(op)['proposalId']
        with a[0].session() as s:
            who=local.authorize_read(s,a[2],a[3]);local.set_membership(s,who.subject_id,a[3],role='LeadInvestigator',enabled=False)
        for f in (lambda:c.read(pid),lambda:c.list(),lambda:c.generate(op)):
            with pytest.raises(HTTPException) as e:f()
            assert e.value.status_code==403


def test_source_policy_denies_history_and_replay(setup_review):
    from mcis_service.redaction.models import AccessPolicyRow
    from mcis_service.redaction.policy import default_policy
    a,_,host=setup_review;op=str(uuid.uuid4())
    with host() as c:pid=c.generate(op)['proposalId']
    with a[0].session() as s:
        row=s.scalars(select(AccessPolicyRow).where(AccessPolicyRow.case_id==a[3],AccessPolicyRow.key=='policy')).first()
        policy=copy.deepcopy(row.doc if row else default_policy());policy['matrix']['LeadInvestigator']['testimony']='Deny'
        if row:row.doc=policy
        else:s.add(AccessPolicyRow(case_id=a[3],key='policy',doc=policy))
    for f in (lambda:w.read(*a[:4],pid),lambda:w.list_records(*a[:4]),lambda:w.append_review(*a[:4],pid,str(uuid.uuid4()),0,ds())):
        with pytest.raises(HTTPException) as e:f()
        assert e.value.status_code==403
