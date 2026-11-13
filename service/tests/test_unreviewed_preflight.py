"""Internal server-generated snapshot; no persistence or real LLM/core claim."""
import pytest
from types import SimpleNamespace
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from .conftest import C,CASE,H
from .test_source_incarnation import fresh
from .test_registered_align_preview import register,request,RAW
from .test_align_preview_w41 import result as base_result

def result(payload):
    r=base_result(payload)
    r["result"]["calibration"]["uncalibratedSources"]=[s["sourceId"] for s in payload["sources"]]
    return r

from .test_binding_review_independent import snapshot
from mcis_service.timeline import align_preview,unreviewed_preflight as preflight
from mcis_service.timeline.evidence_preview import RegisteredPreview


def ctx(client):
    return SimpleNamespace(role='Investigator',operator='test',settings=client.app.state.settings,db=client.app.state.db)


def test_server_calculates_original_bytes_and_never_persists(client,empty_client,monkeypatch):
    target=fresh(client,empty_client);receipt=register(target);calls=[]
    def core(*args):calls.append(args[2]);return result(args[2])
    monkeypatch.setattr(align_preview,'core_run',core)
    before=snapshot(target)
    answer=preflight.compute_unreviewed(ctx(target),CASE,RegisteredPreview.model_validate(request(receipt)))
    assert snapshot(target)==before
    assert calls[0]['sources'][0]['text']==RAW.decode()
    assert answer['serverPreview']['result']['caseId']==CASE
    assert answer['persisted'] is False and answer['usableAsWriteCredential'] is False
    assert answer['observationApproval']=='not_assessed'
    assert answer['generationSnapshot']['sourceIdentities'][0]['evidenceId']==receipt['evidenceId']


@pytest.mark.parametrize('field',['result','serverPreview','generationSnapshot','observationApproval'])
def test_caller_cannot_supply_result_or_authority(client,field):
    receipt=register(client);body=request(receipt);body[field]={}
    with pytest.raises(ValidationError):RegisteredPreview.model_validate(body)


def test_legacy_fails_before_core(client,monkeypatch):
    receipt=register(client)
    monkeypatch.setattr(align_preview,'core_run',lambda *_:pytest.fail('legacy cannot calculate'))
    with pytest.raises(HTTPException) as error:
        preflight.compute_unreviewed(ctx(client),CASE,RegisteredPreview.model_validate(request(receipt)))
    assert error.value.status_code==409


@pytest.mark.parametrize('change',['source_generation','case_generation','readonly','review','bytes'])
def test_changes_during_compute_fail_closed(client,empty_client,monkeypatch,change):
    target=fresh(client,empty_client);receipt=register(target)
    def core(*args):
        if change=='source_generation':
            from mcis_service.evidence_intake.incarnation import SourceIncarnationRow,allocate_for_intake
            from mcis_service.evidence.models import CustodyEventRow
            with target.app.state.db.session() as s:
                row=s.get(SourceIncarnationRow,(CASE,receipt['evidenceId']));s.delete(row);s.flush()
                reg=s.scalars(select(CustodyEventRow).where(CustodyEventRow.case_id==CASE,CustodyEventRow.kind=='Register')).one()
                allocate_for_intake(s,CASE,reg,receipt['requestDigest'],'test','Investigator')
        elif change=='case_generation':
            from mcis_service.cases.incarnation import CaseIncarnationRow,allocate,persist,marker
            from mcis_service.audit import service as audit
            with target.app.state.db.session() as s:
                s.delete(s.get(CaseIncarnationRow,CASE));s.flush();value=allocate(s,CASE,'created')
                event=audit.append(s,case_id=CASE,operator='test',role='Investigator',action='case.create',category='Case',command='test replacement',entity_type='case',entity_id=CASE,snapshot_ref=marker(value))
                persist(s,value,event)
        elif change=='readonly':
            from mcis_service.redaction.policy import default_policy
            p=default_policy();p['matrix']['Investigator']['timeline']='ReadOnly'
            assert target.put(C+'/access-policy',headers=H('LeadInvestigator'),json=p).status_code==200
        elif change=='review':
            assert target.patch(C+'/evidence/'+receipt['evidenceId'],headers=H(),json={'needsReview':True,'reason':'test'}).status_code==200
        else:
            path=target.app.state.settings.blob_dir/CASE/receipt['evidence']['relativePath'];path.write_bytes(b'changed')
        return result(args[2])
    monkeypatch.setattr(align_preview,'core_run',core)
    with pytest.raises(HTTPException) as error:
        preflight.compute_unreviewed(ctx(target),CASE,RegisteredPreview.model_validate(request(receipt)))
    assert error.value.status_code==(403 if change=='readonly' else 409)


