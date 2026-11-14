"""Synthetic API workflows with isolated SQLite, not production SSO or real cases."""
import json
import pytest
from .test_evidence_intake_w42 import local
from .test_package_export_policy import register, policy, counts, URL, RAW, LEAD, INV
from .conftest import H
from mcis_service.package import mcase
from mcis_service.redaction.policy import default_policy


def restore(c, blob):
    v=c.post('/api/v1/packages:verify',content=blob,headers=LEAD)
    assert v.status_code==200 and v.json()['isValid']
    r=c.post('/api/v1/cases:import',content=blob,headers=LEAD)
    assert r.status_code==201,r.text


def preserved(c,blob,item):
    files=mcase.read_zip(blob)
    r=c.get(URL+'/evidence/'+item['evidenceId'],headers=LEAD)
    assert r.status_code==200,r.text
    for key in ('caseId','source','extractedBy','extractedUtc','sha256','relativePath','confidentiality','category'):
        assert r.json()[key]==item[key],key
    audit=c.get(URL+'/audit',params={'limit':2000},headers=LEAD).json()
    original=files['audit/audit.jsonl'].decode().splitlines()
    assert [x['line'] for x in audit[:len(original)]]==original
    assert audit[-1]['action']=='package.import'
    assert c.get(URL+'/audit:verify',headers=LEAD).json()['valid']
    assert c.get(URL+'/custody:verify-chain',headers=LEAD).json()['valid']
    assert c.post(URL+'/evidence:verify-all',headers=LEAD).json()['mismatched']==0
    r=c.get(URL+'/evidence/'+item['evidenceId']+'/content',headers=LEAD)
    assert r.status_code==200 and r.content==RAW


@pytest.mark.parametrize('role',['LeadInvestigator','Investigator','ExternalExpert','InterestedState','AgentService','Public'])
@pytest.mark.parametrize('visibility',['Normal','Restricted'])
def test_role_visibility_round_trip(local,empty_client,role,visibility):
    c,app=local;item=register(c,confidentiality=visibility)
    before=counts(app);r=c.get(URL+'/export',headers=H(role))
    if role not in ('LeadInvestigator','Investigator'):
        assert r.status_code==403 and RAW not in r.content and counts(app)==before
        backup=c.get(URL+'/export',headers=LEAD);assert backup.status_code==200
        assert empty_client.post('/api/v1/cases:import',content=backup.content,headers=H(role)).status_code==403
        return
    assert r.status_code==200,r.text
    restore(empty_client,r.content);preserved(empty_client,r.content,item)
    assert empty_client.get(URL+'/export',headers=H(role)).status_code==200
    for other in ('ExternalExpert','InterestedState','AgentService','Public'):
        assert empty_client.get(URL+'/export',headers=H(other)).status_code==403
        if visibility=='Restricted':
            q=empty_client.get(URL+'/evidence/'+item['evidenceId']+'/content',headers=H(other))
            assert q.status_code==403 and RAW not in q.content


@pytest.mark.parametrize('category',['evidence_meta','audit'])
def test_revoke_before_backup_policy_survives_restore(local,empty_client,category):
    c,app=local;item=register(c);p=policy(c,category);before=counts(app)
    assert c.get(URL+'/export',headers=INV).status_code==403 and counts(app)==before
    backup=c.get(URL+'/export',headers=LEAD);assert backup.status_code==200
    assert json.loads(mcase.read_zip(backup.content)['access-policy.json'])==p
    restore(empty_client,backup.content);preserved(empty_client,backup.content,item)
    assert empty_client.get(URL+'/export',headers=INV).status_code==403
    endpoint='/evidence/'+item['evidenceId']+'/content' if category=='evidence_meta' else '/audit'
    r=empty_client.get(URL+endpoint,headers=INV)
    assert r.status_code==403 and RAW not in r.content


def test_restricted_field_rule_survives_restore(local,empty_client):
    c,_=local;item=register(c,confidentiality='Restricted');p=default_policy()
    p['fieldRules'][-1]['appliesTo'].append('Investigator')
    assert c.put(URL+'/access-policy',json=p,headers=LEAD).status_code==200
    assert c.get(URL+'/export',headers=INV).status_code==403
    backup=c.get(URL+'/export',headers=LEAD);assert backup.status_code==200
    restore(empty_client,backup.content);preserved(empty_client,backup.content,item)
    assert empty_client.get(URL+'/evidence',headers=INV).json()==[]
    assert empty_client.get(URL+'/evidence/'+item['evidenceId']+'/content',headers=INV).status_code==403
    assert empty_client.get(URL+'/export',headers=INV).status_code==403


def test_destination_revoke_after_restore(local,empty_client):
    c,_=local;item=register(c);backup=c.get(URL+'/export',headers=INV)
    assert backup.status_code==200
    restore(empty_client,backup.content);preserved(empty_client,backup.content,item)
    policy(empty_client,'evidence_meta')
    assert empty_client.get(URL+'/export',headers=INV).status_code==403
    assert empty_client.get(URL+'/evidence/'+item['evidenceId']+'/content',headers=INV).status_code==403
    assert empty_client.post('/api/v1/cases:import',content=backup.content,headers=INV).status_code==409
    assert empty_client.get(URL+'/export',headers=INV).status_code==403


def test_source_later_revoke_does_not_revoke_offline_backup(local,empty_client):
    """Documented limitation, not an assertion of global revocation security."""
    c,_=local;item=register(c);backup=c.get(URL+'/export',headers=INV)
    assert backup.status_code==200
    policy(c,'evidence_meta');assert c.get(URL+'/export',headers=INV).status_code==403
    restore(empty_client,backup.content);preserved(empty_client,backup.content,item)
    old=empty_client.get(URL+'/evidence/'+item['evidenceId']+'/content',headers=INV)
    assert old.status_code==200 and old.content==RAW
    assert empty_client.get(URL+'/export',headers=INV).status_code==200


def test_source_hidden_restricted_content_is_denied(local):
    """Same expected denial before restore: distinguish inherited GET flaw from restore."""
    c,app=local;item=register(c,confidentiality='Restricted');p=default_policy()
    p['fieldRules'][-1]['appliesTo'].append('Investigator')
    assert c.put(URL+'/access-policy',json=p,headers=LEAD).status_code==200
    assert c.get(URL+'/evidence',headers=INV).json()==[]
    assert c.get(URL+'/evidence/'+item['evidenceId'],headers=INV).status_code==403
    assert c.get(URL+'/export',headers=INV).status_code==403
    before=counts(app)
    r=c.get(URL+'/evidence/'+item['evidenceId']+'/content',headers=INV)
    print(json.dumps({'stage':'source-before-export','status':r.status_code,
                      'matches_synthetic_original':r.content==RAW,'audit_delta':counts(app)-before}))
    assert r.status_code==403 and RAW not in r.content


@pytest.mark.parametrize('level',['ReadOnly','Redacted'])
def test_vdr_policy_roundtrip(local,empty_client,level):
    c,_=local;item=register(c,category='VDR');policy(c,'vdr_audio',level)
    r=c.get(URL+'/export',headers=INV)
    assert r.status_code==(200 if level=='ReadOnly' else 403)
    backup=c.get(URL+'/export',headers=LEAD);assert backup.status_code==200
    restore(empty_client,backup.content);preserved(empty_client,backup.content,item)
    assert empty_client.get(URL+'/export',headers=INV).status_code==(200 if level=='ReadOnly' else 403)
