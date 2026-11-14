"""Independent supplemental working-history archive boundary probes."""
import json,copy,uuid
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select,func,text
from sqlalchemy.orm import Session
from .test_extraction_working_store import working,host,decisions
from .test_host_extraction import extraction_case
from .test_local_authority import provision
from .conftest import H,make_settings,CASE
from mcis_service.main import create_app
from mcis_service.agents import working_history_archive as a,extraction_working_store as w,extraction
from mcis_service.investigation import journal as j
from mcis_service.identity import local

@pytest.fixture
def arch(working):
    args,_=working;a.initialize(args[0])
    with host(working) as c:
        pid=c.generate(str(uuid.uuid4()))['proposalId']
        c.review(pid,str(uuid.uuid4()),0,decisions('first opinion'))
        c.review(pid,str(uuid.uuid4()),1,decisions('second opinion'))
    with args[0].session() as s:
        subject=local.authorize_read(s,args[2],args[3]).subject_id
        a.grant(s,subject,args[3],can_import=True,can_read=True)
    return args,a.export_bundle(*args[:4]),pid,subject

def repack(p):return a.canonical({'sha256':extraction.digest(p),'payload':p})
def count(db,model):
    with db.session() as s:return s.scalar(select(func.count()).select_from(model))


def test_roundtrip_retains_versions_but_not_live_activation(arch):
    args,raw,pid,_=arch
    before=(count(args[0],w.WorkingProposal),count(args[0],w.WorkingReview))
    one=a.restore_bundle(args[0],args[2],args[3],raw);two=a.restore_bundle(args[0],args[2],args[3],raw)
    assert not one['activated'] and two['replayed']
    view=a.read_imported(args[0],args[2],args[3],one['sha256'])
    item=view['payload']['proposals'][0]
    assert item['proposalId']==pid and [r['decisions'][0]['note'] for r in item['reviews']]==['first opinion','second opinion']
    assert item['result']['proposals'][0]['reviewStatus']=='Draft'
    assert item['result']['fixture'] is True and item['result']['inferencePerformed'] is False
    assert view['historicalClaimsVerified'] is False and view['activated'] is False
    assert before==(count(args[0],w.WorkingProposal),count(args[0],w.WorkingReview))
    assert args[2] not in raw.decode() and 'operationId' not in raw.decode() and 'providerKey' not in raw.decode()


def test_cross_generation_restore_into_empty_target_no_live_rows(arch,tmp_path):
    args,raw,pid,_=arch
    with args[0].session() as s:doc=copy.deepcopy(j.load_case(s,args[3]))
    with TestClient(create_app(make_settings(tmp_path/'empty-target',seed=False))) as target:
        assert target.post('/api/v1/cases',headers=H(),json=doc).status_code==201
        db=target.app.state.db;w.initialize(db);a.initialize(db);subject,token=provision(target)
        with db.session() as s:a.grant(s,subject,CASE,can_import=True,can_read=True)
        imported=a.restore_bundle(db,token,CASE,raw)
        read=a.read_imported(db,token,CASE,imported['sha256'])
        with db.session() as s:assert j.case_current(s,CASE)!=read['payload']['originCaseIncarnation']
        from mcis_service.interviews.models import InterviewRow
        from mcis_service.evidence_intake.incarnation import SourceIncarnationRow
        for model in (w.WorkingProposal,w.WorkingReview,w.WorkingGrant,InterviewRow,SourceIncarnationRow):assert count(db,model)==0
        assert read['payload']['proposals'][0]['proposalId']==pid
        with pytest.raises(HTTPException):w.read(db,target.app.state.settings,token,CASE,pid)


@pytest.mark.parametrize('rights',[(False,False),(True,False),(False,True)])
def test_import_and_read_are_independent_grants(arch,rights):
    args,raw,_,subject=arch
    imported=a.restore_bundle(args[0],args[2],args[3],raw)
    with args[0].session() as s:a.grant(s,subject,args[3],can_import=rights[0],can_read=rights[1])
    for allowed,fn in [(rights[0],lambda:a.restore_bundle(args[0],args[2],args[3],raw)),(rights[1],lambda:a.read_imported(args[0],args[2],args[3],imported['sha256'])),(rights[1],lambda:a.list_imported(args[0],args[2],args[3]))]:
        if allowed:fn()
        else:
            with pytest.raises(HTTPException) as e:fn()
            assert e.value.status_code==403