def test_caller_dto_mutation_does_not_substitute_mapping(client,empty_client,monkeypatch):
    target=fresh(client,empty_client);receipt=register(target);body=RegisteredPreview.model_validate(request(receipt))
    def core(*args):
        body.sources[0].csvMapping.timeColumn='forged'
        return result(args[2])
    monkeypatch.setattr(align_preview,'core_run',core)
    answer=preflight.compute_unreviewed(ctx(target),CASE,body)
    assert answer['request']['sources'][0]['csvMapping']['timeColumn']=='utc'


def test_envelope_bound_does_not_truncate_or_write(client,empty_client,monkeypatch):
    target=fresh(client,empty_client);receipt=register(target)
    monkeypatch.setattr(align_preview,'core_run',lambda *args:result(args[2]))
    monkeypatch.setattr(preflight,'MAX_ENVELOPE_BYTES',10)
    before=snapshot(target)
    with pytest.raises(HTTPException) as error:
        preflight.compute_unreviewed(ctx(target),CASE,RegisteredPreview.model_validate(request(receipt)))
    assert error.value.status_code==413
    assert snapshot(target)==before


def test_foreign_core_source_rejected(client,empty_client,monkeypatch):
    target=fresh(client,empty_client);receipt=register(target)
    def core(*args):
        r=result(args[2]);r['result']['calibration']['uncalibratedSources']=['FOREIGN'];return r
    monkeypatch.setattr(align_preview,'core_run',core)
    with pytest.raises(HTTPException) as error:
        preflight.compute_unreviewed(ctx(target),CASE,RegisteredPreview.model_validate(request(receipt)))
    assert error.value.detail['code']=='TIMELINE_RESULT_REFERENCES'


def test_actual_w2_server_generation(client,empty_client):
    import os
    command=os.getenv('MCIS_PREFLIGHT_REAL_CORE')
    if not command:pytest.skip('set explicit verified real core command')
    target=fresh(client,empty_client);target.app.state.settings.core_cmd=command
    receipt=register(target)
    output=preflight.compute_unreviewed(ctx(target),CASE,RegisteredPreview.model_validate(request(receipt)))
    assert output['serverPreview']['result']['stats']['sourcesImported']==1
    assert output['serverPreview']['result']['stats']['sentencesUsed']==1
    assert output['persisted'] is False


@pytest.mark.parametrize('change',['parent_review','epoch','same_sha_change','access_note'])
def test_remaining_midcompute_boundaries(client,empty_client,monkeypatch,change):
    target=fresh(client,empty_client);receipt=register(target)
    from .test_registered_parent_report import parent,body
    p=parent(target);request_model=RegisteredPreview.model_validate(body(receipt,p))
    def core(*args):
        if change=='parent_review':
            assert target.patch(C+'/evidence/'+p['evidenceId'],headers=H(),json={'needsReview':True,'reason':'test'}).status_code==200
        elif change=='epoch':
            from mcis_service.cases.models import CaseRow
            with target.app.state.db.session() as s:
                row=s.scalars(select(CaseRow).where(CaseRow.case_id==CASE)).one()
                row.doc={**row.doc,'caseEpochUtc':'2026-01-01T00:00:00Z'}
        else:
            from mcis_service.evidence import service
            with target.app.state.db.session() as s:
                service.append_custody(s,case_id=CASE,evidence_id=receipt['evidenceId'],kind='Change' if change=='same_sha_change' else 'Access',operator='test',role='Investigator',sha256=receipt['sourceSha256'],previous_sha256=receipt['sourceSha256'] if change=='same_sha_change' else None,detail='test')
            if change=='access_note':
                assert target.patch(C+'/evidence/'+receipt['evidenceId'],headers=H(),json={'note':'legitimate note'}).status_code==200
        return result(args[2])
    monkeypatch.setattr(align_preview,'core_run',core)
    if change=='access_note':
        answer=preflight.compute_unreviewed(ctx(target),CASE,request_model)
        assert len(answer['generationSnapshot']['sourceIdentities'])==2
        assert answer['generationSnapshot']['reportSnapshots'][0]['relationshipStatus']=='user_declared_not_verified'
    else:
        with pytest.raises(HTTPException) as error:preflight.compute_unreviewed(ctx(target),CASE,request_model)
        assert error.value.status_code==409
