"""Independent ASGI HTTP endpoint checks with real temporary SQLite/files, no mocks."""
import base64
import hashlib
import pytest
from tests.test_evidence_intake_w42 import local, CASE
from tests.conftest import H
from mcis_service.audit.models import AuditEventRow
from mcis_service.evidence.models import CustodyEventRow, EvidenceRow

URL=f'/api/v1/cases/{CASE}/evidence'


def body(value):
    return {'title':'Independent synthetic','source':'Synthetic declaration',
        'extractedBy':'Independent','extractedUtc':'2026-01-01T00:00:00Z',
        'relativePath':'evidence/independent.bin','contentBase64':value}


def snapshot(app):
    with app.state.db.session() as s:
        counts=tuple(s.query(model).count() for model in (EvidenceRow,CustodyEventRow,AuditEventRow))
    root=app.state.settings.blob_dir
    files={str(path.relative_to(root)):(hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else 'directory')
           for path in root.rglob('*')}
    return counts,files


@pytest.mark.parametrize('encoded',['YR==','YWJ=','YQ==Yg==','YQ==\r\n','YQ==\x00','😀','\ud800','QUJD==='])
def test_bad_encoding_preserves_existing_tree_and_rows(local,encoded):
    c,app=local;raw=b'existing synthetic content'
    assert c.post(URL,headers=H(),json=body(base64.b64encode(raw).decode())).status_code==201
    before=snapshot(app)
    # ascii-escaped JSON also exercises lone surrogate handling without client encoder errors.
    import json
    r=c.post(URL,headers={**H(),'Content-Type':'application/json'},content=json.dumps(body(encoded),ensure_ascii=True))
    assert r.status_code==422 and r.json()['code']=='INVALID_BASE64',r.text
    assert snapshot(app)==before
    assert len(r.text)<400 and 'existing synthetic content' not in r.text


def test_valid_duplicate_file_still_cannot_overwrite(local):
    c,app=local;original=b'original'
    assert c.post(URL,headers=H(),json=body(base64.b64encode(original).decode())).status_code==201
    before=snapshot(app)
    r=c.post(URL,headers=H(),json=body(base64.b64encode(b'replacement').decode()))
    assert r.status_code==409 and r.json()['code']=='BLOB_EXISTS'
    assert snapshot(app)==before


@pytest.mark.parametrize('raw',[b'',b'\x00\xff\xfe\x80\xc0\x00', bytes(range(256))*8192+b'\xff'])
def test_canonical_binary_round_trip_and_matching_expected_digest(local,raw):
    c,app=local;b=body(base64.b64encode(raw).decode());b['sha256']=hashlib.sha256(raw).hexdigest()  # New dual-input contract; mismatch covered separately.
    r=c.post(URL,headers=H(),json=b)
    assert r.status_code==201,r.text
    expected=hashlib.sha256(raw).hexdigest()
    assert r.json()['sha256']==expected
    path=app.state.settings.blob_dir/CASE/'evidence/independent.bin'
    assert path.is_file() and path.read_bytes()==raw
    q=c.get(URL+'/'+r.json()['evidenceId']+'/content',headers=H())
    assert q.status_code==200 and q.content==raw and q.headers['x-sha256']==expected


def test_authorization_still_precedes_encoding_diagnostics(local):
    c,app=local;before=snapshot(app)
    r=c.post(URL,headers=H('ExternalExpert'),json=body('synthetic invalid%%%'))
    assert r.status_code==403 and 'INVALID_BASE64' not in r.text
    assert snapshot(app)==before


def test_invalid_encoding_before_bad_path_has_no_side_effect(local):
    c,app=local;before=snapshot(app);b=body('%%%');b['relativePath']='../outside.bin'
    r=c.post(URL,headers=H(),json=b)
    assert r.status_code==422 and r.json()['code']=='INVALID_BASE64'
    assert snapshot(app)==before
    assert not (app.state.settings.blob_dir/'outside.bin').exists()


def test_actual_loopback_http_invalid_then_empty_registration(local):
    """One real TCP HTTP check; other tests use ASGI HTTP transport explicitly."""
    import http.client,json,socket,threading,time
    import uvicorn
    _,app=local
    sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen(16)
    port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,lifespan='off',log_level='error',access_log=False))
    thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
    try:
        deadline=time.monotonic()+5
        while not server.started and thread.is_alive() and time.monotonic()<deadline:time.sleep(.01)
        assert server.started
        before=snapshot(app)
        for value,status in [('YWJ=',422),('',201)]:
            connection=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
            try:
                connection.request('POST',URL,json.dumps(body(value)),headers={**H(),'Content-Type':'application/json'})
                response=connection.getresponse();parsed=json.loads(response.read())
                assert response.status==status,parsed
                if status==422:
                    assert parsed['code']=='INVALID_BASE64' and snapshot(app)==before
                else:assert parsed['sha256']==hashlib.sha256(b'').hexdigest()
            finally:connection.close()
    finally:
        server.should_exit=True;thread.join(timeout=3);sock.close()
    assert not thread.is_alive()
