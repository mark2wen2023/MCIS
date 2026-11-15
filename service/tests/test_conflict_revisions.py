"""Synthetic ordinary API/concurrency/rollback; no historical-security probes."""
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select
from mcis_service.db import put_doc
from mcis_service.timeline.models import ConflictRow
from mcis_service.evidence.models import EvidenceRow
from mcis_service.evidence.service import append_custody
from .test_working_record_archive import client_at,checked,ROOT,CID
from .test_conflict_archive_readiness import body
from .test_consultation_archive_readiness import state
from .conftest import H


def history(c):return checked(c,'get',ROOT+'/conflicts/C-01/revisions').json()


def test_full_overwrite_and_long_revision_chain(tmp_path):
    with client_at(tmp_path/'a',True) as c:
        old=checked(c,'post',ROOT+'/conflicts',body('Synthetic old observation'),201).json()
        replacement=checked(c,'post',ROOT+'/conflicts',body('Synthetic replacement'),201).json()
        explanation='Synthetic unicode解释 '*500
        final=checked(c,'patch',ROOT+'/conflicts/C-01',{'resolution':explanation,'status':'Annotated'}).json()
        result=history(c);rs=result['revisions']
        assert result['coverage']=='captured-from-creation'
        assert len(rs)==3 and rs[0]['before'] is None
        assert rs[1]['before']==old and rs[1]['after']==replacement
        assert rs[2]['before']==replacement and rs[2]['after']==final
        assert rs[2]['after']['resolution']==explanation
        assert [r['revision'] for r in rs]==[1,2,3]
        assert rs[2]['previousSha256']==rs[1]['sha256']
        assert all(r['operator']=='Synthetic Recorder' and r['utc'] and r['auditSeq'] for r in rs)
        assert checked(c,'get',ROOT+'/conflicts/C-01/revisions').headers['cache-control']=='no-store'
        checked(c,'get',ROOT+'/export',status=409)


def test_legacy_baseline_is_unknown_not_invented(tmp_path):
    with client_at(tmp_path/'a',True) as c:
        legacy={**body(),'caseId':CID}
        with c.app.state.db.session() as s:put_doc(s,ConflictRow,CID,'C-01',legacy)
        assert history(c)['coverage']=='unknown-before-capture' and history(c)['revisions']==[]
        checked(c,'patch',ROOT+'/conflicts/C-01',{'resolution':'Synthetic later note'})
        result=history(c);first=result['revisions'][0]
        assert result['coverage']=='unknown-before-capture'
        assert first['before']==legacy and first['beforeSources'] is None


def test_source_version_kept_when_only_resolution_changes(tmp_path):
    with client_at(tmp_path/'a',True) as c:
        # Registry-only fixture: no file bytes or original verification claimed.
        with c.app.state.db.session() as s:
            put_doc(s,EvidenceRow,CID,'EV-001',{'caseId':CID,'evidenceId':'EV-001','sha256':'a'*64,'confidentiality':'Normal'})
        value=body();value['a']['evidenceId']='EV-001'
        checked(c,'post',ROOT+'/conflicts',value,201)
        with c.app.state.db.session() as s:
            append_custody(s,case_id=CID,evidence_id='EV-001',kind='Change',operator='Synthetic',role='LeadInvestigator',sha256='b'*64,previous_sha256='a'*64,detail='Synthetic registered version change')
        checked(c,'patch',ROOT+'/conflicts/C-01',{'resolution':'Synthetic note'})
        rs=history(c)['revisions']
        assert rs[0]['afterSources']['a']['sha256']=='a'*64
        assert rs[1]['afterSources']['a']==rs[0]['afterSources']['a']
        value['a']['valueText']='Synthetic newly observed value'
        checked(c,'post',ROOT+'/conflicts',value,201)
        newest=history(c)['revisions'][-1]['afterSources']['a']
        assert newest['sha256']=='b'*64 and newest['bytesVerified'] is False
        assert newest['custodyHeadSeq'] is not None


def test_failure_rolls_back_row_revision_and_audit(tmp_path,monkeypatch):
    from mcis_service.timeline import revisions
    with client_at(tmp_path/'a',True) as c:
        checked(c,'post',ROOT+'/conflicts',body(),201);before=state(c)
        original=revisions.capture
        def fail(*args):
            original(*args)
            raise RuntimeError('SYNTHETIC_REVISION_FAILURE')
        monkeypatch.setattr(revisions,'capture',fail)
        checked(c,'patch',ROOT+'/conflicts/C-01',{'resolution':'Synthetic failed'},500)
        assert state(c)==before


def test_concurrent_same_id_updates_keep_all_preimages(tmp_path):
    with client_at(tmp_path/'a',True) as c:
        checked(c,'post',ROOT+'/conflicts',body(),201)
        def update(n):
            return checked(c,'patch',ROOT+'/conflicts/C-01',{'resolution':f'Synthetic {n}'}).json()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results=list(executor.map(update,range(2)))
        rs=history(c)['revisions'];assert len(rs)==3
        assert {r['after']['resolution'] for r in rs[1:]}=={r['resolution'] for r in results}
        assert rs[2]['before']==rs[1]['after']
        assert checked(c,'get',ROOT+'/audit:verify').json()['valid']


def test_history_requires_existing_full_content_permission_and_case(tmp_path):
    with client_at(tmp_path/'a',True) as c:
        checked(c,'post',ROOT+'/conflicts',body(),201)
        for role in ('Investigator','Public'):
            checked(c,'get',ROOT+'/conflicts/C-01/revisions',status=403,headers=H(role,'Synthetic'))
        checked(c,'get','/api/v1/cases/OTHER/conflicts/C-01/revisions',status=404)
