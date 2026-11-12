import base64
import hashlib
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select
from mcis_service.package_intake import router as r
from mcis_service.cases.models import CaseRow
from .test_package_intake_parser import base, pack
from .conftest import H

P = '/api/v1/packages/intakes'


def payload(data=None, commit=False):
    data = data or pack(base())
    body = {'contentBase64': base64.b64encode(data).decode()}
    if commit: body.update(sourceSha256=hashlib.sha256(data).hexdigest(), confirmed=True)
    return body


def test_preview_commit_recover(empty_client):
    c = empty_client; data = pack(base()); body = payload(data)
    before = c.get('/api/v1/cases').json()
    out = c.post(P+':preview', json=body)
    assert out.status_code == 200, out.text
    assert c.get('/api/v1/cases').json() == before
    out = c.post(P+':commit', json=payload(data, True))
    assert out.status_code == 200, out.text
    receipt = out.json(); assert receipt['replayed'] is False
    digest = receipt['sourceSha256']
    assert c.get(P+'/'+digest).json()['replayed'] is True
    assert c.post(P+':commit', json=payload(data, True)).json()['replayed'] is True
    assert c.post(P+':preview', json=body).status_code == 409
    archive = c.app.state.settings.blob_dir/'CASE-INTAKE'/'_package_intake'/'source.mcase'
    assert archive.read_bytes() == data
    archive.write_bytes(b'changed')
    assert c.get(P+'/'+digest).status_code == 409
    assert c.post(P+':commit', json=payload(data, True)).status_code == 409


@pytest.mark.parametrize('role', ['Public','ExternalExpert','InterestedState','AgentService'])
def test_roles(empty_client, role):
    for suffix in [':preview', ':commit']:
        assert empty_client.post(P+suffix, json=payload(commit=suffix==':commit'), headers=H(role)).status_code==403
    assert empty_client.get(P+'/'+'a'*64, headers=H(role)).status_code==403


@pytest.mark.parametrize('change', [{'confirmed':False},{'confirmed':1},{'sourceSha256':'a'*64},{'extra':1}])
def test_confirmation(empty_client, change):
    body=payload(commit=True);body.update(change)
    assert empty_client.post(P+':commit',json=body).status_code==422
    assert not list(empty_client.app.state.settings.blob_dir.iterdir())


def test_existing_directory_never_overwritten(empty_client):
    root=empty_client.app.state.settings.blob_dir
    target=root/'CASE-INTAKE';target.mkdir();(target/'sentinel').write_text('original')
    assert empty_client.post(P+':commit',json=payload(commit=True)).status_code==409
    assert (target/'sentinel').read_text()=='original'


def test_final_commit_failure_rolls_back(empty_client, monkeypatch):
    c=empty_client; session_class=c.app.state.db.SessionLocal.class_
    def broken(self): raise RuntimeError('commit injected')
    with monkeypatch.context() as m:
        m.setattr(session_class, 'commit', broken)
        with pytest.raises(RuntimeError,match='commit injected'):
            c.post(P+':commit',json=payload(commit=True))
    assert not list(c.app.state.settings.blob_dir.iterdir())
    with c.app.state.db.session() as s:
        assert not s.scalars(select(CaseRow)).all()
        assert not s.scalars(select(r.IntakeReceipt)).all()


def test_same_case_concurrency(empty_client):
    body=payload(commit=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(lambda _:empty_client.post(P+':commit',json=body),range(2)))
    assert [x.status_code for x in responses]==[200,200]
    assert sorted(x.json()['replayed'] for x in responses)==[False,True]
    with empty_client.app.state.db.session() as s:
        assert len(s.scalars(select(CaseRow)).all())==1
        assert len(s.scalars(select(r.IntakeReceipt)).all())==1


def test_read_only_missing(empty_client):
    assert empty_client.get(P+'/'+'a'*64).status_code==404
    assert not list(empty_client.app.state.settings.blob_dir.iterdir())


def test_real_evidence_package_roundtrip(empty_client):
    from .test_package_intake_parser import valid_package
    from mcis_service.package_intake.parser import parse_package
    raw = valid_package(); parsed = parse_package(raw)
    result = empty_client.post(P+':commit',json=payload(raw,True))
    assert result.status_code == 200, result.text
    root = empty_client.app.state.settings.blob_dir/'CASE-INTAKE'
    for item in parsed.evidence:
        assert (root/item['relativePath']).read_bytes()==parsed.files[item['relativePath']]
    case='/api/v1/cases/CASE-INTAKE'
    assert empty_client.get(case+'/custody:verify-chain').json()['valid']
    assert empty_client.get(case+'/audit:verify').json()['valid']
    actual = empty_client.get(case+'/evidence').json()
    assert len(actual) == len(parsed.evidence)
    for expected, observed in zip(parsed.evidence, actual):
        assert all(observed[k] == v for k, v in expected.items())
