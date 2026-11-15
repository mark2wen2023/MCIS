"""Ordinary synthetic observations and registry evolution; no original files."""
import copy
import pytest
from mcis_service.db import put_doc
from mcis_service.timeline.models import ConflictRow
from mcis_service.evidence.models import EvidenceRow
from .test_working_record_archive import client_at,ROOT,CID,HEAD
from .test_conflict_archive_readiness import body
from .test_consultation_archive_readiness import state
from .conftest import H


def token(c):
    result=c.get(ROOT+'/conflicts:editable',headers=HEAD);assert result.status_code==200
    return result.json()[0]['version']


@pytest.mark.parametrize('side', ['a','b'])
def test_changed_side_rejected_current_history_audit_unchanged(tmp_path,side):
    with client_at(tmp_path/'c',True) as c:
        value=body(); assert c.post(ROOT+'/conflicts',headers=HEAD,json=value).status_code==201
        saved=state(c); edited=copy.deepcopy(value); edited[side]['valueText']='Synthetic changed'
        result=c.post(ROOT+'/conflicts',headers=HEAD,json={**edited,'expectedVersion':token(c)})
        assert result.status_code==409 and result.json()['code']=='CONFLICT_SOURCE_REVIEW_REQUIRED'
        assert state(c)==saved


def test_unchanged_sides_post_and_investigator_patch_keep_binding(tmp_path):
    with client_at(tmp_path/'c',True) as c:
        value=body(); assert c.post(ROOT+'/conflicts',headers=HEAD,json=value).status_code==201
        result=c.post(ROOT+'/conflicts',headers=HEAD,json={**value,'resolution':'Synthetic note','expectedVersion':token(c)})
        assert result.status_code==201
        result=c.patch(ROOT+'/conflicts/C-01',headers=H('Investigator','Synthetic'),json={'expectedVersion':token(c),'resolution':'Synthetic allowed note','status':'Annotated'})
        assert result.status_code==200
        revisions=c.get(ROOT+'/conflicts/C-01/revisions',headers=HEAD)
        assert revisions.status_code==200
        rows=revisions.json()['revisions']
        assert len(rows)==3 and all(r['afterSources']==rows[0]['afterSources'] for r in rows)


def test_legacy_note_never_binds_today_registry(tmp_path):
    with client_at(tmp_path/'c',True) as c:
        value=body();value['caseId']=CID;value['a']['evidenceId']='EV-A'
        with c.app.state.db.session() as s:
            put_doc(s,ConflictRow,CID,'C-01',value)
            put_doc(s,EvidenceRow,CID,'EV-A',{'caseId':CID,'evidenceId':'EV-A','sha256':'b'*64,'confidentiality':'Normal'})
        for text in ('Synthetic first note','Synthetic second note'):
            result=c.patch(ROOT+'/conflicts/C-01',headers=H('Investigator','Synthetic'),json={'expectedVersion':token(c),'resolution':text})
            assert result.status_code==200
        history=c.get(ROOT+'/conflicts/C-01/revisions',headers=HEAD)
        assert history.status_code==200
        doc=history.json();assert doc['coverage']=='unknown-before-capture'
        assert doc['revisions'][0]['beforeSources'] is None
        for r in doc['revisions']:
            assert r['afterSources']['a']=={'evidenceId':'EV-A','status':'unresolved','bytesVerified':False}
            assert r['afterSources']['b']=={'evidenceId':None,'status':'unregistered','bytesVerified':False}