def test_invalid_live_source_denies_export_but_authorized_history_read_still_works(arch):
    from mcis_service.interviews.models import InterviewRow
    args,raw,_,_=arch;imported=a.restore_bundle(args[0],args[2],args[3],raw)
    with args[0].session() as s:
        row=s.scalars(select(InterviewRow).where(InterviewRow.case_id==args[3],InterviewRow.key==args[4])).one();doc=copy.deepcopy(row.doc);doc['turns'][0]['answer']+=' changed';row.doc=doc
    with pytest.raises(HTTPException):a.export_bundle(*args[:4])
    assert not a.read_imported(args[0],args[2],args[3],imported['sha256'])['activated']


@pytest.mark.parametrize('damage',['extra','authority','origin','case','record','seq','boolrevision','decisions','fact','reviewstatus','fixture','citation','duplicateproposal'])
def test_strict_untrusted_payload_rejected_before_rows(arch,damage):
    args,raw,_,_=arch;p=json.loads(raw)['payload'];item=p['proposals'][0]
    if damage=='extra':p['grants']={'admin':True}
    elif damage=='authority':p['authority']='verified'
    elif damage=='origin':p['originCaseIncarnation']='invalid'
    elif damage=='case':p['caseId']='FOREIGN'
    elif damage=='record':item['recordId']='OTHER'
    elif damage=='seq':item['reviews'][0]['revision']=2
    elif damage=='boolrevision':item['reviews'][0]['revision']=True
    elif damage=='decisions':item['reviews'][0]['decisions']=[]
    elif damage=='fact':item['reviews'][0]['factVerified']=True
    elif damage=='reviewstatus':item['result']['proposals'][0]['reviewStatus']='Confirmed'
    elif damage=='fixture':item['result']['inferencePerformed']=True
    elif damage=='citation':item['result']['citations'][0]['recordId']='OTHER'
    elif damage=='duplicateproposal':p['proposals'].append(copy.deepcopy(item))
    with pytest.raises(HTTPException):a.restore_bundle(args[0],args[2],args[3],repack(p))
    assert count(args[0],a.ImportedWorkingArchive)==0


def test_historical_author_is_not_provisioned(arch):
    args,raw,_,_=arch;p=json.loads(raw)['payload'];fake=str(uuid.uuid4());item=p['proposals'][0];item['generatedBySubjectId']=fake
    for r in item['reviews']:r['authorSubjectId']=fake
    result=a.restore_bundle(args[0],args[2],args[3],repack(p));assert not result['activated']
    with args[0].session() as s:assert s.get(local.Subject,fake) is None
    assert fake in json.dumps(a.read_imported(args[0],args[2],args[3],result['sha256']))


def test_commit_failure_has_no_imported_row(arch,monkeypatch):
    args,raw,_,_=arch;original=Session.commit
    def fail(_):raise RuntimeError('synthetic commit error')
    monkeypatch.setattr(Session,'commit',fail)
    with pytest.raises(RuntimeError):a.restore_bundle(args[0],args[2],args[3],raw)
    monkeypatch.setattr(Session,'commit',original)
    assert count(args[0],a.ImportedWorkingArchive)==0
    assert not a.restore_bundle(args[0],args[2],args[3],raw)['replayed']


def test_final_import_grant_revoke_rolls_back(arch,monkeypatch):
    args,raw,_,subject=arch;old=a._final
    def final(s,token,case_id,mode,before):
        a.grant(s,subject,case_id,can_import=False,can_read=True)
        return old(s,token,case_id,mode,before)
    monkeypatch.setattr(a,'_final',final)
    with pytest.raises(HTTPException):a.restore_bundle(args[0],args[2],args[3],raw)
    assert count(args[0],a.ImportedWorkingArchive)==0


def test_raw_duplicate_nonfinite_depth_and_budget_rejected(arch):
    args,raw,_,_=arch
    for bad in (b'{"sha256":"a","sha256":"b","payload":{}}',b'{"x":NaN}',b'['*2000+b']'*2000,b' '*(a.MAX_BYTES+1)):
        with pytest.raises(HTTPException):a.restore_bundle(args[0],args[2],args[3],bad)
    assert count(args[0],a.ImportedWorkingArchive)==0


