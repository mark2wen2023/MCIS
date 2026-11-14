"""Independent durability/concurrency/rollback checks; synthetic fixture only."""
import json,uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from fastapi import HTTPException
from sqlalchemy import text
from .test_host_extraction import extraction_case
from .test_agents_w20 import ITEM
from mcis_service.agents import extraction_working_store as w,host_extraction as h
from mcis_service.identity import local


def prepared(v):
    args,binding=v;w.initialize(args[0])
    with args[0].session() as s:
        who,_=w._auth(s,args[2],args[3]);w.grant(s,who.subject_id,args[3],enabled=True)
    original=h.run(*args,binding,h.FixtureProvider(json.dumps({'statements':[ITEM]})))
    saved=w._save_generated(*args,str(uuid.uuid4()),binding,original)
    return args,saved,original


def decisions(note):return [{'index':1,'decision':'needs_verification','note':note}]


def test_two_actual_concurrent_review_writers_only_one_wins(extraction_case):
    args,saved,_=prepared(extraction_case);gate=Barrier(2)
    def worker(note):
        gate.wait()
        try:return w.append_review(*args[:4],saved['proposalId'],str(uuid.uuid4()),0,decisions(note))
        except HTTPException as e:return e.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(worker,n) for n in ('核实甲','核实乙')]
        results=[f.result(timeout=20) for f in futures]
    assert sum(isinstance(x,dict) for x in results)==1 and results.count(409)==1
    current=w.read(*args[:4],saved['proposalId']);assert current['revision']==1
    assert current['proposal']['result']['proposals'][0]['reviewStatus']=='Draft'


def test_final_failure_rolls_back_append_and_proposal(extraction_case,monkeypatch):
    args,saved,original=prepared(extraction_case)
    def failure(*a,**kw):raise RuntimeError('injected final guard failure')
    with monkeypatch.context() as m:
        m.setattr(w,'_final',failure)
        with pytest.raises(RuntimeError):w.append_review(*args[:4],saved['proposalId'],str(uuid.uuid4()),0,decisions('不可残留'))
        with pytest.raises(RuntimeError):w._save_generated(*args,str(uuid.uuid4()),extraction_case[1],original)
    assert w.read(*args[:4],saved['proposalId'])['revision']==0
    assert len(w.list_records(*args[:4])['items'])==1


@pytest.mark.parametrize('table',['extraction_working_proposals','extraction_working_reviews'])
@pytest.mark.parametrize('verb',['UPDATE','DELETE'])
def test_sql_append_only_trigger(extraction_case,table,verb):
    args,saved,_=prepared(extraction_case)
    w.append_review(*args[:4],saved['proposalId'],str(uuid.uuid4()),0,decisions('保留'))
    statement=f'UPDATE {table} SET doc=doc' if verb=='UPDATE' else f'DELETE FROM {table}'
    with pytest.raises(Exception):
        with args[0].engine.begin() as c:c.execute(text(statement))
    assert w.read(*args[:4],saved['proposalId'])['revision']==1


def test_reopened_database_and_actor_bound_replay(extraction_case):
    args,saved,_=prepared(extraction_case);op=str(uuid.uuid4());payload=decisions('等待补证')
    w.append_review(*args[:4],saved['proposalId'],op,0,payload)
    from mcis_service.db import Database
    reopened=Database(str(args[0].engine.url))
    replay=w.append_review(reopened,*args[1:4],saved['proposalId'],op,0,payload)
    assert replay['replayed'] and replay['revision']==1
    with args[0].session() as s:
        subject=local.create_subject(s);token=local.issue_session(s,subject)
        local.set_membership(s,subject,args[3],role='LeadInvestigator',can_save_unreviewed=True)
        w.grant(s,subject,args[3],enabled=True)
    with pytest.raises(HTTPException) as e:w.append_review(args[0],args[1],token,args[3],saved['proposalId'],op,0,payload)
    assert e.value.status_code==409
    current=w.read(*args[:4],saved['proposalId']);assert current['revision']==1
    assert args[2] not in json.dumps(current) and token not in json.dumps(current)
    reopened.engine.dispose()
