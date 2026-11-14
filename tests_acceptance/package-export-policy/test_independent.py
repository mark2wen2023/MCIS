"""Independent whole-package policy probes, synthetic local DB and authenticated-role simulation only."""
import io
import json
import zipfile
import pytest
from tests.test_evidence_intake_w42 import local, CASE
from tests.conftest import H
from tests.test_package_export_policy import register, counts, policy, URL, RAW
from mcis_service.db import put_doc
from mcis_service.redaction.policy import default_policy
from mcis_service.redaction.models import AccessPolicyRow


@pytest.mark.parametrize('category',['evidence_meta','audit'])
def test_original_blocker_now_denied_without_payload_or_audit(local,category):
    c,app=local;register(c);policy(c,category);before=counts(app)
    r=c.get(URL+'/export',headers=H())
    assert r.status_code==403 and r.json()['code']=='PACKAGE_CONTENT_FORBIDDEN'
    assert RAW not in r.content and counts(app)==before


@pytest.mark.parametrize('level',['ReadOnly','ReadWrite'])
def test_all_emitted_categories_allow_full_read_levels(local,level):
    from mcis_service.package import mcase
    c,app=local;register(c);p=default_policy()
    for category in ('ais_sim','evidence_meta','audit','timeline','recommendations','agent_drafts'):
        p['matrix']['Investigator'][category]=level
    assert c.put(URL+'/access-policy',headers=H('LeadInvestigator'),json=p).status_code==200
    r=c.get(URL+'/export',headers=H()); assert r.status_code==200,r.text
    files=mcase.read_zip(r.content)
    assert files['evidence/EV-001/source.bin']==RAW and mcase.verify_files(files)['isValid']
    assert json.loads(files['access-policy.json'])['matrix']['Investigator']['evidence_meta']==level


@pytest.mark.parametrize('model_name',['VesselRow','EnvironmentObservationRow','TimelineEventRow','AgentDraftRow'])
def test_embedded_other_case_doc_refuses(local,model_name):
    from mcis_service.cases.models import VesselRow
    from mcis_service.environment.models import EnvironmentObservationRow
    from mcis_service.timeline.models import TimelineEventRow
    from mcis_service.agents.models import AgentDraftRow
    models={m.__name__:m for m in (VesselRow,EnvironmentObservationRow,TimelineEventRow,AgentDraftRow)}
    c,app=local;register(c)
    with app.state.db.session() as s:put_doc(s,models[model_name],CASE,'synthetic',{'caseId':'OTHER-CASE','synthetic':'foreign binding'})
    before=counts(app);r=c.get(URL+'/export',headers=H('LeadInvestigator'))
    assert r.status_code==409 and r.json()['code']=='PACKAGE_CASE_BINDING' and counts(app)==before


def test_trackpoint_embedded_other_case_refuses(local):
    from mcis_service.cases.models import TrackPointRow
    c,app=local;register(c)
    with app.state.db.session() as s:
        s.add(TrackPointRow(case_id=CASE,vessel_id='synthetic-vessel',time_sec=0,
                           doc={'caseId':'OTHER-CASE','timeSec':0,'synthetic':'foreign binding'}))
    before=counts(app);r=c.get(URL+'/export',headers=H('LeadInvestigator'))
    if r.status_code==200:
        files=zipfile.ZipFile(io.BytesIO(r.content))
        payload=json.loads(files.read('derived/tracks/synthetic-vessel.track.json'))
        assert payload['points'][0]['caseId']=='OTHER-CASE'
    assert r.status_code==409, 'TrackPointRow embedded case binding omitted from preflight: '+str(r.status_code)
    assert counts(app)==before


@pytest.mark.parametrize('kind',['unknown','colreg_denied'])
def test_late_member_refusal_rolls_back_prior_export_audit(local,monkeypatch,kind):
    from mcis_service.package import mcase
    c,app=local;register(c)
    if kind=='colreg_denied':policy(c,'colreg')
    original=mcase.build_files
    def build(*args):
        files=original(*args)
        files['analysis/colreg.json' if kind=='colreg_denied' else 'new/unclassified.txt']=b'synthetic hidden body'
        return files
    monkeypatch.setattr(mcase,'build_files',build)
    before=counts(app);r=c.get(URL+'/export',headers=H())
    assert r.status_code==(403 if kind=='colreg_denied' else 409)
    assert b'synthetic hidden body' not in r.content and counts(app)==before


def test_member_check_holds_actual_sqlite_writer(local,monkeypatch):
    import sqlite3
    from mcis_service.package import access
    c,app=local;register(c);original=access.members;observed=[]
    def members(session,*args):
        assert session.connection().connection.driver_connection.in_transaction
        connection=sqlite3.connect(app.state.settings.data_dir/'test.db',timeout=.02)
        try:
            with pytest.raises(sqlite3.OperationalError) as error:connection.execute('BEGIN IMMEDIATE')
            assert error.value.sqlite_errorcode==sqlite3.SQLITE_BUSY
        finally:connection.close()
        observed.append(True)
        return original(session,*args)
    monkeypatch.setattr(access,'members',members)
    r=c.get(URL+'/export',headers=H())
    assert r.status_code==200 and observed==[True]


def test_normal_track_without_embedded_case_remains_compatible(local):
    from mcis_service.cases.models import TrackPointRow
    c,app=local;register(c)
    point={'timeSec':0,'lonDeg':121,'latDeg':31}
    with app.state.db.session() as s:s.add(TrackPointRow(case_id=CASE,vessel_id='synthetic-vessel',time_sec=0,doc=point))
    r=c.get(URL+'/export',headers=H())
    assert r.status_code==200,r.text
    files=zipfile.ZipFile(io.BytesIO(r.content))
    assert json.loads(files.read('derived/tracks/synthetic-vessel.track.json'))['points']==[point]
