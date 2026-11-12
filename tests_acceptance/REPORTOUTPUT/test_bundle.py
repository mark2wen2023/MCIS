"""Independent synthetic baseline checks. Prepared before freeze; no pass claimed."""
import hashlib
import io
import json
import zipfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from mcis_service.config import Settings
from mcis_service.main import create_app
from mcis_service.audit.models import AuditEventRow
from mcis_service.reports.models import ReportAuditRow

CASE = 'SYN-INDEPENDENT-OUTPUT'
HEADERS = {'X-MCIS-Role': 'LeadInvestigator', 'X-MCIS-Operator': 'Independent Synthetic Output'}
BASE = '/api/v1/cases/' + CASE

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

@pytest.fixture
def fixture(tmp_path):
    app = create_app(Settings(data_dir=Path(tmp_path), seed_demo=False))
    with TestClient(app, raise_server_exceptions=False) as client:
        case = {'caseId': CASE, 'schemaVersion': '1.0.0', 'title': '虚构独立下载验收',
                'accidentType': 'Collision', 'isFictionalDemo': True,
                'caseEpochUtc': '2026-01-01T00:00:00Z', 'incidentTimeUtc': '2026-01-01T00:00:00Z',
                'incidentLocation': {'lonDeg': 121, 'latDeg': 31}, 'displayTimeZoneOffsetMinutes': 0}
        response = client.post('/api/v1/cases', headers=HEADERS, json=case)
        assert response.status_code == 201, response.text
        response = client.post(BASE + '/reports', headers=HEADERS, json={'templateId': 'imo-cic', 'lang': 'bilingual'})
        assert response.status_code == 201, response.text
        report = response.json()
        yield client, report, BASE + '/reports/' + report['reportId']

@pytest.mark.parametrize('fmt', ['pdf', 'docx'])
def test_real_bundle_matches_stored_input_and_persisted_audit(fixture, fmt, monkeypatch):
    client, report, url = fixture
    preview = client.get(url + '/output-bundle:preview', headers=HEADERS)
    assert preview.status_code == 200, preview.text
    expected = preview.json()['reportDocumentSha256']
    calls=[];original=implementation.render
    def observed(doc,**options):
        calls.append(copy.deepcopy(doc));return original(doc,**options)
    monkeypatch.setattr(implementation,'render',observed)
    with client.app.state.db.session() as session:
        old = list(session.scalars(select(AuditEventRow).where(AuditEventRow.case_id == CASE)))
        old_lines = [row.line for row in old]
    response = client.post(url + '/output-bundle', headers=HEADERS,
                           json={'format': fmt, 'lang': 'en', 'expectedReportDigest': expected})
    assert response.status_code == 200, response.text[:200]
    assert calls==[report]
    assert response.headers['cache-control'] == 'no-store'
    assert digest(response.content) == response.headers['x-sha256']
    with zipfile.ZipFile(io.BytesIO(response.content)) as bundle:
        assert bundle.namelist() == ['report.' + fmt, 'report.json', 'audit.json', 'manifest.json']
        source = bundle.read('report.json')
        assert digest(source) == expected and json.loads(source) == report
        output = bundle.read('report.' + fmt)
        if fmt == 'pdf':
            assert output.startswith(b'%PDF-')
            import subprocess
            extracted=subprocess.run(['pdftotext','-','-'],input=output,capture_output=True,check=True).stdout.decode()
            assert report['reportId'] in extracted and report['caseId'] in extracted and 'DRAFT' in extracted
        else:
            with zipfile.ZipFile(io.BytesIO(output)) as docx:
                assert report['reportId'].encode() in docx.read('word/document.xml')
        audit = json.loads(bundle.read('audit.json'))
        manifest = json.loads(bundle.read('manifest.json'))
        for member in manifest['members']:
            raw = bundle.read(member['name'])
            assert len(raw) == member['byteLength'] and digest(raw) == member['sha256']
        reason = json.loads(audit['snapshot']['doc']['reason'])
        assert reason['reportDocumentSha256'] == expected
        assert reason['documentSha256'] == digest(output)
    assert client.get(url, headers=HEADERS).json() == report
    with client.app.state.db.session() as session:
        events = list(session.scalars(select(AuditEventRow).where(AuditEventRow.case_id == CASE).order_by(AuditEventRow.seq)))
        assert [row.line for row in events[:-1]] == old_lines
        assert events[-1].line == audit['line'] and events[-1].seq == audit['seq']
        snapshot = session.scalars(select(ReportAuditRow).where(ReportAuditRow.case_id == CASE, ReportAuditRow.key == audit['snapshot']['key'])).one()
        assert snapshot.doc == audit['snapshot']['doc']

from concurrent.futures import ThreadPoolExecutor
from mcis_service.report_output import router as implementation
from mcis_service.redaction.policy import default_policy, CATEGORIES
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.reports.models import ReportRow
from mcis_service.db import put_doc
import copy
import base64

