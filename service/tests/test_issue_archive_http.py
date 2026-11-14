import pytest
from sqlalchemy import select
from .test_issue_archive import bundle
from .test_issue_journal import ready
from .test_identity_http_trial import trial,headers
from .conftest import CASE
from mcis_service.investigation import archive,journal
from mcis_service.identity import local
URL=f'/api/v1/trial/cases/{CASE}/issue-archives'

def test_complete_archive_http(bundle):
    v,original=bundle;t,_,_,token,_=v
    with trial(t) as api:
        exported=api.get(URL+'/export',headers=headers(token))
        assert exported.status_code==200 and exported.content==original
        assert exported.headers['content-disposition'].startswith('attachment;')
        digest,_=archive.validate(exported.content)
        restored=api.post(URL+'/import',headers=headers(token),content=exported.content)
        assert restored.status_code==200 and restored.json()['activated'] is False
        assert api.post(URL+'/import',headers=headers(token),content=exported.content).json()['replayed']
        listed=api.get(URL,headers=headers(token));read=api.get(URL+'/'+digest,headers=headers(token))
        assert listed.json()['items'][0]['sha256']==digest
        assert read.json()['payload']['cards'][0]['events'][0]['note']=='初步判断'
        assert read.json()['status']=='imported_history_untrusted' and token not in read.text
        assert read.headers['cache-control']=='no-store'

@pytest.mark.parametrize('extra',[{'Origin':'https://evil'},{'Cookie':'x=y'},{'X-MCIS-Role':'LeadInvestigator'},{'Content-Encoding':'gzip'}])
def test_bad_transport(bundle,extra):
    v,raw=bundle
    with trial(v[0]) as api:r=api.post(URL+'/import',headers={**headers(v[3]),**extra},content=raw)
    assert r.status_code==400

@pytest.mark.parametrize('data',[b'{}',b'{"a":1,"a":2}',b'null',b'\xff'])
def test_invalid_data_no_mutation(bundle,data):
    v,_=bundle
    with trial(v[0]) as api:r=api.post(URL+'/import',headers=headers(v[3]),content=data)
    assert r.status_code==422
    with v[0].app.state.db.session() as s:assert list(s.scalars(select(archive.ImportedArchive)))==[]

def test_revoked_grant_and_session(bundle):
    v,raw=bundle;t,_,sub,token,_=v
    with t.app.state.db.session() as s:journal.grant(s,sub,CASE,enabled=False)
    with trial(t) as api:
        assert api.post(URL+'/import',headers=headers(token),content=raw).status_code==403
        assert api.get(URL+'/export',headers=headers(token)).status_code==200
        with t.app.state.db.session() as s:local.revoke_session(s,token)
        assert api.get(URL,headers=headers(token)).status_code==403

@pytest.mark.parametrize('suffix,method',[('/import','get'),('/export','post'),('/','get'),('?x=1','get'),('/bad','get'),('','delete')])
def test_exact_route(bundle,suffix,method):
    v,_=bundle
    with trial(v[0]) as api:r=getattr(api,method)(URL+suffix,headers=headers(v[3]))
    assert r.status_code==404
