"""Ordinary synthetic subset of existing 7aa9b9f candidate; no restricted integrity probes."""
import base64, hashlib, json
import pytest
from sqlalchemy import select
from .test_working_record_archive import client_at,checked,CID,ROOT,HEAD,snapshot
from mcis_service.timeline.models import TimelineEventRow
from mcis_service.package.mcase import read_zip


def populate(c):
    report=checked(c,'post',ROOT+'/reports',{'templateId':'cn-msa','lang':'en'},201).json()
    for n in (2,1):
        checked(c,'post',ROOT+'/timeline/events',{'eventId':f'TE-{n:02}','timeSec':n,'endTimeSec':n+0.5,'kind':'Event','title':f'Synthetic {n}', 'sourceLabel':'Synthetic unverified source','confirmed':False},201)
    return report


def rows(c):
    with c.app.state.db.session()as s:
        return [(r.key,r.created_utc,r.updated_utc,r.doc)for r in s.scalars(select(TimelineEventRow).where(TimelineEventRow.case_id==CID).order_by(TimelineEventRow.key))]


def exported(c):return checked(c,'get',ROOT+'/export').content


def commit(c,raw,status=200):
    return checked(c,'post','/api/v1/packages/intakes:commit',{'contentBase64':base64.b64encode(raw).decode(),'confirmed':True,'sourceSha256':hashlib.sha256(raw).hexdigest()},status)


def test_three_store_exact_rows_audit_and_source(tmp_path):
    with client_at(tmp_path/'a',True)as a:
        report=populate(a);before=rows(a);raw=exported(a)
        assert json.loads(read_zip(raw)['manifest.json'])['packageVersion']=='1.4.0'
        original_audit=read_zip(raw)['audit/audit.jsonl']
        with client_at(tmp_path/'b')as b:
            preview=checked(b,'post','/api/v1/packages/intakes:preview',{'contentBase64':base64.b64encode(raw).decode()}).json()
            assert preview['packageVersion']=='1.4.0'
            commit(b,raw);assert rows(b)==before
            assert checked(b,'get',ROOT+'/reports/'+report['reportId']).json()==report
            raw2=exported(b);assert read_zip(raw2)['audit/audit.jsonl'].startswith(original_audit)
            assert raw in read_zip(raw2).values()
            with client_at(tmp_path/'c')as c:
                commit(c,raw2);assert rows(c)==before
                raw3=exported(c);assert raw2 in read_zip(raw3).values()


def test_unknown_state_and_legacy_entry_still_rejected(tmp_path):
    with client_at(tmp_path/'a',True)as a:
        populate(a);raw=exported(a)
        checked(a,'post',ROOT+'/recommendations',{'title':'Synthetic','addressee':'Synthetic','causeNodeIds':['SYN'],'dueUtc':'2099-01-01T00:00:00Z'},201)
        before=snapshot(a);checked(a,'get',ROOT+'/export',status=409);assert snapshot(a)==before
    with client_at(tmp_path/'b')as b:
        before=snapshot(b)
        r=b.post('/api/v1/cases:import',files={'file':('synthetic.mcase',raw)},headers=HEAD)
        assert r.status_code==422;assert snapshot(b)==before


def test_evidence_reference_and_original_bytes_survive(tmp_path):
    from .test_working_record_archive import populate as with_evidence
    with client_at(tmp_path/'a',True)as a:
        data,evidence,*_=with_evidence(a)
        checked(a,'post',ROOT+'/timeline/events',{'timeSec':0,'kind':'Observation','title':'Synthetic source-linked event','evidenceIds':[evidence['evidenceId']]},201)
        before=rows(a);raw=exported(a)
        with client_at(tmp_path/'b')as b:
            commit(b,raw);assert rows(b)==before
            original=checked(b,'get',ROOT+'/archive-history/evidence/'+evidence['evidenceId']+'/content')
            assert original.content==data
            assert original.headers['x-sha256']==hashlib.sha256(data).hexdigest()
            assert exported(b).startswith(b'PK')


@pytest.mark.parametrize('seconds',[0.0001,1.2345])
def test_existing_api_submillisecond_values_preserved(tmp_path,seconds):
    with client_at(tmp_path/'a',True)as a:
        populate(a)
        checked(a,'post',ROOT+'/timeline/events',{'timeSec':seconds,'title':'Synthetic fractional time','kind':'Event'},201)
        before=rows(a);raw=exported(a)
        with client_at(tmp_path/'b')as b:
            commit(b,raw);assert rows(b)==before



def test_synthetic_post_restore_failure_rolls_back(tmp_path, monkeypatch):
    # Ordinary injected server failure, not a historical-integrity mutation probe.
    from mcis_service.working_records_archive import service
    with client_at(tmp_path/'source', True) as source:
        populate(source)
        raw = exported(source)
    with client_at(tmp_path/'restored') as restored:
        before = snapshot(restored)
        original = service.restore
        def fail_after_restore(*args, **kwargs):
            original(*args, **kwargs)
            raise RuntimeError('SYNTHETIC_POST_RESTORE_FAILURE')
        monkeypatch.setattr(service, 'restore', fail_after_restore)
        commit(restored, raw, 500)
        assert snapshot(restored) == before
        assert rows(restored) == []
        assert not (restored.app.state.settings.blob_dir/CID).exists()
