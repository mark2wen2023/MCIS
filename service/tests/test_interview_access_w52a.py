"""Synthetic security regressions; raw markers never represent a real witness."""
import copy
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import select,func
from mcis_service.db import put_doc
from mcis_service.interviews.models import InterviewRow
from mcis_service.audit.models import AuditEventRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import CATEGORIES, default_policy
from mcis_service.interviews import access
from .w52_synthetic_support import client,doc,CASE,BASE,MARK
from .conftest import H
LEAD=H('LeadInvestigator')

def seed(client,signed=False):
    d=doc();d['signed']=signed;d.pop('evidenceId');d.pop('sourceSha256')
    with client.app.state.db.session() as s:put_doc(s,InterviewRow,CASE,'IR-01',d)
    return d

def count(client):
    with client.app.state.db.session() as s:return s.scalar(select(func.count()).select_from(AuditEventRow))

@pytest.mark.parametrize('role',['Investigator','ExternalExpert','AgentService','Public','InterestedState'])
def test_all_original_outputs_denied(client,role):
    seed(client)
    before=count(client)
    for path in ['/interviews','/interviews/IR-01','/interviews/IR-01/crosscheck','/interview-compare','/interview-compare/IR-01','/agents/inputs/interviews/IR-01','/export']:
        r=client.get(BASE+path,headers=H(role))
        assert r.status_code==403,(path,r.text)
        assert MARK not in r.text and r.headers['cache-control']=='no-store'
    r=client.post(BASE+'/redaction/preview',headers=H(role),json={'role':'LeadInvestigator','recordId':'IR-01'})
    assert r.status_code==403 and MARK not in r.text
    assert count(client)==before

@pytest.mark.parametrize('field,value',[('signed',True),('turns',[{'round':1,'question':'q','answer':'a'}]),('crossChecks',doc()['crossChecks']),('sourceSha256','injected')])
def test_create_injection_refused(client,field,value):
    body=doc();body.update(signed=False,turns=[],crossChecks=[]);body.pop('sourceSha256');body.pop('evidenceId');body[field]=value
    r=client.post(BASE+'/interviews',headers=LEAD,json=body)
    assert r.status_code==422 and count(client)==0


def test_unsigned_create_append_reopen_and_concurrent_no_loss(client):
    body=doc();body.update(signed=False,turns=[],crossChecks=[]);body.pop('sourceSha256');body.pop('evidenceId')
    assert client.post(BASE+'/interviews',headers=LEAD,json=body).status_code==201
    def append(q):return client.post(BASE+'/interviews/IR-01/turns',headers=LEAD,json={'question':q,'answer':'Synthetic '+q})
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(append,['A','B']))
    assert [r.status_code for r in results]==[201,201]
    r=client.get(BASE+'/interviews/IR-01',headers=LEAD)
    assert r.status_code==200
    assert {t['question'] for t in r.json()['turns']}=={'A','B'}
    assert [t['round'] for t in r.json()['turns']]==[1,2]


def test_signed_mutations_refused(client):
    seed(client,signed=True);before=count(client)
    r=client.post(BASE+'/interviews/IR-01/turns',headers=LEAD,json={'question':'q','answer':'a'})
    assert r.status_code==409 and r.json()['code']=='INTERVIEW_SIGNED'
    r=client.post(BASE+'/interview-compare/IR-01/rows/IR-01-S01:confirm',headers=LEAD,json={})
    assert r.status_code==409 and r.json()['code']=='INTERVIEW_SIGNED'
    assert count(client)==before

@pytest.mark.parametrize('category',CATEGORIES)
def test_all_categories_fail_closed(client,category):
    seed(client);p=default_policy();p['matrix']['LeadInvestigator'][category]='Deny'
    with client.app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',p)
    r=client.get(BASE+'/interviews/IR-01',headers=LEAD)
    assert r.status_code==403 and MARK not in r.text


def test_source_unregistered_and_hash_conflict(client):
    from mcis_service.evidence.models import EvidenceRow
    d=seed(client);d['evidenceId']='EV-1';d['sourceSha256']='a'*64
    with client.app.state.db.session() as s:put_doc(s,InterviewRow,CASE,'IR-01',d)
    assert client.get(BASE+'/interviews/IR-01',headers=LEAD).status_code==403
    with client.app.state.db.session() as s:put_doc(s,EvidenceRow,CASE,'EV-1',{'evidenceId':'EV-1','caseId':CASE,'sha256':'b'*64,'confidentiality':'Normal'})
    assert client.get(BASE+'/interviews/IR-01',headers=LEAD).status_code==409


