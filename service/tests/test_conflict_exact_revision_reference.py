"""Ordinary synthetic exact lookup, not tamper/permission/security probes."""
import json
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator
from .test_working_record_archive import client_at,ROOT,HEAD,CID
from .test_conflict_source_receipt_submit import seed,prepare,change


def test_exact_reference_survives_registry_and_observation_updates(tmp_path):
    with client_at(tmp_path/'c',True) as c:
        original=seed(c);request,_=prepare(c,original)
        saved=c.post(ROOT+'/conflicts',headers=HEAD,json=request)
        assert saved.status_code==201
        history=c.get(ROOT+'/conflicts/C-01/revisions',headers=HEAD)
        assert history.status_code==200
        old=history.json()['revisions'][-1]
        url=ROOT+'/conflicts/C-01/revisions/2?sha256='+old['sha256']
        first=c.get(url,headers=HEAD)
        assert first.status_code==200,first.text
        schema=json.loads((Path(__file__).resolve().parents[2]/'contracts/schemas/conflict-revision-reference.schema.json').read_text())
        Draft202012Validator(schema).validate(first.json()['reference'])
        assert first.headers['cache-control']=='no-store'
        assert first.json()['revision']==old
        assert first.json()['bytesVerified'] is False
        change(c,'EV-A')
        current=saved.json();current['a']['valueText']='Synthetic next observation'
        version=c.get(ROOT+'/conflicts:editable',headers=HEAD).json()[0]['version']
        receipt=c.post(ROOT+'/conflicts/C-01/source-receipts',headers=HEAD,json={
            'expectedVersion':version,'observations':{k:current[k] for k in ('a','b')}})
        assert receipt.status_code==201,receipt.text
        new=c.post(ROOT+'/conflicts',headers=HEAD,json={**current,'expectedVersion':version,'sourceReceiptId':receipt.json()['receiptId']})
        assert new.status_code==201,new.text
        after=c.get(url,headers=HEAD)
        assert after.status_code==200 and after.json()==first.json()
        assert after.json()['revision']['afterSources']['a']['sha256']=='a'*64
        latest=c.get(ROOT+'/conflicts/C-01/revisions',headers=HEAD).json()['revisions'][-1]
        assert latest['revision']==3 and latest['afterSources']['a']['sha256']=='b'*64


@pytest.mark.parametrize('revision,digest,status',[(99,'a'*64,404),(1,'f'*64,409),(0,'a'*64,422),(1,'invalid',422)])
def test_missing_or_inapplicable_reference_never_returns_latest(tmp_path,revision,digest,status):
    with client_at(tmp_path/'c',True) as c:
        seed(c)
        r=c.get(ROOT+f'/conflicts/C-01/revisions/{revision}?sha256={digest}',headers=HEAD)
        assert r.status_code==status,r.text
        assert 'revision' not in r.json()


def test_legacy_current_record_does_not_invent_revision(tmp_path):
    from mcis_service.db import put_doc
    from mcis_service.timeline.models import ConflictRow
    from .test_conflict_archive_readiness import body
    with client_at(tmp_path/'c',True) as c:
        with c.app.state.db.session() as s:put_doc(s,ConflictRow,CID,'C-01',{**body(),'caseId':CID})
        h=c.get(ROOT+'/conflicts/C-01/revisions',headers=HEAD)
        assert h.status_code==200 and h.json()['coverage']=='unknown-before-capture'
        r=c.get(ROOT+'/conflicts/C-01/revisions/1?sha256='+'a'*64,headers=HEAD)
        assert r.status_code==404 and r.json()['code']=='CONFLICT_REVISION_NOT_CAPTURED'
