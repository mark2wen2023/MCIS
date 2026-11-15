"""Synthetic ordinary profile-selection regressions; no restricted probes."""
import hashlib,json
from sqlalchemy import select,func
from mcis_service.package.mcase import read_zip
from mcis_service.reports.models import ReportRow
from .test_working_record_archive import client_at,checked,ROOT,CID,snapshot
from .test_bounded_timeline_archive_increment import exported,commit,rows
from .conftest import H


def event(c):
    checked(c,'post',ROOT+'/timeline/events',{'eventId':'TE-01','timeSec':1,
        'kind':'Observation','title':'Synthetic timeline-only declaration',
        'confirmed':True,'presumptive':True,'sourceLabel':'Synthetic source, not independently verified'},201)


def test_timeline_only_two_restores_preserve_rows_sources_and_audit(tmp_path):
    with client_at(tmp_path/'a',True) as a:
        event(a)
        with a.app.state.db.session() as s:
            assert s.scalar(select(func.count()).select_from(ReportRow))==0
        original=rows(a);raw=exported(a);files=read_zip(raw)
        assert json.loads(files['manifest.json'])['packageVersion']=='1.4.0'
        first_audit=files['audit/audit.jsonl']
    with client_at(tmp_path/'b') as b:
        commit(b,raw);assert rows(b)==original
        origin=checked(b,'get',ROOT+'/timeline').json()['eventOrigins']['TE-01']
        assert origin['status']=='restored-history'
        assert origin['sourcePackageSha256']==hashlib.sha256(raw).hexdigest()
        raw2=exported(b);files2=read_zip(raw2)
        assert raw in files2.values()
        assert files2['audit/audit.jsonl'].startswith(first_audit)
        assert files2['timeline/records.v1.json']==files['timeline/records.v1.json']
    with client_at(tmp_path/'c') as c:
        commit(c,raw2);assert rows(c)==original
        current=checked(c,'get',ROOT+'/timeline').json()['eventOrigins']['TE-01']
        assert current['sourcePackageSha256']==hashlib.sha256(raw2).hexdigest()
        assert current['rowSha256']==origin['rowSha256']
        assert checked(c,'get',ROOT+'/audit:verify').json()['valid']
        files3=read_zip(exported(c))
        assert raw in files3.values() and raw2 in files3.values()
        assert files3['audit/audit.jsonl'].startswith(files2['audit/audit.jsonl'])


def test_timeline_plus_unsupported_state_refuses_without_partial_package(tmp_path):
    with client_at(tmp_path/'a',True) as a:
        event(a)
        checked(a,'post',ROOT+'/recommendations',{'title':'Synthetic','addressee':'Synthetic',
            'causeNodeIds':['SYN'],'dueUtc':'2099-01-01T00:00:00Z'},201)
        before=snapshot(a)
        response=checked(a,'get',ROOT+'/export',status=409)
        assert response.json()['code']=='ARCHIVE_RESTORE_UNSUPPORTED'
        assert not response.content.startswith(b'PK')
        assert snapshot(a)==before


def test_timeline_only_keeps_full_content_permission_gate(tmp_path):
    with client_at(tmp_path/'a',True) as a:
        event(a);before=snapshot(a)
        for role in ('Investigator','Public'):
            response=checked(a,'get',ROOT+'/export',status=403,headers=H(role,'Synthetic'))
            assert not response.content.startswith(b'PK')
        assert snapshot(a)==before


def test_empty_case_remains_legacy_roundtrippable(tmp_path):
    with client_at(tmp_path/'a',True) as a:
        raw=exported(a)
        assert json.loads(read_zip(raw)['manifest.json'])['packageVersion']=='1.0.0'
    with client_at(tmp_path/'b') as b:
        commit(b,raw)
        assert checked(b,'get',ROOT+'/timeline').json()['events']==[]
