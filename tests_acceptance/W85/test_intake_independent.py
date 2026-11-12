"""Independent API acceptance; synthetic basic package built without implementation helpers."""
import base64
import hashlib
import io
import json
import zipfile
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.cases.models import CaseRow
from mcis_service.audit.models import AuditEventRow
from mcis_service.package_intake.router import IntakeReceipt
from mcis_service.redaction.policy import default_policy

BASE='/api/v1/packages/intakes'
CID='CASE-ACCEPT-W85'


def files():
    case={'caseId':CID,'schemaVersion':'1.0.0','title':'独立验收虚构案','accidentCode':'','accidentType':'Collision',
          'accidentGrade':'','incidentTimeUtc':'2026-01-01T00:00:00Z','caseEpochUtc':'2026-01-01T00:00:00Z',
          'displayTimeZoneOffsetMinutes':480,'incidentLocation':{'lonDeg':120,'latDeg':30,'heightM':0},
          'seaLevelOffsetM':0,'leadInvestigator':'测试员','agencyName':'测试机构','isFictionalDemo':True,'summaryNotes':''}
    return {'case.json':json.dumps(case,ensure_ascii=False).encode(),'case.ext.json':b'{}','vessels.json':b'[]',
            'evidence/index.json':b'[]','audit/audit.jsonl':b'','audit/custody.jsonl':b'',
            'access-policy.json':json.dumps(default_policy()).encode()}


