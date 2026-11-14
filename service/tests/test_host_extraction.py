import json
import pytest
from fastapi import HTTPException
from .test_agents_w20 import interview as build_interview,RECORD,ITEM,QUOTE
from .test_local_authority import provision
from .conftest import CASE
from mcis_service.agents import host_extraction as h,model_client
from mcis_service.identity import local

@pytest.fixture
def extraction_case(client,empty_client,monkeypatch):
    from .test_internal_unreviewed_save import setup
    client,_,_=setup(client,empty_client,monkeypatch)
    build_interview.__wrapped__(client)
    _,token=provision(client)
    args=(client.app.state.db,client.app.state.settings,token,CASE,RECORD)
    return args,h.describe(*args)['bindingDigest']


def test_disabled_even_when_environment_configured(extraction_case,monkeypatch):
    args,binding=extraction_case
    monkeypatch.setenv('MCIS_AGENT_BASE_URL','http://127.0.0.1:12345/v1');monkeypatch.setenv('MCIS_AGENT_MODEL','not-opted-in')
    monkeypatch.setattr(model_client,'complete',lambda *a:pytest.fail('no implicit inference'))
    result=h.run(*args,binding);assert result['status']=='not_connected' and not result['inferencePerformed'] and result['proposals']==[]


def test_fixture_exact_quote_unreviewed_no_writes(extraction_case):
    args,binding=extraction_case
    from sqlalchemy import text
    def counts():
        with args[0].engine.connect() as c:return {name:c.execute(text('select count(*) from "'+name+'"')).scalar() for name in c.execute(text("select name from sqlite_master where type='table'")).scalars()}
    before=counts();result=h.run(*args,binding,h.FixtureProvider(json.dumps({'statements':[ITEM]})))
    assert result['status']=='PendingReview' and result['fixture'] and not result['inferencePerformed'] and not result['saved']
    assert result['proposals'][0]['reviewStatus']=='Draft' and result['citations'][0]['quote']==QUOTE
    assert result['receipt']['sourceScope']=='interview_document_only' and not result['receipt']['persistentAudit'] and not result['receipt']['signature']
    assert counts()==before and args[2] not in json.dumps(result)


def test_local_provider_redacted_messages_with_mock_not_real_inference(extraction_case,monkeypatch):
    args,binding=extraction_case;seen=[]
    def fake(cfg,messages):seen.append(messages);return json.dumps({'statements':[ITEM]})
    monkeypatch.setattr(model_client,'complete',fake)
    result=h.run(*args,binding,h.LocalProvider(model_client.ModelConfig('http://127.0.0.1:12345/v1','test-mock')))
    assert result['receipt']['providerMode']=='local' and seen
    sent=json.dumps(seen,ensure_ascii=False)
    assert '13812345678' not in sent and '私人片段' not in sent and '测试甲' not in sent and args[2] not in sent
    # This test mocks complete; no actual model inference is claimed by test evidence.

@pytest.mark.parametrize('url',['https://example.com/v1','http://example.com/v1','http://127.0.0.1:80/v1?x=1','http://u:p@127.0.0.1:80/v1'])
def test_local_config_rechecked_at_call(extraction_case,monkeypatch,url):
    args,binding=extraction_case
    monkeypatch.setattr(model_client,'complete',lambda *a:pytest.fail('bad endpoint must never be contacted'))
    with pytest.raises(HTTPException):h.run(*args,binding,h.LocalProvider(model_client.ModelConfig(url,'test')))

@pytest.mark.parametrize('content',['{}','{"statements":[],"statements":[]}', 'x'*(h.MAX_OUTPUT+1),json.dumps({'statements':[{**ITEM,'quote':'invented'}]})])
def test_bad_output_no_proposals(extraction_case,content):
    args,binding=extraction_case
    with pytest.raises(HTTPException) as e:h.run(*args,binding,h.FixtureProvider(content))
    assert e.value.status_code==502 and 'invented' not in str(e.value.detail)


def test_revoked_during_provider_no_return(extraction_case,monkeypatch):
    args,binding=extraction_case
    def revoked(self,messages):
        with args[0].session() as s:local.revoke_session(s,args[2])
        return json.dumps({'statements':[ITEM]})
    monkeypatch.setattr(h.FixtureProvider,'complete',revoked)
    with pytest.raises(HTTPException) as e:h.run(*args,binding,h.FixtureProvider('unused'))
    assert e.value.status_code==403


def test_binding_mismatch_before_provider(extraction_case,monkeypatch):
    args,_=extraction_case
    monkeypatch.setattr(h.FixtureProvider,'complete',lambda *a:pytest.fail('binding mismatch must not infer'))
    with pytest.raises(HTTPException) as e:h.run(*args,'0'*64,h.FixtureProvider('unused'))
    assert e.value.status_code==409


def test_registered_original_binding_and_changed_bytes(extraction_case):
    args,_=extraction_case
    from sqlalchemy import select
    from mcis_service.interviews.models import InterviewRow
    from mcis_service.evidence_intake.incarnation import SourceIncarnationRow
    from mcis_service.evidence.models import EvidenceRow
    with args[0].session() as s:
        source=s.scalars(select(SourceIncarnationRow).where(SourceIncarnationRow.case_id==CASE)).first()
        row=s.scalars(select(InterviewRow).where(InterviewRow.case_id==CASE,InterviewRow.key==RECORD)).one()
        row.doc={**row.doc,'evidenceId':source.evidence_id,'sourceSha256':source.source_sha256}
        evidence=s.scalars(select(EvidenceRow).where(EvidenceRow.case_id==CASE,EvidenceRow.key==source.evidence_id)).one().doc
        relative=evidence['relativePath']
    descriptor=h.describe(*args);assert descriptor['sourceScope']=='registered_original_bytes'
    result=h.run(*args,descriptor['bindingDigest'],h.FixtureProvider(json.dumps({'statements':[ITEM]})))
    assert result['receipt']['sourceScope']=='registered_original_bytes'
    (args[1].blob_dir/CASE/relative).write_bytes(b'changed-original')
    with pytest.raises(HTTPException):h.run(*args,descriptor['bindingDigest'],h.FixtureProvider(json.dumps({'statements':[ITEM]})))


def test_whitespace_model_rejected(extraction_case,monkeypatch):
    args,binding=extraction_case
    monkeypatch.setattr(model_client,'complete',lambda *a:pytest.fail('empty model must not be contacted'))
    with pytest.raises(HTTPException):h.run(*args,binding,h.LocalProvider(model_client.ModelConfig('http://127.0.0.1:12345/v1','   ')))
