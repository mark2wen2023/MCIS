"""New dual-input contract: synthetic API requests, real isolated SQLite/files."""
import base64,hashlib
import pytest
from .test_evidence_intake_w42 import local,CASE,counts
from .test_legacy_evidence_base64 import body,URL
from .conftest import H


def snap(app):
    return counts(app),{str(p.relative_to(app.state.settings.blob_dir)):(p.read_bytes() if p.is_file() else None) for p in app.state.settings.blob_dir.rglob('*')}


@pytest.mark.parametrize('raw',[b'',b'\x00\xffsynthetic',bytes(range(256))*4096+b'!'])
@pytest.mark.parametrize('uppercase',[False,True])
def test_matching_expected_checksum(local,raw,uppercase):
    c,app=local;b=body(base64.b64encode(raw).decode());digest=hashlib.sha256(raw).hexdigest()
    b['sha256']=digest.upper() if uppercase else digest
    r=c.post(URL,json=b,headers=H());assert r.status_code==201,r.text
    assert r.json()['sha256']==digest and counts(app)==(1,1,1)
    stored=app.state.settings.blob_dir/CASE/'evidence/synthetic.bin'
    assert stored.read_bytes()==raw
    q=c.get(URL+'/'+r.json()['evidenceId']+'/content',headers=H())
    assert q.status_code==200 and q.content==raw


@pytest.mark.parametrize('raw',[b'',b'synthetic source',b'\x00\xff'])
@pytest.mark.parametrize('existing',[False,True])
def test_mismatch_zero_writes(local,raw,existing):
    c,app=local
    if existing:
        assert c.post(URL,json=body(base64.b64encode(b'existing synthetic').decode()),headers=H()).status_code==201
    before=snap(app);b=body(base64.b64encode(raw).decode());b['sha256']='0'*64
    r=c.post(URL,json=b,headers=H())
    assert r.status_code==422 and r.json()['code']=='EXPECTED_SHA256_MISMATCH'
    assert snap(app)==before


@pytest.mark.parametrize('digest',['','0'*63,'0'*65,'g'*64,' '+('0'*64),'0'*64+'\n','０'*64,'0'*32+'-'+('0'*31)])
def test_malformed_expected_checksum_zero_writes(local,digest):
    c,app=local;before=snap(app);b=body('Zg==');b['sha256']=digest
    r=c.post(URL,json=b,headers=H())
    assert r.status_code==422 and r.json()['code']=='INVALID_SHA256' and snap(app)==before


@pytest.mark.parametrize('encoded',['!!!!','Zh==','Zg==\n'])
def test_strict_base64_precedes_digest_comparison(local,encoded):
    c,app=local;before=snap(app);b=body(encoded);b['sha256']='0'*64
    r=c.post(URL,json=b,headers=H())
    assert r.status_code==422 and r.json()['code']=='INVALID_BASE64' and snap(app)==before


@pytest.mark.parametrize('mode',['content-only','content-null-sha','sha-only','null-content-sha'])
def test_single_field_compatibility(local,mode):
    c,app=local;raw=b'legacy synthetic';b=body(base64.b64encode(raw).decode())
    if mode=='content-null-sha':b['sha256']=None
    elif mode in ('sha-only','null-content-sha'):
        b['sha256']=hashlib.sha256(raw).hexdigest();b['contentBase64']=None
        if mode=='sha-only':del b['contentBase64']
    r=c.post(URL,json=b,headers=H());assert r.status_code==201,r.text
    assert r.json()['sha256']==hashlib.sha256(raw).hexdigest() and counts(app)==(1,1,1)
    assert (app.state.settings.blob_dir/CASE/'evidence/synthetic.bin').exists()==mode.startswith('content')


def test_authorization_precedes_checksum_detail(local):
    c,app=local;b=body('Zg==');b['sha256']='0'*64;before=snap(app)
    r=c.post(URL,json=b,headers=H('Public'))
    assert r.status_code==403 and snap(app)==before