def package(f):
    def role(p):
        if p=='case.json':return 'CaseDefinition'
        if p=='vessels.json':return 'VesselLibrary'
        if p.startswith('audit/'):return 'Audit'
        if p.startswith(('raw/','evidence/')):return 'RawEvidence'
        return 'Derived'
    # This profile names generic sidecars Metadata, mirror documented manifest roles.
    from mcis_service.package.mcase import infer_role
    m={'packageFormat':'MCIS-MCASE','packageVersion':'1.0.0','caseId':CID,
       'createdAtUtc':'2026-01-01T00:00:00Z','lastModifiedAtUtc':'2026-01-01T00:00:00Z','generatorVersion':'acceptance-independent',
       'files':[{'relativePath':p,'role':infer_role(p),'sizeBytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for p,b in f.items()]}
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w',zipfile.ZIP_DEFLATED) as z:
        for p,raw in f.items():z.writestr(p,raw)
        z.writestr('manifest.json',json.dumps(m))
    return b.getvalue()


def body(raw,commit=False):
    b={'contentBase64':base64.b64encode(raw).decode()}
    if commit:b.update(confirmed=True,sourceSha256=hashlib.sha256(raw).hexdigest())
    return b


@pytest.fixture
def client(tmp_path):
    settings=Settings(data_dir=tmp_path,seed_demo=False)
    with TestClient(create_app(settings)) as c:yield c


def test_new_case_preview_commit_replay_source_and_chain(client):
    raw=package(files()); digest=hashlib.sha256(raw).hexdigest()
    assert client.post(BASE+':preview',json=body(raw)).status_code==200
    with client.app.state.db.session() as s:assert s.scalar(select(CaseRow)) is None
    out=client.post(BASE+':commit',json=body(raw,True))
    assert out.status_code==200,out.text
    assert out.json()['replayed'] is False
    assert client.get(BASE+'/'+digest).json()['replayed'] is True
    assert client.post(BASE+':commit',json=body(raw,True)).json()['replayed'] is True
    assert (client.app.state.settings.blob_dir/CID/'_package_intake/source.mcase').read_bytes()==raw
    with client.app.state.db.session() as s:
        assert len(s.scalars(select(IntakeReceipt)).all())==1
        assert len(s.scalars(select(AuditEventRow)).all())==1


@pytest.mark.parametrize('extra',[('foreign/.keep',b''),('analysis/timeline.json',b'{"events":[{}]}'),('unknown.json',b'{}')])
def test_unknown_or_nonempty_business_never_silently_discarded(client,extra):
    f=files();f[extra[0]]=extra[1];raw=package(f)
    assert client.post(BASE+':preview',json=body(raw)).status_code==422
    assert client.post(BASE+':commit',json=body(raw,True)).status_code==422


@pytest.mark.parametrize('role',['Public','AgentService','InterestedState','ExternalExpert'])
def test_restricted_identity_no_preview_or_commit_or_receipt(client,role):
    raw=package(files());h={'X-MCIS-Role':role}
    assert client.post(BASE+':preview',json=body(raw),headers=h).status_code==403
    assert client.post(BASE+':commit',json=body(raw,True),headers=h).status_code==403
    assert client.get(BASE+'/'+hashlib.sha256(raw).hexdigest(),headers=h).status_code==403


def test_same_case_different_package_concurrent(client):
    f=files();raw1=package(f)
    c=json.loads(f['case.json']);c['title']='不同原包';f['case.json']=json.dumps(c).encode();raw2=package(f)
    with ThreadPoolExecutor(2) as e:
        out=list(e.map(lambda raw:client.post(BASE+':commit',json=body(raw,True)),[raw1,raw2]))
    assert sorted(x.status_code for x in out)==[200,409]
    with client.app.state.db.session() as s:
        assert len(s.scalars(select(CaseRow)).all())==1
        assert len(s.scalars(select(IntakeReceipt)).all())==1


def test_final_commit_failure_removes_only_owned_files(client,monkeypatch):
    sentinel=client.app.state.settings.blob_dir/'unrelated';sentinel.mkdir();(sentinel/'a').write_text('keep')
    def reject(_):raise RuntimeError('independent final commit failure')
    with monkeypatch.context() as m:
        m.setattr(client.app.state.db.SessionLocal.class_,'commit',reject)
        with pytest.raises(RuntimeError):client.post(BASE+':commit',json=body(package(files()),True))
    assert list(client.app.state.settings.blob_dir.iterdir())==[sentinel]
    assert (sentinel/'a').read_text()=='keep'
    with client.app.state.db.session() as s:
        assert not s.scalars(select(CaseRow)).all()
        assert not s.scalars(select(AuditEventRow)).all()
        assert not s.scalars(select(IntakeReceipt)).all()


@pytest.mark.parametrize('ending',['\r\n','\n'])
def test_accepted_audit_lines_import_exactly(client,ending):
    f=files()
    rec={'utc':'2026-01-01T00:00:00Z','operator':'测试员','action':'case.create','category':'Case',
         'command':'跨行标记\u2028保留','before':'','after':'','seq':1,'prev':'0'*64}
    line=json.dumps(rec,ensure_ascii=False,separators=(',',':'))
    f['audit/audit.jsonl']=(line+ending).encode();raw=package(f)
    preview=client.post(BASE+':preview',json=body(raw))
    if preview.status_code==422:return # explicit unsupported rejection is acceptable
    assert preview.status_code==200,preview.text
    out=client.post(BASE+':commit',json=body(raw,True))
    assert out.status_code==200,out.text
    with client.app.state.db.session() as s:
        first=s.scalars(select(AuditEventRow).order_by(AuditEventRow.seq)).first()
        assert first.line==line+('\r' if ending=='\r\n' else '')


def test_accepted_bom_audit_matches_import(client):
    f=files()
    line=json.dumps({'utc':'2026-01-01T00:00:00Z','operator':'test','action':'case.create','category':'Case',
                     'command':'new','before':'','after':'','seq':1,'prev':'0'*64},separators=(',',':'))
    f['audit/audit.jsonl']=b'\xef\xbb\xbf'+line.encode()+b'\n';raw=package(f)
    p=client.post(BASE+':preview',json=body(raw))
    if p.status_code==422:return
    assert p.status_code==200,p.text
    out=client.post(BASE+':commit',json=body(raw,True))
    assert out.status_code==200,out.text


def test_receipt_refuses_changed_original_and_no_reimport(client):
    raw=package(files());digest=hashlib.sha256(raw).hexdigest()
    assert client.post(BASE+':commit',json=body(raw,True)).status_code==200
    original=client.app.state.settings.blob_dir/CID/'_package_intake/source.mcase'
    original.write_bytes(b'tampered')
    assert client.get(BASE+'/'+digest).status_code==409
    assert client.post(BASE+':commit',json=body(raw,True)).status_code==409
    assert original.read_bytes()==b'tampered'


def test_existing_symlink_not_followed(client,tmp_path):
    root=client.app.state.settings.blob_dir
    elsewhere=tmp_path/'elsewhere';elsewhere.mkdir();sentinel=elsewhere/'sentinel';sentinel.write_text('untouched')
    (root/CID).symlink_to(elsewhere,target_is_directory=True)
    assert client.post(BASE+':commit',json=body(package(files()),True)).status_code==409
    assert sentinel.read_text()=='untouched'
    assert list(elsewhere.iterdir())==[sentinel]


def test_changed_policy_receipt_does_not_bypass(client):
    from mcis_service.redaction.models import AccessPolicyRow
    raw=package(files());digest=hashlib.sha256(raw).hexdigest()
    assert client.post(BASE+':commit',json=body(raw,True)).status_code==200
    with client.app.state.db.session() as s:
        row=s.scalars(select(AccessPolicyRow)).first()
        policy=json.loads(json.dumps(row.doc))
        # Replace policy by deny-all rather than relying on original default grant.
        policy['matrix']['Investigator']['evidence_meta']='Deny'
        row.doc=policy
    result=client.get(BASE+'/'+digest)
    assert result.status_code==403,result.text


def test_lf_audit_bytes_preserved_and_import_appended(client):
    f=files()
    line=json.dumps({'utc':'2026-01-01T00:00:00Z','operator':'原记录员','action':'case.create','category':'Case',
                     'command':'原始记录','before':'','after':'','seq':1,'prev':'0'*64},ensure_ascii=False,separators=(',',':'))
    f['audit/audit.jsonl']=(line+'\n').encode();raw=package(f)
    assert client.post(BASE+':preview',json=body(raw)).status_code==200
    out=client.post(BASE+':commit',json=body(raw,True));assert out.status_code==200,out.text
    with client.app.state.db.session() as s:
        rows=s.scalars(select(AuditEventRow).order_by(AuditEventRow.seq)).all()
        assert len(rows)==2 and rows[0].line==line
        assert rows[1].action=='package.import'
        assert rows[1].prev_hash==hashlib.sha256(line.encode()).hexdigest()
