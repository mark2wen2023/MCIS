"""Independent synthetic HTTP/SQLite checks of NEW expected-checksum contract."""
import base64
import hashlib
import json
from pathlib import Path
import pytest
from tests.test_evidence_intake_w42 import local,CASE
from tests.conftest import H
from mcis_service.audit.models import AuditEventRow
from mcis_service.evidence.models import EvidenceRow,CustodyEventRow

URL=f'/api/v1/cases/{CASE}/evidence'


def body(raw,sha):
    return {'title':'Independent checksum','source':'Synthetic declaration only','extractedBy':'Independent',
        'extractedUtc':'2026-01-01T00:00:00Z','relativePath':'evidence/checksum.bin',
        'contentBase64':base64.b64encode(raw).decode(),'sha256':sha}


def state(app):
    with app.state.db.session() as s:
        rows=tuple(s.query(m).count() for m in (EvidenceRow,CustodyEventRow,AuditEventRow))
    root=app.state.settings.blob_dir
    return rows,{str(p.relative_to(root)):(p.read_bytes() if p.is_file() else None) for p in root.rglob('*')}


@pytest.mark.parametrize('raw',[b'',b'\xff\x00\x80\xc0',bytes(range(256))*8192+b'!'])
def test_mixed_case_checksum_matches_exact_bytes(local,raw):
    c,app=local;sha=hashlib.sha256(raw).hexdigest()
    mixed=''.join(ch.upper() if i%2 else ch for i,ch in enumerate(sha))
    r=c.post(URL,headers=H(),json=body(raw,mixed))
    assert r.status_code==201 and r.json()['sha256']==sha,r.text
    assert (app.state.settings.blob_dir/CASE/'evidence/checksum.bin').read_bytes()==raw
    read=c.get(URL+'/'+r.json()['evidenceId']+'/content',headers=H())
    assert read.status_code==200 and read.content==raw and read.headers['x-sha256']==sha


def test_expected_digest_compares_incoming_bytes_not_existing_file(local):
    c,app=local;original=b'old synthetic';sha=hashlib.sha256(original).hexdigest()
    assert c.post(URL,headers=H(),json=body(original,sha)).status_code==201
    before=state(app)
    r=c.post(URL,headers=H(),json=body(b'different incoming bytes',sha))
    assert r.status_code==422 and r.json()['code']=='EXPECTED_SHA256_MISMATCH'
    assert state(app)==before
    # Fully matching incoming digest does not override the old blob's no-overwrite rule.
    raw=b'different incoming bytes'
    r=c.post(URL,headers=H(),json=body(raw,hashlib.sha256(raw).hexdigest()))
    assert r.status_code==409 and r.json()['code']=='BLOB_EXISTS' and state(app)==before


@pytest.mark.parametrize('sha',['\ud800'*64,'A'*64+'\r',True,[],123])
def test_bad_sha_or_schema_type_no_mutation(local,sha):
    c,app=local;before=state(app)
    r=c.post(URL,headers={**H(),'Content-Type':'application/json'},content=json.dumps(body(b'x',sha),ensure_ascii=True))
    assert r.status_code==422 and state(app)==before,r.text
    if isinstance(sha,str):assert r.json()['code']=='INVALID_SHA256'


def test_request_only_digest_declaration_stays_no_file(local):
    c,app=local;sha=hashlib.sha256(b'not uploaded').hexdigest()
    b=body(b'',sha);b.pop('contentBase64')
    r=c.post(URL,headers=H(),json=b)
    assert r.status_code==201 and r.json()['sha256']==sha
    assert not (app.state.settings.blob_dir/CASE/'evidence/checksum.bin').exists()
    assert c.get(URL+'/'+r.json()['evidenceId']+'/content',headers=H()).status_code==404


def test_actual_loopback_http_error_order_and_matching_empty(local):
    import http.client,socket,threading,time
    import uvicorn
    _,app=local;sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen(16)
    port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,lifespan='off',log_level='error',access_log=False))
    thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
    try:
        deadline=time.monotonic()+5
        while not server.started and thread.is_alive() and time.monotonic()<deadline:time.sleep(.01)
        assert server.started
        invalid64=body(b'x','bad');invalid64['contentBase64']='Zh=='
        scenarios=[(invalid64,H(),422,'INVALID_BASE64'),(body(b'x','0'*64),H('Public'),403,'FORBIDDEN'),
            (body(b'', '0'*64),H(),422,'EXPECTED_SHA256_MISMATCH'),
            (body(b'',hashlib.sha256(b'').hexdigest().upper()),H(),201,None)]
        before=state(app)
        for payload,headers,status,code in scenarios:
            conn=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
            try:
                conn.request('POST',URL,json.dumps(payload),headers={**headers,'Content-Type':'application/json'})
                response=conn.getresponse();result=json.loads(response.read())
                assert response.status==status,result
                if code:
                    assert result['code']==code and state(app)==before
                else:assert result['sha256']==hashlib.sha256(b'').hexdigest()
            finally:conn.close()
    finally:server.should_exit=True;thread.join(timeout=3);sock.close()
    assert not thread.is_alive()


def test_openapi_dual_fields_nullable_and_problem_ref_resolves():
    import yaml
    doc=yaml.safe_load((Path(__file__).resolve().parents[2]/'contracts/openapi.yaml').read_text())
    post=doc['paths']['/api/v1/cases/{caseId}/evidence']['post']
    properties=post['requestBody']['content']['application/json']['schema']['properties']
    for key in ('contentBase64','sha256'):assert set(properties[key]['type'])=={'string','null'}
    ref=post['responses']['422']['$ref'];assert ref.startswith('#/')
    value=doc
    for part in ref[2:].split('/'):value=value[part]
    assert isinstance(value,dict) and 'description' in value
    assert '新增双字段校验合同' in properties['sha256']['description']
