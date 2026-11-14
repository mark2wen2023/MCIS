"""Independent negative tests for reserved history and legacy file side effects."""
import json
import pytest
from fastapi import HTTPException
from .conftest import CASE,H
from .history_result_fixture import marker,value
from .test_unreviewed_history_schema import event,build_package,damage_package
from .test_package import _unzip,_zip,_manifest
from .test_binding_review_independent import snapshot
from mcis_service.timeline import unreviewed_history as history

@pytest.mark.parametrize('token',['NaN','Infinity','-Infinity','1e999'])
def test_nonfinite_reserved_json_rejected(token):
    e=event();e['snapshot_ref']=history.PREFIX+'{"version":'+token+'}'
    with pytest.raises(HTTPException) as error:history.validate_lines([json.dumps(e)],CASE)
    assert error.value.status_code==422

@pytest.mark.parametrize('classification',[{'category':'TimelineUnreviewed'},{'action':'timeline.unreviewed.future'},{'entity_type':'timeline-unreviewed-result'},{'snapshotRef':'local-unreviewed-result:v99:x'}])
def test_reserved_classification_without_canonical_marker_rejected(classification):
    e={'seq':1,'action':'legacy','category':'Case',**classification}
    with pytest.raises(HTTPException):history.validate_lines([json.dumps(e)],CASE)


def test_float_identity_version_and_snapshot_length_rejected():
    for branch,key in [('identity','version'),('snapshot','byteLength')]:
        d=value()
        row=d['generationSnapshot']['sourceIdentities' if branch=='identity' else 'sourceSnapshots'][0]
        row[key]=1.0
        e=event();e['snapshot_ref']=marker(d)
        with pytest.raises(HTTPException):history.declaration(e,CASE)


def test_legacy_invalid_marker_rejects_before_any_supplied_blob_write(client,empty_client,tmp_path):
    from fastapi.testclient import TestClient
    from mcis_service.main import create_app
    from .conftest import make_settings
    bad=damage_package(build_package(client,empty_client),'version')
    files=_unzip(bad);files['raw/review-side-effect.bin']=b'harmless synthetic file'
    del files['manifest.json'];files['manifest.json']=_manifest(CASE,files)
    with TestClient(create_app(make_settings(tmp_path/'destination',seed=False))) as target:
        before=snapshot(target)
        response=target.post('/api/v1/cases:import',headers=H('LeadInvestigator'),content=_zip(files))
        assert response.status_code==422
        assert response.json()['code']=='UNREVIEWED_HISTORY_INVALID'
        assert snapshot(target)==before
        assert not (target.app.state.settings.blob_dir/CASE/'raw/review-side-effect.bin').exists()


def two_sources():
    import copy
    d=value()
    r=copy.deepcopy(d['request']['sources'][0]);r['evidenceId']='EV-901';d['request']['sources'].append(r)
    i=copy.deepcopy(d['generationSnapshot']['sourceIdentities'][0]);i.update(evidenceId='EV-901',incarnation='30000000-0000-4000-8000-000000000002',registeredSeq=2,requestDigest='c'*64,sourceSha256='d'*64)
    d['generationSnapshot']['sourceIdentities'].append(i)
    v=copy.deepcopy(d['generationSnapshot']['sourceSnapshots'][0]);v.update(evidenceId='EV-901',registrationDigest='c'*64,sourceSha256='d'*64)
    d['generationSnapshot']['sourceSnapshots'].append(v)
    return d


def test_duplicate_registration_sequence_rejected_independently():
    d=two_sources();e=event();e['snapshot_ref']=marker(d)
    history.declaration(e,CASE)
    d['generationSnapshot']['sourceIdentities'][1]['registeredSeq']=1
    e['snapshot_ref']=marker(d)
    with pytest.raises(HTTPException):history.declaration(e,CASE)


def test_foreign_case_on_conflict_rejected_independently():
    d=two_sources()
    conflict={'conflictId':'C-01','caseId':CASE,'summary':'synthetic','status':'Open',
              'a':{'sourceLabel':'EV-900','valueText':'45'},'b':{'sourceLabel':'EV-901','valueText':'46'}}
    d['serverPreview']['result']['conflicts']=[conflict]
    e=event();e['snapshot_ref']=marker(d)
    history.declaration(e,CASE)
    conflict['caseId']='CASE-FOREIGN'
    e['snapshot_ref']=marker(d)
    with pytest.raises(HTTPException):history.declaration(e,CASE)
