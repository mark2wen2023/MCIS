import copy,json,uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import select,text
from .test_host_extraction import extraction_case
from .test_agents_w20 import ITEM
from mcis_service.agents import extraction_working_store as w,host_extraction as h
from mcis_service.agents.persistent_extraction_review_host import PersistentExtractionReviewHost
from mcis_service.identity import local

@pytest.fixture
def working(extraction_case):
    args,binding=extraction_case;w.initialize(args[0])
    with args[0].session() as s:w.grant(s,local.authorize_read(s,args[2],args[3]).subject_id,args[3],enabled=True)
    return args,binding

def host(v):
    a,_=v
    return PersistentExtractionReviewHost(db=a[0],settings=a[1],session_token=a[2],case_id=a[3],record_id=a[4],provider=h.FixtureProvider(json.dumps({'statements':[ITEM]})))
def decisions(note='需核实'):return [{'index':1,'decision':'needs_verification','note':note}]

def test_persist_reopen_revise_original_retained(working):
    a,_=working;op=str(uuid.uuid4())
    with host(working) as c:
        saved=c.generate(op);pid=saved['proposalId'];assert saved['saved'] and not saved['factActivated'] and saved['revision']==0
        assert c.scope['profile']=='mcis-extraction-review-persistent-trial-v1'
        first=c.review(pid,str(uuid.uuid4()),0,decisions());assert first['revision']==1
    with host(working) as c:
        assert c.generate(op)['replayed']
        second=c.review(pid,str(uuid.uuid4()),1,decisions('补充核实后仍保留疑问'))
        assert second['revision']==2 and len(second['reviews'])==2
        assert second['proposal']['result']['proposals'][0]['quote']==ITEM['quote']
        assert c.read(pid)['reviews'][0]['decisions']==decisions()
        assert c.list()['items'][0]['proposalId']==pid
    assert a[2] not in json.dumps(second)


def test_separate_grant_required(extraction_case):
    a,_=extraction_case;w.initialize(a[0])
    with host(extraction_case) as c:
        with pytest.raises(HTTPException) as e:c.generate(str(uuid.uuid4()))
    assert e.value.status_code==403


def test_read_without_write_grant_and_revoke(working):
    a,_=working
    with host(working) as c:
        saved=c.generate(str(uuid.uuid4()));pid=saved['proposalId']
        with a[0].session() as s:w.grant(s,local.authorize_read(s,a[2],a[3]).subject_id,a[3],enabled=False)
        assert c.read(pid)['proposalId']==pid
        with pytest.raises(HTTPException):c.review(pid,str(uuid.uuid4()),0,decisions())
        with a[0].session() as s:local.revoke_session(s,a[2])
        with pytest.raises(HTTPException):c.read(pid)


def test_record_change_denies_read_list_and_replay(working):
    a,_=working;op=str(uuid.uuid4())
    with host(working) as c:saved=c.generate(op)
    from mcis_service.interviews.models import InterviewRow
    with a[0].session() as s:
        row=s.scalars(select(InterviewRow).where(InterviewRow.case_id==a[3],InterviewRow.key==a[4])).one();doc=copy.deepcopy(row.doc);doc['turns'][0]['answer']+=' changed';row.doc=doc
    for call in (lambda:w.read(*a[:4],saved['proposalId']),lambda:w.list_records(*a[:4])):
        with pytest.raises(HTTPException) as e:call()
        assert e.value.status_code==409
    with host(working) as c:
        with pytest.raises(HTTPException):c.generate(op)


def test_no_auto_initialize(extraction_case):
    a,_=extraction_case
    with a[0].engine.connect() as c:assert 'extraction_working_proposals' not in set(c.execute(text("select name from sqlite_master where type='table'")).scalars())

@pytest.mark.parametrize('damage',['status','quote','receipt','extra'])
def test_private_save_revalidates_frozen_output(working,damage):
    a,binding=working;result=h.run(*a,binding,h.FixtureProvider(json.dumps({'statements':[ITEM]})))
    if damage=='status':result['status']='Approved'
    elif damage=='quote':result['proposals'][0]['quote']='invented'
    elif damage=='receipt':result['receipt']['bindingDigest']='0'*64
    else:result['token']='not-allowed'
    with pytest.raises((ValueError,HTTPException)):w._save_generated(*a,str(uuid.uuid4()),binding,result)
    assert w.list_records(*a[:4])['items']==[]


def test_replay_review_conflict_and_stale_revision(working):
    a,_=working
    with host(working) as c:
        pid=c.generate(str(uuid.uuid4()))['proposalId'];op=str(uuid.uuid4())
        assert c.review(pid,op,0,decisions())['revision']==1
        assert c.review(pid,op,0,decisions())['replayed']
        with pytest.raises(HTTPException):c.review(pid,op,0,decisions('changed'))
        with pytest.raises(HTTPException):c.review(pid,str(uuid.uuid4()),0,decisions())
