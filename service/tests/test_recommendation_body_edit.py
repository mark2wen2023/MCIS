"""Real temporary SQLite/API checks; all seed content is fictional Lily/Mary."""
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from .test_recommendations import client as seeded_client, H
from .conftest import C, CASE
from mcis_service.audit import service as audit
from mcis_service.db import get_doc, put_doc
from mcis_service.recommendations.models import RecommendationRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy

RID='SR-2099-99'
URL=f'{C}/recommendations/{RID}/body-edit'


@pytest.fixture
def client(seeded_client):
    result=seeded_client.post(f'{C}/recommendations',json={'id':RID,'title':'虚构编辑测试','body':'旧正文','addressee':'虚构对象','causeNodeIds':['FICTIONAL-NODE'],'dueUtc':'2099-01-01T00:00:00Z'},headers=H())
    assert result.status_code==201
    return seeded_client


def get(client):
    r=client.get(URL,headers=H()); assert r.status_code==200; return r.json()


def save(client, view, body):
    return client.put(URL,json={'expectedVersion':view['version'],'body':body},headers=H())


def lines(client):
    with client.app.state.db.session() as s:return audit.all_lines(s,CASE)


def test_full_body_versions_sources_noop_and_repeat(client):
    before=client.get(f'{C}/recommendations/{RID}',headers=H()).json(); initial=get(client); old=lines(client)
    assert save(client,initial,initial['body']).status_code==200 and lines(client)==old
    text='约 3.4 海里\n<script>literal</script>'+('原文😀'*400)
    response=save(client,initial,text);assert response.status_code==200
    new=response.json();assert new['version']!=initial['version'] and new['body']==text
    assert new['versions'][0]['before']==initial['body'] and new['versions'][0]['after']==text
    assert new['versions'][0]['causeNodeIds']==before['causeNodeIds']
    after=client.get(f'{C}/recommendations/{RID}',headers=H()).json()
    assert {k:v for k,v in before.items() if k not in ('body','updatedUtc')}=={k:v for k,v in after.items() if k not in ('body','updatedUtc')}
    committed=lines(client); assert save(client,initial,text).status_code==409 and lines(client)==committed
    assert save(client,new,text).status_code==200 and lines(client)==committed
    assert json.loads(json.loads(committed[-1])['reason'])['after']==text
    assert audit.verify_chain(committed)['valid']
    assert 'no-store' in response.headers['cache-control']


def test_changed_source_link_and_aba_reject_old_version(client):
    base=get(client)
    for ids in [['NEW-NODE'],base['causeNodeIds']]:
        assert client.patch(f'{C}/recommendations/{RID}',json={'causeNodeIds':ids},headers=H()).status_code==200
    before=lines(client);assert save(client,base,'overwrite').status_code==409 and lines(client)==before


def test_published_and_legacy_body_write_rejected(client):
    base=get(client)
    assert client.patch(f'{C}/recommendations/{RID}',json={'body':'bypass'},headers=H()).status_code==428
    assert client.post(f'{C}/recommendations/{RID}:transition',json={'to':'Issued'},headers=H()).status_code==200
    current=get(client);assert save(client,current,'published').status_code==409
    assert get(client)['body']==base['body']


@pytest.mark.parametrize('data',[{'body':None},{'body':1},{'body':'x'*20001},{'body':'\ud800'},{'body':'ok','extra':True},{'expectedVersion':'wrong','body':'ok'}])
def test_invalid_no_mutation(client,data):
    base=get(client);before=lines(client)
    result=client.put(URL,content=json.dumps({'expectedVersion':base['version'],**data}),headers={**H(),'Content-Type':'application/json'})
    assert result.status_code==422 and lines(client)==before and get(client)==base


def test_revoked_write_and_no_identity_escalation(client):
    base=get(client);before=lines(client)
    for role in ['Investigator','ExternalExpert','Public','AgentService']:
        assert client.put(URL,json={'expectedVersion':base['version'],'body':'no'},headers=H(role)).status_code==403
    policy=default_policy();policy['matrix']['LeadInvestigator']['recommendations']='ReadOnly'
    with client.app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',policy)
    assert save(client,base,'denied').status_code==403 and lines(client)==before


def test_audit_failure_rolls_back_body(client,monkeypatch):
    base=get(client);before=lines(client)
    def fail(*args,**kwargs):raise RuntimeError('private source must not echo')
    monkeypatch.setattr(audit,'append',fail)
    result=save(client,base,'new');assert result.status_code==500 and 'private source' not in result.text
    assert get(client)==base and lines(client)==before


def test_concurrent_same_version_single_winner(client):
    base=get(client);before=lines(client)
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses=list(pool.map(lambda text:save(client,base,text).status_code,['first','second']))
    assert sorted(statuses)==[200,409] and len(lines(client))==len(before)+1
    assert len(get(client)['versions'])==1


def test_clear_preserves_prior_body_and_history_survives_reopen(client):
    base=get(client);new=save(client,base,'must keep '+('文'*500)).json();empty=save(client,new,'').json()
    assert empty['body']=='' and empty['versions'][0]['before']==new['body']
    assert get(client)==empty
    from fastapi.testclient import TestClient
    from mcis_service.main import create_app
    with TestClient(create_app(client.app.state.settings)) as reopened:
        assert get(reopened)==empty


def test_full_history_is_preserved_in_existing_package_export(client):
    from io import BytesIO
    from zipfile import ZipFile
    from mcis_service.cases.models import CaseRow
    isolated='FICTIONAL-BODY-EXPORT'
    with client.app.state.db.session() as s:
        case=get_doc(s,CaseRow,CASE,CASE);case['caseId']=isolated;put_doc(s,CaseRow,isolated,isolated,case)
        rec=get_doc(s,RecommendationRow,CASE,RID);rec['caseId']=isolated;put_doc(s,RecommendationRow,isolated,RID,rec)
    url=f'/api/v1/cases/{isolated}/recommendations/{RID}/body-edit'
    base=client.get(url,headers=H()).json();text='full preserved '+('原文'*700)
    assert client.put(url,json={'expectedVersion':base['version'],'body':text},headers=H()).status_code==200
    response=client.get(f'/api/v1/cases/{isolated}/export',headers=H());assert response.status_code==200
    with ZipFile(BytesIO(response.content)) as archive:
        assert json.loads(archive.read('recommendations.json'))[0]['body']==text
        records=[json.loads(line) for line in archive.read('audit/audit.jsonl').decode().splitlines()]
        full=json.loads(next(row['reason'] for row in records if row['action']=='safetyrec.body_edit'))
        assert full['after']==text and full['before']==base['body'] and full['causeNodeIds']==base['causeNodeIds']
