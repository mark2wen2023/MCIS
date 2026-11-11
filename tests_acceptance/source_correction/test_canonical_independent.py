"""Run only in explicitly named canonical snapshot; no fallback to old workspace."""
import os,sys,hashlib,shutil
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
EXPECTED=Path(os.environ['MCIS_CANONICAL_SNAPSHOT']).resolve()
sys.path.insert(0,str(EXPECTED/'service'))
from mcis_service.config import PROJECT_ROOT, Settings
from mcis_service.main import create_app
from mcis_service.seed import yangze22 as seed
from mcis_service.reports import public_text
from mcis_service.reports.templates import get_template
from mcis_service.db import get_doc
from mcis_service.evidence.models import EvidenceRow
from mcis_service.evidence import service as ev
SHA='bca8f8b8ba04a5d0669a121bc6c9380c8cd6f8397f67be2d0b30b38871c22ef2'
BLOB='d5a6b5fc79ad0371c8ccc372b40ca9110d5c30c4'
H={'X-MCIS-Role':'Investigator'}
@pytest.fixture()
def client(tmp_path):
    assert PROJECT_ROOT.resolve()==EXPECTED
    assert Path(seed.__file__).resolve().is_relative_to(EXPECTED)
    assert Path(public_text.__file__).resolve().is_relative_to(EXPECTED)
    with TestClient(create_app(Settings(data_dir=tmp_path,db_url=f'sqlite:///{tmp_path}/fresh.db',seed_demo=True))) as c:yield c

def test_exact_original_and_custody(client):
    raw=(EXPECTED/'reports/yangze22/report.txt').read_bytes()
    assert len(raw)==62607 and hashlib.sha256(raw).hexdigest()==SHA
    assert hashlib.sha1(b'blob 62607\0'+raw).hexdigest()==BLOB
    with client.app.state.db.session() as s:
        item=get_doc(s,EvidenceRow,seed.CASE_ID,'EV-201')
        stored=(client.app.state.settings.blob_dir/seed.CASE_ID/item['relativePath']).read_bytes()
        assert item['sha256']==SHA and stored==raw
        events=ev.custody_events(s,seed.CASE_ID,'EV-201')
        assert events and all(e.sha256==SHA for e in events)
    assert client.get(f'/api/v1/cases/{seed.CASE_ID}/audit:verify',headers=H).json()['valid']
    excerpts=public_text.excerpts({'caseId':seed.CASE_ID,'isFictionalDemo':False},get_template('cn-msa',seed.CASE_ID))
    assert excerpts and all(SHA in x['sourceRef'] for x in excerpts.values())
    lines=raw.decode().split('\n')
    for x in excerpts.values():assert x['quote']=='\n'.join(lines[x['lineStart']-1:x['lineEnd']])

def test_one_lf_is_not_normalized(tmp_path):
    source=tmp_path/'reports/yangze22';source.mkdir(parents=True)
    for name in ('case.json','report.txt'):shutil.copy(EXPECTED/'reports/yangze22'/name,source/name)
    (source/'report.txt').write_bytes((source/'report.txt').read_bytes()+b'\n')
    with pytest.raises(ValueError,match='checksum mismatch'):seed.load_source(source)
    assert public_text.excerpts({'caseId':seed.CASE_ID,'isFictionalDemo':False},get_template('cn-msa',seed.CASE_ID),tmp_path)=={}

@pytest.mark.parametrize('template',['imo-cic','maib','cn-msa'])
def test_fresh_yangze_all_templates_pdf_docx(client,template):
    base=f'/api/v1/cases/{seed.CASE_ID}'
    r=client.post(base+'/reports',headers=H,json={'templateId':template,'lang':'bilingual'})
    assert r.status_code==201,r.text
    doc=r.json();assert doc['realDataStatus']=='authorized-public' and doc['isFictionalDemo'] is False
    rid=doc['reportId']
    for fmt,magic in [('pdf',b'%PDF'),('docx',b'PK')]:
        out=client.get(base+f'/reports/{rid}/export?format={fmt}&lang=bilingual',headers=H)
        assert out.status_code==200,out.text[:100] if out.status_code!=200 else ''
        assert out.content.startswith(magic) and out.headers['x-sha256']==hashlib.sha256(out.content).hexdigest()
