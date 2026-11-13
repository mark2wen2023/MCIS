import copy
import hashlib
import json
import uuid
import pytest
from fastapi import HTTPException
from .conftest import C,CASE,H
from .test_source_incarnation import fresh
from .history_result_fixture import value,marker,inject_valid_history,RUN,STAMP
from .test_package import _zip,_unzip,_manifest
from .test_archive_generation_boundary import upload
from .test_binding_review_independent import snapshot
from mcis_service.timeline import unreviewed_history as history


def event(d=None):
    return {'seq':1,'utc':STAMP,'action':'timeline.unreviewed.save','category':'TimelineUnreviewed','entity_type':'timeline-unreviewed-result','entity_id':RUN,'snapshot_ref':marker(d)}


def test_schema_accepts_only_history_without_authority():
    d=history.declaration(event(),CASE)
    assert d['status']=='unreviewed' and d['serverPreview']['persisted'] is False


@pytest.mark.parametrize('bad',['unknown_version','duplicate_key','nan','depth','foreign_case','false_approval','source_digest','source_set','parent_set','foreign_result','bool_version','extra','metadata','duplicate_run','inner_case','inner_epoch','float_version','float_seq','import_error','surrogate'])
def test_invalid_declarations_reject(bad):
    d=value();e=event()
    if bad=='unknown_version':e['snapshot_ref']=e['snapshot_ref'].replace(':v1:',':v2:')
    elif bad=='duplicate_key':e['snapshot_ref']=history.PREFIX+'{"version":1,"version":1}'
    elif bad=='nan':e['snapshot_ref']=history.PREFIX+'{"x":NaN}'
    elif bad=='depth':e['snapshot_ref']=history.PREFIX+'['*40+'0'+']'*40
    elif bad=='foreign_case':d['caseId']='CASE-FOREIGN'
    elif bad=='false_approval':d['status']='approved'
    elif bad=='source_digest':d['generationSnapshot']['sourceSnapshots'][0]['registrationDigest']='c'*64
    elif bad=='source_set':d['generationSnapshot']['sourceIdentities']=[]
    elif bad=='parent_set':d['generationSnapshot']['reportSnapshots']=[{}]
    elif bad=='foreign_result':d['serverPreview']['result']['calibration']['uncalibratedSources']=['FOREIGN']
    elif bad=='bool_version':d['version']=True
    elif bad=='surrogate':d['serverPreview']['result']['calibration']['error']='\ud800'
    elif bad=='inner_case':d['serverPreview']['result']['caseId']='CASE-FOREIGN'
    elif bad=='inner_epoch':d['serverPreview']['result']['caseEpochUtc']='2020-01-01T00:00:00Z'
    elif bad=='float_version':d['version']=1.0
    elif bad=='float_seq':d['generationSnapshot']['sourceIdentities'][0]['registeredSeq']=1.0
    elif bad=='import_error':d['serverPreview']['result']['importDiagnostics']=[{'sourceId':'EV-900','severity':'Error','lineNumber':1,'code':'bad','message':'not usable'}]
    elif bad=='extra':d['approved']=True
    elif bad=='metadata':e['entity_id']=str(uuid.uuid4())
    if bad not in ('unknown_version','duplicate_key','nan','depth','metadata'):e['snapshot_ref']=marker(d)
    lines=[json.dumps(e)]
    if bad=='duplicate_run':lines.append(json.dumps({**e,'seq':2}))
    with pytest.raises(HTTPException) as error:history.validate_lines(lines,CASE)
    assert error.value.status_code==422


def test_capacity_and_line_separator_rejected(monkeypatch):
    monkeypatch.setattr(history,'MAX_BYTES',100)
    with pytest.raises(HTTPException):history.declaration(event(),CASE)
    monkeypatch.setattr(history,'MAX_BYTES',2*1024*1024)
    e=event();e['snapshot_ref']+='\u2028'
    with pytest.raises(HTTPException):history.declaration(e,CASE)