def test_interview_audit_only_is_protected(client):
    from mcis_service.audit.service import append
    with client.app.state.db.session() as s:append(s,case_id=CASE,operator='Synthetic',role='LeadInvestigator',action='statement.add',category='Interview',command='synthetic',after=MARK)
    before=count(client)
    for path in ['/audit','/export']:
        r=client.get(BASE+path,headers=H());assert r.status_code==403 and MARK not in r.text
    assert count(client)==before


def test_agent_payload_and_citation_paths_gate(client):
    from mcis_service.agents.models import AgentDraftRow
    d=seed(client)
    for payload,citations in [({'recordId':'IR-01'},[]), ({},[{'recordId':'IR-01','quote':MARK}]), ({'span':{'round':1}},[])]:
        draft={'draftId':'AD-001','caseId':CASE,'targetEntityType':'other','kind':'other','status':'PendingReview','payload':payload,'citations':citations}
        with client.app.state.db.session() as s:put_doc(s,AgentDraftRow,CASE,'AD-001',draft)
        r=client.get(BASE+'/agents/drafts',headers=H())
        assert r.status_code==403 and MARK not in r.text


def test_package_rejects_transcript_and_residual_audit_before_writes(client):
    import io,json,zipfile
    from mcis_service.package.mcase import manifest_json
    from mcis_service.audit.service import build_line
    for extra in [{'testimony/IR-01.json':json.dumps(doc()).encode()}, {'audit/audit.jsonl':build_line(utc='2026-01-01T00:00:00Z',operator='synthetic',action='statement.add',category='Interview',command=MARK,before='',after='',seq=1,role='LeadInvestigator',entity_type='statement',entity_id='S1',prev='0'*64).encode()}]:
        files={'case.json':json.dumps({'caseId':CASE}).encode(),**extra}
        files['manifest.json']=manifest_json(CASE,files,'2026-01-01T00:00:00Z').encode()
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w') as z:
            for path,data in files.items():z.writestr(path,data)
        before=count(client)
        r=client.post('/api/v1/cases:import',headers=LEAD,content=output.getvalue())
        assert r.status_code==422 and r.json()['code']=='INTERVIEW_IMPORT_UNSUPPORTED',r.text
        assert count(client)==before


def test_failed_append_rolls_back_and_does_not_echo(client,monkeypatch):
    from mcis_service.interviews import router
    seed(client);before=count(client)
    def fail(*a,**kw):raise RuntimeError(MARK)
    monkeypatch.setattr(router.audit,'append',fail)
    r=client.post(BASE+'/interviews/IR-01/turns',headers=LEAD,json={'question':'q','answer':'new'})
    assert r.status_code==500 and MARK not in r.text and r.headers['cache-control']=='no-store'
    assert count(client)==before
    with client.app.state.db.session() as s:
        d=s.scalars(select(InterviewRow).where(InterviewRow.case_id==CASE)).one().doc
        assert len(d['turns'])==1


def test_local_model_stub_preserves_mandatory_egress_and_apply(client,monkeypatch):
    import json
    from mcis_service.agents import model_client
    d=seed(client);d['turns'][0]['answer']='Synthetic observable '+MARK
    with client.app.state.db.session() as s:put_doc(s,InterviewRow,CASE,'IR-01',d)
    monkeypatch.setenv('MCIS_AGENT_BASE_URL','http://127.0.0.1:12345/v1')
    monkeypatch.setenv('MCIS_AGENT_MODEL','synthetic-stub-not-real-model')
    calls=[]
    def complete(cfg,messages):
        calls.append(messages)
        assert MARK not in json.dumps(messages)
        return json.dumps({'statements':[{'kind':'Observation','subject':'synthetic','summary':'Synthetic only','claim':{'valueType':'Occurrence','occurred':True},'round':1,'field':'Answer','quote':'Synthetic observable'}]})
    monkeypatch.setattr(model_client,'complete',complete)
    url=BASE+'/agents/people_ops/interviews/IR-01:extract'
    assert client.post(url,headers=H('AgentService')).status_code==403
    assert not calls
    r=client.post(url,headers=LEAD)
    assert r.status_code==201,r.text
    assert len(calls)==1
    r=client.post(BASE+'/agents/drafts/'+r.json()['draftId']+'/review',headers=LEAD,json={'decision':'Confirmed'})
    assert r.status_code==200,r.text
    assert client.get(BASE+'/interviews/IR-01',headers=LEAD).json()['statements'][0]['extractedBy']=='Agent'


