"""Protect injected synthetic history before any result storage is enabled."""
import json
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from .conftest import C,CASE,H,make_settings
from .test_source_incarnation import fresh
from .test_registered_align_preview import register
from .history_result_fixture import inject_valid_history
from .test_archive_generation_boundary import upload
from mcis_service.main import create_app
from mcis_service.audit import service as audit
from mcis_service.timeline import unreviewed_access as boundary

SECRET='synthetic-derived-content-not-for-audit-only-role'


def inject(client,variant='marker'):
    with client.app.state.db.session() as s:
        event=audit.append(s,case_id=CASE,operator='test',role='LeadInvestigator',
            action='timeline.unreviewed.save' if variant=='action' else 'legacy.import',
            category='TimelineUnreviewed' if variant=='category' else 'Case',
            command='synthetic historical fixture',
            entity_type='timeline-unreviewed-result' if variant=='entity' else 'case',entity_id=CASE,
            snapshot_ref=('local-unreviewed-result:v1:' if variant=='marker' else '')+SECRET)
        return event.seq


def deny_evidence(client):
    from mcis_service.redaction.policy import default_policy
    p=default_policy();p['matrix']['Investigator']['audit']='ReadOnly';p['matrix']['Investigator']['evidence_meta']='Deny'
    assert client.put(C+'/access-policy',headers=H('LeadInvestigator'),json=p).status_code==200


@pytest.mark.parametrize('variant',['marker','action','category','entity'])
def test_audit_and_export_do_not_leak_to_audit_only_role(client,empty_client,variant):
    target=fresh(client,empty_client);seq=inject(target,variant);deny_evidence(target)
    for suffix in ['/audit','/audit?afterSeq='+str(seq-1)+'&limit=1','/audit?category='+('TimelineUnreviewed' if variant=='category' else 'Case'),'/export']:
        response=target.get(C+suffix,headers=H())
        assert response.status_code==403,response.text
        assert SECRET not in response.text
    full=target.get(C+'/audit',headers=H('LeadInvestigator'))
    assert full.status_code==200 and SECRET in full.text


@pytest.mark.parametrize('raw',[
 {'snapshot_ref':'local-unreviewed-result:v99:bad','category':'Case'},
 {'snapshot_ref':'local-unreviewed-resultmalformed'},
 {'snapshotRef':'benign','snapshot_ref':'local-unreviewed-result:v1:x'},
 {'entityType':'case','entity_type':'timeline-unreviewed-result'},
])
def test_raw_marker_cannot_hide_behind_projected_fields(raw):
    assert boundary.related({'category':'Case','snapshotRef':'benign','line':json.dumps(raw)})
    assert boundary.related(raw)


@pytest.mark.parametrize('line',['{bad','{"snapshot_ref":"local-unreviewed-result:v1:x","snapshot_ref":"benign"}','[]','{"x":NaN}'])
def test_malformed_raw_fails_closed(line):
    assert boundary.related({'category':'Case','line':line})


@pytest.mark.parametrize('modern',[False,True])
def test_imported_history_has_no_index_but_remains_protected(client,empty_client,tmp_path,modern):
    target=fresh(client,empty_client)
    if modern:register(target)
    inject_valid_history(target)
    package=target.get(C+'/export',headers=H('LeadInvestigator'));assert package.status_code==200,package.text
    with TestClient(create_app(make_settings(tmp_path/'restored',seed=False))) as restored:
        response=upload(restored,package.content) if modern else restored.post('/api/v1/cases:import',headers=H('LeadInvestigator'),content=package.content)
        assert response.status_code in (200,201),response.text
        # Roundtrip supported default policy first; modern archive parser has
        # an existing non-default-policy restriction, not widened here.
        roundtrip=restored.get(C+'/export',headers=H('LeadInvestigator'))
        assert roundtrip.status_code==200,roundtrip.text
        deny_evidence(restored)
        assert restored.get(C+'/audit',headers=H()).status_code==403
        data=restored.get(C+'/audit',headers=H('LeadInvestigator'))
        assert data.status_code==200 and 'local-unreviewed-result:v1:' in data.text
        assert restored.get(C+'/export',headers=H()).status_code==403
        export=restored.get(C+'/export',headers=H('LeadInvestigator'))
        assert export.status_code==(409 if modern else 200),export.text
        if modern:assert export.json()['code']=='ARCHIVE_RESTORE_UNSUPPORTED'


def test_capacity_counts_actual_escaped_utf8_and_newlines(monkeypatch):
    monkeypatch.setattr(boundary,'MAX_AUDIT_MEMBER_BYTES',100)
    monkeypatch.setattr(boundary,'EXPORT_HEADROOM_BYTES',10)
    assert boundary.ensure_archive_capacity(['a'*44],'b'*44)==90
    with pytest.raises(HTTPException) as e:boundary.ensure_archive_capacity(['a'*44],'b'*45)
    assert e.value.status_code==413
    encoded=json.dumps({'snapshot_ref':'"\\'*20},ensure_ascii=False)
    assert len(encoded)>80
    with pytest.raises(HTTPException):boundary.ensure_archive_capacity(['older-audit'],encoded)
    with pytest.raises(HTTPException):boundary.ensure_archive_capacity([], '\ud800')


def test_unrelated_audit_not_escalated(client,empty_client):
    target=fresh(client,empty_client);deny_evidence(target)
    assert target.get(C+'/audit?action=case.create',headers=H()).status_code==200


def test_access_workbench_cannot_leak_disguised_result(client,empty_client):
    target=fresh(client,empty_client)
    with target.app.state.db.session() as s:
        audit.append(s,case_id=CASE,operator='test',role='LeadInvestigator',action='policy.update',category='Access',command='synthetic imported masquerade',entity_type='accessPolicy',entity_id='policy',snapshot_ref='local-unreviewed-result:v1:'+SECRET)
    deny_evidence(target)
    response=target.get(C+'/access-workbench',headers=H())
    assert response.status_code==403 and SECRET not in response.text
    response=target.get(C+'/access-workbench',headers=H('LeadInvestigator'))
    assert response.status_code==200 and SECRET in response.text