def args_for(client, url):
    response = client.get(url + '/output-bundle:preview', headers=HEADERS)
    assert response.status_code == 200, response.text
    return {'format': 'docx', 'lang': 'zh', 'expectedReportDigest': response.json()['reportDocumentSha256']}

def audit_lines(client):
    with client.app.state.db.session() as session:
        return [(r.seq, r.line) for r in session.scalars(select(AuditEventRow).where(AuditEventRow.case_id == CASE).order_by(AuditEventRow.seq))]

@pytest.mark.parametrize('category', CATEGORIES)
def test_each_category_denied_before_renderer_and_missing_report(fixture, category, monkeypatch):
    client, report, url = fixture
    args = args_for(client, url)
    policy = copy.deepcopy(default_policy())
    policy['matrix']['LeadInvestigator'][category] = 'Deny'
    with client.app.state.db.session() as session:
        put_doc(session, AccessPolicyRow, CASE, 'policy', policy)
    before = audit_lines(client)
    def prohibited(*a, **kw):
        pytest.fail('renderer must not be called')
    monkeypatch.setattr(implementation, 'render', prohibited)
    for target in (url, BASE + '/reports/MISSING'):
        for method, suffix in [('GET', ':preview'), ('POST', '')]:
            r = client.request(method, target + '/output-bundle' + suffix, headers=HEADERS, **({'json': args} if method == 'POST' else {}))
            assert r.status_code == 403, r.text
            assert r.json()['code'] == 'FORBIDDEN' and r.headers['cache-control'] == 'no-store'
    assert audit_lines(client) == before

@pytest.mark.parametrize('change,expected', [('report',409), ('allowed_policy',409), ('denied_policy',403)])
def test_render_releases_writer_for_second_connection(fixture, monkeypatch, change, expected):
    client, report, url = fixture
    args = args_for(client, url)
    before = audit_lines(client)
    calls = []
    def writer():
        with client.app.state.db.session() as session:
            if change == 'report':
                doc = copy.deepcopy(report)
                doc['disclaimerEn'] += ' synthetic concurrent modification'
                put_doc(session, ReportRow, CASE, report['reportId'], doc)
            else:
                policy = copy.deepcopy(default_policy())
                if change == 'denied_policy': policy['matrix']['LeadInvestigator']['audit'] = 'Deny'
                put_doc(session, AccessPolicyRow, CASE, 'policy', policy)
    def render(doc, **kw):
        calls.append(copy.deepcopy(doc))
        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(writer).result(timeout=10)
        return b'SYNTHETIC RENDER STUB: used only for scheduling tests'
    monkeypatch.setattr(implementation, 'render', render)
    r = client.post(url + '/output-bundle', headers=HEADERS, json=args)
    assert r.status_code == expected, r.text
    assert len(calls) == 1 and audit_lines(client) == before

@pytest.mark.parametrize('raw', [b'{}', b'{"format":"docx","format":"pdf"}', b'\xef\xbb\xbf{}', b'{"x":NaN}', b'{"x":"\\ud800"}'])
def test_bad_body_no_render_no_audit(fixture, monkeypatch, raw):
    client, report, url = fixture
    before = audit_lines(client)
    monkeypatch.setattr(implementation, 'render', lambda *a, **kw: pytest.fail('unexpected render'))
    r = client.post(url + '/output-bundle', headers={**HEADERS,'Content-Type':'application/json'}, content=raw)
    assert r.status_code == 422, r.text
    assert r.headers['cache-control'] == 'no-store' and audit_lines(client) == before

def test_generated_reason_survives_actual_archive_roundtrip(fixture, tmp_path):
    client, report, url = fixture
    r = client.post(url + '/output-bundle', headers=HEADERS, json=args_for(client, url))
    assert r.status_code == 200, r.text
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        output_audit = json.loads(z.read('audit.json'))
        rendered = z.read('report.docx')
    archived = client.get(BASE + '/export', headers=HEADERS)
    assert archived.status_code == 200, archived.text
    with TestClient(create_app(Settings(data_dir=tmp_path/'restored',seed_demo=False)),raise_server_exceptions=False) as target:
        restored = target.post('/api/v1/packages/intakes:commit', headers=HEADERS,
            json={'contentBase64':base64.b64encode(archived.content).decode(),'sourceSha256':digest(archived.content),'confirmed':True})
        assert restored.status_code == 200, restored.text
        assert target.get(url, headers=HEADERS).json() == report
        assert output_audit['line'] in [line for _,line in audit_lines(target)]
        assert not any(p.read_bytes() == rendered for p in target.app.state.settings.blob_dir.rglob('*') if p.is_file())

from sqlalchemy import event, text
from sqlalchemy.orm import Session

