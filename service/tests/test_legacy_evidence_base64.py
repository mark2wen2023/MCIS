"""Real local API/SQLite, synthetic bytes; no external services or identity claims."""
import base64
import hashlib
import pytest
from .test_evidence_intake_w42 import local, counts, CASE
from .conftest import H
URL=f'/api/v1/cases/{CASE}/evidence'


def body(value):
    return {'title':'Synthetic strict encoding','source':'Synthetic declaration only',
            'extractedBy':'Synthetic collector','extractedUtc':'2026-01-01T00:00:00Z',
            'relativePath':'evidence/synthetic.bin','contentBase64':value}


@pytest.mark.parametrize('value',['!!!!','Zg','Zg=','Zg===','Zg==x','Zm9v=','Zm9v====',
                                 'Z g==','Zg==\n','\tZg==','====','AA=A','_w==','é',
                                 'data:application/octet-stream;base64,Zg==','Zh==','Zm9='])
def test_invalid_no_writes(local,value):
    c,app=local
    before=counts(app);files=set(app.state.settings.blob_dir.rglob('*'))
    r=c.post(URL,json=body(value),headers=H())
    assert r.status_code==422,r.text
    assert r.json()['code']=='INVALID_BASE64'
    assert counts(app)==before
    assert set(app.state.settings.blob_dir.rglob('*'))==files


@pytest.mark.parametrize('size',[0,1,2,3,255,65536,1048576,1048577])
def test_valid_exact_size_and_empty_file(local,size):
    c,app=local;raw=(bytes(range(256))*((size+255)//256))[:size]
    r=c.post(URL,json=body(base64.b64encode(raw).decode()),headers=H())
    assert r.status_code==201,r.text
    assert r.json()['sha256']==hashlib.sha256(raw).hexdigest()
    assert counts(app)==(1,1,1)
    stored=app.state.settings.blob_dir/CASE/'evidence/synthetic.bin'
    assert stored.is_file() and stored.stat().st_size==size and stored.read_bytes()==raw
    q=c.get(URL+'/'+r.json()['evidenceId']+'/content',headers=H())
    assert q.status_code==200 and q.content==raw


def test_invalid_does_not_overwrite_existing_file(local):
    c,app=local;raw=b'original synthetic evidence'
    assert c.post(URL,json=body(base64.b64encode(raw).decode()),headers=H()).status_code==201
    before=counts(app)
    r=c.post(URL,json=body('!!!!'),headers=H())
    assert r.status_code==422 and counts(app)==before
    assert (app.state.settings.blob_dir/CASE/'evidence/synthetic.bin').read_bytes()==raw


def test_digest_only_stays_metadata_only(local):
    c,app=local;b=body(None);b['sha256']=hashlib.sha256(b'synthetic unavailable').hexdigest()
    r=c.post(URL,json=b,headers=H())
    assert r.status_code==201 and r.json()['sha256']==b['sha256']
    assert counts(app)==(1,1,1)
    assert not (app.state.settings.blob_dir/CASE/'evidence/synthetic.bin').exists()


@pytest.mark.parametrize('value',[17,True,[],{}])
def test_non_string_rejected_without_mutation(local,value):
    c,app=local;before=counts(app)
    r=c.post(URL,json=body(value),headers=H())
    assert r.status_code==422 and counts(app)==before
    assert not (app.state.settings.blob_dir/CASE/'evidence/synthetic.bin').exists()
