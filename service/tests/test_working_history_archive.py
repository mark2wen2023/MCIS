import json,uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from .test_host_extraction import extraction_case
from .test_extraction_working_store import working,host,decisions
from mcis_service.agents import working_history_archive as a,extraction_working_store as w
from mcis_service.identity import local

@pytest.fixture
def archive_bundle(working):
    args,_=working;a.initialize(args[0])
    with host(working) as c:
        pid=c.generate(str(uuid.uuid4()))['proposalId'];c.review(pid,str(uuid.uuid4()),0,decisions())
    raw=a.export_bundle(*args[:4])
    return working,raw

def permissions(v,read=True,write=True):
    args,_=v
    with args[0].session() as s:a.grant(s,local.authorize_read(s,args[2],args[3]).subject_id,args[3],can_import=write,can_read=read)


def test_archive_roundtrip_inert(archive_bundle):
    v,raw=archive_bundle;args,_=v;permissions(v)
    before=w.list_records(*args[:4]);one=a.restore_bundle(args[0],args[2],args[3],raw)
    assert not one['activated'] and a.restore_bundle(args[0],args[2],args[3],raw)['replayed']
    restored=a.read_imported(args[0],args[2],args[3],one['sha256'])
    assert restored['status']=='imported_untrusted_history' and not restored['historicalClaimsVerified']
    assert restored['payload']['proposals'][0]['reviews'][0]['decisions']==decisions()
    assert a.list_imported(args[0],args[2],args[3])['items'][0]['sha256']==one['sha256']
    assert w.list_records(*args[:4])==before and args[2] not in raw.decode()
    assert 'operation_id' not in raw.decode() and 'providerKey' not in raw.decode()


def test_import_does_not_confer_read(archive_bundle):
    v,raw=archive_bundle;args,_=v
    with pytest.raises(HTTPException):a.restore_bundle(args[0],args[2],args[3],raw)
    permissions(v,read=False);saved=a.restore_bundle(args[0],args[2],args[3],raw)
    with pytest.raises(HTTPException) as e:a.read_imported(args[0],args[2],args[3],saved['sha256'])
    assert e.value.status_code==403
    permissions(v,read=True,write=False)
    assert a.read_imported(args[0],args[2],args[3],saved['sha256'])['activated'] is False
    with pytest.raises(HTTPException):a.restore_bundle(args[0],args[2],args[3],raw)

@pytest.mark.parametrize('damage',['unknown','hash','revision','decision','record','span','fixture','citationbool','foreigncase'])
def test_invalid_archive_no_write(archive_bundle,damage):
    v,raw=archive_bundle;args,_=v;permissions(v);wrapper=json.loads(raw);p=wrapper['payload'];item=p['proposals'][0]
    if damage=='unknown':p['token']='forbidden'
    elif damage=='revision':item['reviews'][0]['revision']=2
    elif damage=='decision':item['reviews'][0]['decisions']*=2
    elif damage=='record':item['result']['proposals'][0]['recordId']='OTHER'
    elif damage=='span':item['result']['proposals'][0]['span']['length']+=1
    elif damage=='fixture':item['result']['fixture']=False
    elif damage=='citationbool':item['result']['citations'][0]['round']=True
    elif damage=='foreigncase':p['caseId']='OTHER'
    wrapper['sha256']='0'*64 if damage=='hash' else a.extraction.digest(p)
    with pytest.raises(HTTPException):a.restore_bundle(args[0],args[2],args[3],a.canonical(wrapper))
    with args[0].session() as s:assert not list(s.scalars(select(a.ImportedWorkingArchive)))


def test_changed_live_record_blocks_export_not_explicit_archive_read(archive_bundle):
    v,raw=archive_bundle;args,_=v;permissions(v);saved=a.restore_bundle(args[0],args[2],args[3],raw)
    from mcis_service.interviews.models import InterviewRow
    with args[0].session() as s:
        row=s.scalars(select(InterviewRow).where(InterviewRow.case_id==args[3],InterviewRow.key==args[4])).one()
        row.doc={**row.doc,'signed':not row.doc.get('signed',False)}
    with pytest.raises(HTTPException):a.export_bundle(*args[:4])
    restored=a.read_imported(args[0],args[2],args[3],saved['sha256'])
    assert restored['historicalClaimsVerified'] is False and restored['activated'] is False


def test_historical_origin_not_live_identity(archive_bundle):
    v,raw=archive_bundle;args,_=v;permissions(v);wrapper=json.loads(raw);p=wrapper['payload']
    p['originCaseIncarnation']=str(uuid.uuid4());fake=str(uuid.uuid4());p['proposals'][0]['generatedBySubjectId']=fake
    wrapper['sha256']=a.extraction.digest(p);saved=a.restore_bundle(args[0],args[2],args[3],a.canonical(wrapper))
    assert a.read_imported(args[0],args[2],args[3],saved['sha256'])['payload']['originCaseIncarnation']==p['originCaseIncarnation']
    with args[0].session() as s:assert s.get(local.Subject,fake) is None


def test_registered_source_declaration_export(working):
    args,_=working
    from mcis_service.interviews.models import InterviewRow
    from mcis_service.evidence_intake.incarnation import SourceIncarnationRow
    with args[0].session() as s:
        source=s.scalars(select(SourceIncarnationRow).where(SourceIncarnationRow.case_id==args[3])).first()
        row=s.scalars(select(InterviewRow).where(InterviewRow.case_id==args[3],InterviewRow.key==args[4])).one()
        row.doc={**row.doc,'evidenceId':source.evidence_id,'sourceSha256':source.source_sha256}
        expected={'evidenceId':source.evidence_id,'sourceIncarnation':source.incarnation,'sourceSha256':source.source_sha256}
    with host(working) as c:c.generate(str(uuid.uuid4()))
    raw=a.export_bundle(*args[:4]);payload=json.loads(raw)['payload'];item=payload['proposals'][0]
    assert item['sourceDeclaration']==expected and item['result']['receipt']['sourceScope']=='registered_original_bytes'
    item['sourceDeclaration']=None
    with pytest.raises(HTTPException):a.validate(a.canonical({'payload':payload,'sha256':a.extraction.digest(payload)}))


def test_export_final_epoch_expiry_denied(archive_bundle,monkeypatch):
    v,_=archive_bundle;args,_=v;finalized=False;original_final=w._final;original_load=a.j.load_case
    def finalized_check(*call,**kw):
        nonlocal finalized
        result=original_final(*call,**kw);finalized=True;return result
    def load(s,*call,**kw):
        result=original_load(s,*call,**kw)
        if finalized:s.scalar(select(local.SessionRecord)).expires_at=0
        return result
    monkeypatch.setattr(w,'_final',finalized_check);monkeypatch.setattr(a.j,'load_case',load)
    with pytest.raises(HTTPException) as e:a.export_bundle(*args[:4])
    assert e.value.status_code==403