def db_state(client):
    with client.app.state.db.engine.connect() as connection:
        names = sorted(connection.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).scalars())
        return {name:[tuple(row) for row in connection.execute(text('SELECT * FROM "'+name+'"'))] for name in names}

@pytest.mark.parametrize('fault', ['render', 'assemble', 'commit'])
def test_failed_precommit_work_rolls_back_every_table(fixture, monkeypatch, fault):
    client, report, url = fixture
    args = args_for(client, url)
    before = db_state(client)
    def explode(*a, **kw): raise RuntimeError('synthetic failure must not escape')
    if fault == 'render': monkeypatch.setattr(implementation,'render',explode)
    if fault == 'assemble': monkeypatch.setattr(implementation,'assemble',explode)
    def block_export_commit(session):
        if session.get_bind() is not client.app.state.db.engine: return
        rows = session.scalars(select(AuditEventRow).where(AuditEventRow.case_id == CASE, AuditEventRow.action == 'report.export')).all()
        if rows: raise RuntimeError('synthetic commit failure')
    if fault == 'commit': event.listen(Session,'before_commit',block_export_commit)
    try:
        r = client.post(url+'/output-bundle',headers=HEADERS,json=args)
    finally:
        if fault == 'commit': event.remove(Session,'before_commit',block_export_commit)
    assert r.status_code == (503 if fault == 'render' else 500), r.text
    assert 'synthetic failure' not in r.text and r.headers['cache-control']=='no-store'
    assert db_state(client) == before

def test_renderer_mutation_does_not_change_input_snapshot(fixture, monkeypatch):
    client, report, url = fixture
    args = args_for(client,url)
    def mutating(doc, **kw):
        doc['lang']='en'; doc['sections'].clear()
        return b'synthetic renderer mutation probe only'
    monkeypatch.setattr(implementation,'render',mutating)
    r=client.post(url+'/output-bundle',headers=HEADERS,json=args)
    assert r.status_code==200,r.text
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        assert json.loads(z.read('report.json'))==report
        assert digest(z.read('report.json'))==args['expectedReportDigest']
    assert client.get(url,headers=HEADERS).json()==report

@pytest.mark.parametrize('kind', ['default_role','report_identity','source_identity'])
def test_identity_and_default_role_fail_closed(fixture, monkeypatch, kind):
    client, report, url = fixture
    args=args_for(client,url)
    headers=HEADERS
    if kind=='default_role': headers={**HEADERS,'X-MCIS-Role':'Investigator'}
    else:
        with client.app.state.db.session() as session:
            if kind=='report_identity':
                changed=copy.deepcopy(report);changed['caseId']='SYN-OTHER-CASE'
                put_doc(session,ReportRow,CASE,report['reportId'],changed)
            else:
                from mcis_service.evidence.models import EvidenceRow
                put_doc(session,EvidenceRow,CASE,'SYN-E1',{'caseId':'SYN-OTHER-CASE','evidenceId':'SYN-E1'})
    before=db_state(client)
    monkeypatch.setattr(implementation,'render',lambda *a,**kw:pytest.fail('must refuse before render'))
    for method,suffix in [('GET',':preview'),('POST','')]:
        r=client.request(method,url+'/output-bundle'+suffix,headers=headers,**({'json':args} if method=='POST' else {}))
        assert r.status_code=={'default_role':403,'report_identity':422,'source_identity':409}[kind],r.text
        assert r.headers['cache-control']=='no-store'
    assert db_state(client)==before

@pytest.mark.parametrize('budget', ['REPORT_LIMIT','OUTPUT_LIMIT','AUDIT_LIMIT','MANIFEST_LIMIT','ZIP_LIMIT'])
def test_engineering_budget_rejection_has_no_persistent_effect(fixture,monkeypatch,budget):
    client,report,url=fixture
    args=args_for(client,url);before=db_state(client)
    monkeypatch.setattr(implementation,budget,16)
    r=client.post(url+'/output-bundle',headers=HEADERS,json=args)
    assert r.status_code==413 and r.json()['code']=='REPORT_OUTPUT_BUDGET',r.text
    assert db_state(client)==before
    if budget=='REPORT_LIMIT':
        assert client.get(url+'/output-bundle:preview',headers=HEADERS).status_code==413

def test_actual_request_byte_budget(fixture):
    client,report,url=fixture;before=db_state(client)
    r=client.post(url+'/output-bundle',headers={**HEADERS,'Content-Type':'application/json'},content=b' '*1025)
    assert r.status_code==413 and db_state(client)==before

