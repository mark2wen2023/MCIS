"""Synthetic API/SQLite timeline+report archives; faults explicitly injected."""
import base64,copy,hashlib,io,json,zipfile
import pytest
from sqlalchemy import select
from .test_working_record_archive import client_at,checked,CID,ROOT,HEAD,snapshot
from mcis_service.timeline.models import TimelineEventRow
from mcis_service.package.mcase import read_zip,manifest_json
from mcis_service.working_records_archive.timeline import PATH


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


def rewrite(raw,change):
    files=read_zip(raw);manifest=json.loads(files.pop('manifest.json'));change(files,manifest)
    files['manifest.json']=manifest_json(CID,files,manifest['createdAtUtc'],manifest['packageVersion']).encode()
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED)as z:
        for p,b in files.items():z.writestr(p,b)
    return out.getvalue()


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


@pytest.mark.parametrize('change',['case','key','duplicate','utc','end','vessel','evidence','unknown','mirror','outer','inner','missing','track-version','empty','timestamp','budget','missing-mirror','unknown-member','future'])
def test_invalid_zero_write(tmp_path,change):
    with client_at(tmp_path/'a',True)as a:
        populate(a);raw=exported(a)
    def mutate(files,m):
        data=json.loads(files[PATH]);r=data['events'][0];d=r['doc']
        if change=='case':d['caseId']='OTHER'
        if change=='key':r['key']='TE-99'
        if change=='duplicate':data['events'].append(copy.deepcopy(r))
        if change=='utc':d['utc']='2026-01-01T00:00:59Z'
        if change=='end':d['endTimeSec']=-1
        if change=='vessel':d['vesselId']='missing'
        if change=='evidence':d['evidenceIds']=['EV-999']
        if change=='unknown':data['unknown']=True
        if change=='inner':data['version']=99
        if change=='empty':data['events']=[]
        if change=='timestamp':r['createdUtc']='invalid'
        if change=='budget':data['events']=[copy.deepcopy(r) for _ in range(257)]
        if change=='future':m['packageVersion']='1.5.0'
        if change=='outer':m['packageVersion']='1.2.0'
        if change=='track-version':m['packageVersion']='1.3.0'
        files[PATH]=json.dumps(data).encode()
        files['analysis/timeline.json']=json.dumps({'events':[r['doc']for r in data['events']]}).encode()
        if change=='mirror':files['analysis/timeline.json']=b'{"events":[]}'
        if change=='missing':del files[PATH]
        if change=='missing-mirror':del files['analysis/timeline.json']
        if change=='unknown-member':files['timeline/unknown.json']=b'{}'
    bad=rewrite(raw,mutate)
    with client_at(tmp_path/'b')as b:
        before=snapshot(b);commit(b,bad,422);assert snapshot(b)==before
        assert not(b.app.state.settings.blob_dir/CID).exists()


def test_permission_and_post_restore_rollback(tmp_path,monkeypatch):
    from mcis_service.working_records_archive import service
    from .conftest import H
    with client_at(tmp_path/'a',True)as a:
        populate(a);raw=exported(a)
        checked(a,'get',ROOT+'/export',status=403,headers=H())
    with client_at(tmp_path/'b')as b:
        before=snapshot(b)
        checked(b,'post','/api/v1/packages/intakes:preview',{'contentBase64':base64.b64encode(raw).decode()},403,headers=H())
        original=service.restore
        def failed(*a,**kw):original(*a,**kw);raise RuntimeError('SYNTHETIC_AFTER_TIMELINE_RESTORE')
        monkeypatch.setattr(service,'restore',failed)
        commit(b,raw,500);assert snapshot(b)==before;assert rows(b)==[]
        assert not(b.app.state.settings.blob_dir/CID).exists()


def test_unknown_state_and_legacy_entry_still_rejected(tmp_path):
    with client_at(tmp_path/'a',True)as a:
        populate(a);raw=exported(a)
        checked(a,'post',ROOT+'/recommendations',{'title':'Synthetic','addressee':'Synthetic','causeNodeIds':['SYN'],'dueUtc':'2099-01-01T00:00:00Z'},201)
        before=snapshot(a);checked(a,'get',ROOT+'/export',status=409);assert snapshot(a)==before
    with client_at(tmp_path/'b')as b:
        before=snapshot(b)
        r=b.post('/api/v1/cases:import',files={'file':('synthetic.mcase',raw)},headers=HEAD)
        assert r.status_code==422;assert snapshot(b)==before


def test_revoke_waits_for_reserved_export_then_next_read_denied(tmp_path,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from mcis_service.working_records_archive import timeline
    from mcis_service.redaction.models import AccessPolicyRow
    from mcis_service.redaction.policy import default_policy
    from mcis_service.db import put_doc
    entered,release,revoking,revoked=Event(),Event(),Event(),Event()
    with client_at(tmp_path/'a',True)as a:
        populate(a);original=timeline.validate
        def held(*args,**kwargs):
            if not entered.is_set():
                entered.set();assert release.wait(5)
            return original(*args,**kwargs)
        monkeypatch.setattr(timeline,'validate',held)
        def revoke():
            policy=default_policy()
            policy['matrix']['LeadInvestigator']['timeline']='Deny'
            revoking.set()
            with a.app.state.db.session()as s:
                s.connection().exec_driver_sql('BEGIN IMMEDIATE')
                put_doc(s,AccessPolicyRow,CID,'policy',policy)
            revoked.set()
        with ThreadPoolExecutor(2)as pool:
            export=pool.submit(exported,a);assert entered.wait(5)
            revocation=pool.submit(revoke);assert revoking.wait(5)
            try:assert not revoked.wait(.1)
            finally:release.set()
            assert export.result(timeout=10).startswith(b'PK')
            revocation.result(timeout=10)
        before=snapshot(a);checked(a,'get',ROOT+'/export',status=403);assert snapshot(a)==before


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