def test_unknown_start_time_not_invented(client):
    body=doc();body.update(signed=False,turns=[],crossChecks=[])
    for key in ('sourceSha256','evidenceId','startUtc'):body.pop(key)
    r=client.post(BASE+'/interviews',headers=LEAD,json=body)
    assert r.status_code==422 and count(client)==0


def test_final_modified_agent_payload_cannot_change_source_scope(client):
    from mcis_service.agents.models import AgentDraftRow
    d=seed(client)
    # Previously unrelated generic draft becomes interview-bearing only in final payload.
    draft={'draftId':'AD-001','caseId':CASE,'agent':'aggregate','targetEntityType':'other','kind':'other','status':'PendingReview','payload':{},'citations':[{'quote':'Synthetic'}], 'createdUtc':'2026-01-01T00:00:00Z'}
    with client.app.state.db.session() as s:put_doc(s,AgentDraftRow,CASE,'AD-001',draft)
    before=count(client)
    r=client.post(BASE+'/agents/drafts/AD-001/review',headers=H(),json={'decision':'Modified','payload':{'recordId':'IR-01'},'note':'Synthetic'})
    assert r.status_code==403 and count(client)==before
    with client.app.state.db.session() as s:
        assert s.scalars(select(AgentDraftRow)).one().doc['status']=='PendingReview'


def test_model_call_does_not_hold_database_writer_and_revoked_result_discarded(client,monkeypatch):
    import json
    from mcis_service.agents import model_client
    from mcis_service.agents.models import AgentDraftRow
    seed(client)
    monkeypatch.setenv('MCIS_AGENT_BASE_URL','http://127.0.0.1:12345/v1')
    monkeypatch.setenv('MCIS_AGENT_MODEL','synthetic-stub-not-real-model')
    committed=[]
    def complete(cfg,messages):
        # A distinct connection must commit while the model is running. A long
        # BEGIN IMMEDIATE here would raise SQLite locked, causing this test to fail.
        p=default_policy();p['matrix']['LeadInvestigator']['testimony']='Deny'
        with client.app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',p)
        committed.append(True)
        return json.dumps({'statements':[]})
    monkeypatch.setattr(model_client,'complete',complete)
    r=client.post(BASE+'/agents/people_ops/interviews/IR-01:extract',headers=LEAD)
    assert committed==[True]
    assert r.status_code==403 and MARK not in r.text
    with client.app.state.db.session() as s:
        assert s.scalar(select(func.count()).select_from(AgentDraftRow))==0
        events=list(s.scalars(select(AuditEventRow)))
        assert [e.action for e in events]==['agent.run.started']


def test_model_result_discarded_if_source_changes_during_call(client,monkeypatch):
    import json
    from mcis_service.agents import model_client
    from mcis_service.agents.models import AgentDraftRow
    seed(client)
    monkeypatch.setenv('MCIS_AGENT_BASE_URL','http://127.0.0.1:12345/v1')
    monkeypatch.setenv('MCIS_AGENT_MODEL','synthetic-stub-not-real-model')
    def complete(cfg,messages):
        with client.app.state.db.session() as s:
            row=s.scalars(select(InterviewRow)).one();d=copy.deepcopy(row.doc)
            d['turns'][0]['answer']='Synthetic changed source';row.doc=d
        return json.dumps({'statements':[]})
    monkeypatch.setattr(model_client,'complete',complete)
    r=client.post(BASE+'/agents/people_ops/interviews/IR-01:extract',headers=LEAD)
    assert r.status_code==409,r.text
    assert r.json()['code']=='INTERVIEW_CHANGED'
    with client.app.state.db.session() as s:assert s.scalar(select(func.count()).select_from(AgentDraftRow))==0