def test_final_epoch_read_expiry_denies_return_and_rolls_back(arch,monkeypatch):
    args,raw,_,_=arch;old=j.load_case;calls=0
    def load(s,case_id):
        nonlocal calls
        value=old(s,case_id);calls+=1
        if calls==2:
            s.scalar(select(local.SessionRecord)).expires_at=0;s.flush()
        return value
    monkeypatch.setattr(j,'load_case',load)
    with pytest.raises(HTTPException):a.restore_bundle(args[0],args[2],args[3],raw)
    assert count(args[0],a.ImportedWorkingArchive)==0


def test_target_epoch_change_hides_history_and_prevents_replay(arch):
    from mcis_service.cases.models import CaseRow
    args,raw,_,_=arch;imported=a.restore_bundle(args[0],args[2],args[3],raw)
    with args[0].session() as s:
        row=s.scalars(select(CaseRow).where(CaseRow.case_id==args[3])).one();doc=copy.deepcopy(row.doc);doc['caseEpochUtc']='2020-01-01T00:00:00Z';row.doc=doc
    for fn in (lambda:a.read_imported(args[0],args[2],args[3],imported['sha256']),lambda:a.restore_bundle(args[0],args[2],args[3],raw)):
        with pytest.raises(HTTPException):fn()
    assert a.list_imported(args[0],args[2],args[3])['items']==[]
    assert count(args[0],a.ImportedWorkingArchive)==1


def test_revoked_session_cannot_read_list_or_import_existing_archive(arch):
    args,raw,_,_=arch;imported=a.restore_bundle(args[0],args[2],args[3],raw)
    with args[0].session() as s:local.revoke_session(s,args[2])
    for fn in (lambda:a.read_imported(args[0],args[2],args[3],imported['sha256']),lambda:a.list_imported(args[0],args[2],args[3]),lambda:a.restore_bundle(args[0],args[2],args[3],raw)):
        with pytest.raises(HTTPException) as e:fn()
        assert e.value.status_code==403
    assert count(args[0],a.ImportedWorkingArchive)==1

@pytest.mark.parametrize('bad',['document_nonnull','registered_null','bad_id','bad_incarnation','bad_hash','extra'])
def test_source_declaration_scope_and_shape_fail_closed(arch,bad):
    args,raw,_,_=arch;p=json.loads(raw)['payload'];item=p['proposals'][0]
    decl={'evidenceId':'historical-source','sourceIncarnation':str(uuid.uuid4()),'sourceSha256':'a'*64}
    receipt=item['result']['receipt']
    receipt['sourceScope']='interview_document_only' if bad=='document_nonnull' else 'registered_original_bytes'
    receipt['runChecksum']=extraction.digest({k:v for k,v in receipt.items() if k!='runChecksum'})
    if bad=='bad_id':decl['evidenceId']='../other-case'
    if bad=='bad_incarnation':decl['sourceIncarnation']='not-uuid'
    if bad=='bad_hash':decl['sourceSha256']='not-hash'
    if bad=='extra':decl['verified']=True
    item['sourceDeclaration']=None if bad=='registered_null' else decl
    with pytest.raises(HTTPException):a.restore_bundle(args[0],args[2],args[3],repack(p))
    assert count(args[0],a.ImportedWorkingArchive)==0


def test_rehashed_registered_declaration_is_inert_unverified_claim(arch):
    from mcis_service.evidence_intake.incarnation import SourceIncarnationRow
    args,raw,_,_=arch;p=json.loads(raw)['payload'];item=p['proposals'][0]
    declaration={'evidenceId':'missing-historical-source','sourceIncarnation':str(uuid.uuid4()),'sourceSha256':'b'*64}
    item['sourceDeclaration']=declaration;receipt=item['result']['receipt'];receipt['sourceScope']='registered_original_bytes'
    receipt['runChecksum']=extraction.digest({k:v for k,v in receipt.items() if k!='runChecksum'})
    before=count(args[0],SourceIncarnationRow)
    imported=a.restore_bundle(args[0],args[2],args[3],repack(p))
    view=a.read_imported(args[0],args[2],args[3],imported['sha256'])
    assert view['historicalClaimsVerified'] is False and view['activated'] is False
    assert view['payload']['proposals'][0]['sourceDeclaration']==declaration
    assert count(args[0],SourceIncarnationRow)==before