def test_response_failure_after_commit_does_not_erase_event(fixture,monkeypatch):
    client,report,url=fixture;args=args_for(client,url);before=audit_lines(client)
    def broken_response(*args,**kwargs):raise RuntimeError('synthetic response failure after commit')
    monkeypatch.setattr(implementation,'Response',broken_response)
    r=client.post(url+'/output-bundle',headers=HEADERS,json=args)
    assert r.status_code==500 and r.headers['cache-control']=='no-store'
    after=audit_lines(client)
    assert after[:-1]==before and len(after)==len(before)+1
    assert json.loads(after[-1][1])['action']=='report.export'
    assert client.get(url,headers=HEADERS).json()==report

@pytest.mark.parametrize('fmt',['pdf','docx'])
def test_old_plain_export_still_returns_original_format(fixture,fmt):
    client,report,url=fixture;before=audit_lines(client)
    r=client.get(url+'/export',params={'format':fmt,'lang':'en'},headers=HEADERS)
    assert r.status_code==200,r.text
    assert digest(r.content)==r.headers['x-sha256'] and r.headers['cache-control']=='no-store'
    assert r.content.startswith(b'%PDF-' if fmt=='pdf' else b'PK')
    assert client.get(url,headers=HEADERS).json()==report
    lines=audit_lines(client);assert len(lines)==len(before)+1
    assert json.loads(lines[-1][1]).get('reason','')==''

@pytest.mark.parametrize('when',['before','during'])
@pytest.mark.parametrize('source_problem',['missing','changed'])
def test_unrelated_current_interview_source_is_rechecked(fixture,monkeypatch,when,source_problem):
    from mcis_service.interviews.models import InterviewRow
    from mcis_service.evidence.models import EvidenceRow
    client,report,url=fixture;args=args_for(client,url)
    def introduce():
        with client.app.state.db.session() as session:
            if source_problem=='changed':
                put_doc(session,EvidenceRow,CASE,'SYN-SOURCE',{'caseId':CASE,'evidenceId':'SYN-SOURCE','sha256':'a'*64,'confidentiality':'Internal'})
            put_doc(session,InterviewRow,CASE,'IR-99',{'caseId':CASE,'recordId':'IR-99','evidenceId':'SYN-SOURCE','sourceSha256':'b'*64})
    calls=[]
    def render(*a,**kw):
        calls.append(1)
        if when=='before':pytest.fail('source refusal must precede render')
        with ThreadPoolExecutor(max_workers=1) as executor:executor.submit(introduce).result(timeout=10)
        return b'synthetic scheduling probe'
    if when=='before':introduce()
    before=audit_lines(client)
    monkeypatch.setattr(implementation,'render',render)
    r=client.post(url+'/output-bundle',headers=HEADERS,json=args)
    assert r.status_code==(403 if source_problem=='missing' else 409),r.text
    assert len(calls)==(0 if when=='before' else 1) and audit_lines(client)==before

@pytest.mark.parametrize('mode',['readonly','fieldrule'])
def test_readonly_export_is_allowed_but_applicable_rule_denied(fixture,mode):
    client,report,url=fixture;args=args_for(client,url)
    policy=copy.deepcopy(default_policy())
    policy['matrix']['LeadInvestigator']={key:'ReadOnly' for key in CATEGORIES}
    if mode=='fieldrule':policy['fieldRules'].append({'ruleId':'SYN-LEAD','field':'evidence.restricted','method':'Remove','appliesTo':['LeadInvestigator']})
    with client.app.state.db.session() as session:put_doc(session,AccessPolicyRow,CASE,'policy',policy)
    r=client.post(url+'/output-bundle',headers=HEADERS,json=args)
    assert r.status_code==(200 if mode=='readonly' else 403),r.text

@pytest.mark.parametrize('over',[0,1])
def test_actual_two_mib_report_boundary(fixture,over):
    client,report,url=fixture
    changed=copy.deepcopy(report);changed['disclaimerEn']=''
    raw=json.dumps(changed,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    changed['disclaimerEn']='x'*(2*1024*1024-len(raw)+over)
    with client.app.state.db.session() as session:put_doc(session,ReportRow,CASE,report['reportId'],changed)
    before=audit_lines(client)
    r=client.get(url+'/output-bundle:preview',headers=HEADERS)
    assert r.status_code==(200 if over==0 else 413),r.text[:100]
    assert audit_lines(client)==before

@pytest.mark.parametrize('over',[0,1])
def test_actual_sixteen_mib_rendered_byte_boundary(fixture,monkeypatch,over):
    client,report,url=fixture;args=args_for(client,url);before=audit_lines(client)
    # Synthetic output-size probe, NOT a real PDF/DOCX renderer validation.
    output=b'x'*(16*1024*1024+over)
    monkeypatch.setattr(implementation,'render',lambda *a,**kw:output)
    r=client.post(url+'/output-bundle',headers=HEADERS,json=args)
    assert r.status_code==(200 if over==0 else 413),r.text[:100] if r.status_code!=200 else ''
    if over:assert audit_lines(client)==before
    else:
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:assert z.read('report.docx')==output