def test_reserved_shadowing_and_unrelated_legacy():
    e=event();line=json.dumps(e)[:-1]+',"snapshot_ref":"benign"}'
    with pytest.raises(HTTPException):history.validate_lines([line],CASE)
    history.validate_lines([json.dumps({'category':'Case','action':'case.create','snapshot_ref':'unrelated legacy text'})],CASE)


def build_package(client,empty_client):
    target=fresh(client,empty_client);inject_valid_history(target)
    response=target.get(C+'/export',headers=H('LeadInvestigator'))
    assert response.status_code==200,response.text
    return response.content


def damage_package(raw,mutation):
    files=_unzip(raw);lines=[json.loads(x) for x in files['audit/audit.jsonl'].decode().splitlines()]
    row=next(x for x in lines if x.get('snapshot_ref','').startswith(history.PREFIX))
    if mutation=='version':row['snapshot_ref']=row['snapshot_ref'].replace(':v1:',':v2:')
    if mutation=='metadata':row['category']='Case'
    if mutation=='missing':del row['snapshot_ref']
    if mutation=='shadow':row['snapshotRef']='benign'
    if mutation=='repeat':lines.append(copy.deepcopy(row))
    prev='0'*64;encoded=[]
    for index,r in enumerate(lines,1):
        r['seq']=index;r['prev']=prev
        line=json.dumps(r,ensure_ascii=True,separators=(',',':'))
        prev=hashlib.sha256(line.encode()).hexdigest();encoded.append(line)
    files['audit/audit.jsonl']=('\n'.join(encoded)+'\n').encode()
    del files['manifest.json'];files['manifest.json']=_manifest(CASE,files)
    return _zip(files)


@pytest.mark.parametrize('modern',[False,True])
@pytest.mark.parametrize('mutation',['version','metadata','missing','shadow','repeat'])
def test_both_import_entries_reject_before_db_or_file_writes(client,empty_client,tmp_path,modern,mutation):
    from fastapi.testclient import TestClient
    from mcis_service.main import create_app
    from .conftest import make_settings
    raw=damage_package(build_package(client,empty_client),mutation)
    with TestClient(create_app(make_settings(tmp_path/'target',seed=False))) as target:
        before=snapshot(target)
        response=upload(target,raw) if modern else target.post('/api/v1/cases:import',headers=H('LeadInvestigator'),content=raw)
        assert response.status_code==422,response.text
        assert response.json()['code']=='UNREVIEWED_HISTORY_INVALID',response.text
        assert snapshot(target)==before
        assert not (target.app.state.settings.blob_dir/CASE).exists()


@pytest.mark.parametrize('modern',[False,True])
def test_valid_history_roundtrip_is_exact_and_never_live(client,empty_client,tmp_path,modern):
    from fastapi.testclient import TestClient
    from sqlalchemy import inspect
    from mcis_service.main import create_app
    from .conftest import make_settings
    raw=build_package(client,empty_client)
    with TestClient(create_app(make_settings(tmp_path/'target',seed=False))) as target:
        response=upload(target,raw) if modern else target.post('/api/v1/cases:import',headers=H('LeadInvestigator'),content=raw)
        assert response.status_code in (200,201),response.text
        with target.app.state.db.session() as s:
            # The new local index table exists in the application schema, but
            # historical imports must never populate it.
            from sqlalchemy import select,func
            from mcis_service.timeline.unreviewed_storage import UnreviewedRunRow
            assert s.scalar(select(func.count()).select_from(UnreviewedRunRow))==0
        again=target.get(C+'/export',headers=H('LeadInvestigator'));assert again.status_code==200,again.text
        records=[json.loads(x) for x in _unzip(again.content)['audit/audit.jsonl'].decode().splitlines()]
        saved=[r['snapshot_ref'] for r in records if r.get('snapshot_ref','').startswith(history.PREFIX)]
        assert saved==[marker()]
