"""Synthetic ordinary workflow tests; no historical security or ECFC probes."""
import hashlib
from sqlalchemy import select
from mcis_service.timeline.origin import TimelineImportOrigin
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from .test_working_record_archive import client_at, checked, ROOT, CID, snapshot
from .test_bounded_timeline_archive_increment import populate, exported, commit, rows


def origins(c, suffix=''):
    return checked(c, 'get', ROOT+'/timeline'+suffix).json()['eventOrigins']


def add(c, key='TE-03'):
    return checked(c, 'post', ROOT+'/timeline/events', {'eventId':key,'timeSec':3,
        'title':'Synthetic declared event','kind':'Observation','confirmed':True,'presumptive':True},201).json()


def test_restore_mixed_and_second_generation(tmp_path):
    with client_at(tmp_path/'a',True) as a:
        populate(a);add(a)
        assert all(v == {'status':'unavailable'} for v in origins(a).values())
        initial=rows(a);raw=exported(a)
    with client_at(tmp_path/'b') as b:
        commit(b,raw);assert rows(b)==initial
        before=origins(b)
        assert all(v['status']=='restored-history' and v['sourcePackageSha256']==hashlib.sha256(raw).hexdigest() for v in before.values())
        add(b,'TE-04');assert origins(b)['TE-04']=={'status':'unavailable'}
        assert origins(b)['TE-03']==before['TE-03']
        assert set(origins(b,'?fromSec=3'))=={'TE-03','TE-04'}
        raw2=exported(b)
    with client_at(tmp_path/'c') as c:
        commit(c,raw2)
        after=origins(c)
        assert after['TE-03']['rowSha256']==before['TE-03']['rowSha256']
        assert all(v['sourcePackageSha256']==hashlib.sha256(raw2).hexdigest() for v in after.values())
        assert after['TE-04']['status']=='restored-history'
        from mcis_service.package.mcase import read_zip
        raw3=exported(c)
        assert raw in read_zip(raw3).values() and raw2 in read_zip(raw3).values()
        assert checked(c,'get',ROOT+'/audit:verify').json()['valid']


def test_pre_index_database_missing_source_stays_unknown(tmp_path,monkeypatch):
    # Model the prior importer, which saved valid1.4 packages but no local index.
    import mcis_service.timeline.origin as origin
    with client_at(tmp_path/'a',True) as a:
        populate(a);raw=exported(a)
    with client_at(tmp_path/'b') as b:
        with monkeypatch.context() as m:
            m.setattr(origin,'record',lambda *args:None)
            commit(b,raw)
        assert all(v=={'status':'unavailable'} for v in origins(b).values())
        raw2=exported(b)
    with client_at(tmp_path/'c') as c:
        commit(c,raw2)
        assert all(v['status']=='restored-history' for v in origins(c).values())


def test_other_case_same_id_never_inherits_origin(tmp_path):
    with client_at(tmp_path/'a',True) as a:
        populate(a);raw=exported(a)
    with client_at(tmp_path/'b') as b:
        commit(b,raw)
        with b.app.state.db.session() as s:
            original=s.scalars(select(CaseRow).where(CaseRow.case_id==CID)).one().doc
            put_doc(s,CaseRow,'OTHER','OTHER',{**original,'caseId':'OTHER'})
        checked(b,'post','/api/v1/cases/OTHER/timeline/events',{'eventId':'TE-01','timeSec':1,'kind':'Event','title':'Other synthetic event'},201)
        result=checked(b,'get','/api/v1/cases/OTHER/timeline').json()
        assert result['eventOrigins']=={'TE-01':{'status':'unavailable'}}
        assert origins(b)['TE-01']['status']=='restored-history'


def test_index_failure_rolls_back_case_and_rows(tmp_path,monkeypatch):
    import mcis_service.timeline.origin as origin
    with client_at(tmp_path/'a',True) as a:
        populate(a);raw=exported(a)
    with client_at(tmp_path/'b') as b:
        before=snapshot(b);record=origin.record
        def failure(*args):
            record(*args)
            raise RuntimeError('SYNTHETIC_INDEX_FAILURE')
        monkeypatch.setattr(origin,'record',failure)
        commit(b,raw,500)
        assert snapshot(b)==before and rows(b)==[]
        with b.app.state.db.session() as s:
            assert list(s.scalars(select(TimelineImportOrigin)))==[]
        assert not (b.app.state.settings.blob_dir/CID).exists()


def test_legacy_package_no_timeline_origin_and_public_still_denied(tmp_path):
    from .test_package_intake_parser import base,pack
    from .conftest import H
    with client_at(tmp_path/'legacy') as c:
        commit(c,pack(base()))
        assert origins(c)=={}
        add(c)
        assert origins(c)=={'TE-03':{'status':'unavailable'}}
        before=snapshot(c)
        response=checked(c,'get',ROOT+'/timeline',status=403,headers=H('Public','Synthetic'))
        assert 'eventOrigins' not in response.json()
        assert snapshot(c)==before


def test_derived_cache_export_validation_fails_closed(monkeypatch):
    # Pure constructed cache inputs, not mutations of historical reports/audits.
    from types import SimpleNamespace
    import pytest
    from fastapi import HTTPException
    import mcis_service.timeline.origin as origin
    raw=b'synthetic bytes for unit-only dependency stub'
    sha=hashlib.sha256(raw).hexdigest()
    row=SimpleNamespace(event_id='TE-01',row_sha256='a'*64,package_sha256=sha)
    session=SimpleNamespace(scalars=lambda query:iter([row]))
    import mcis_service.package.mcase as mcase
    monkeypatch.setattr(mcase,'read_zip',lambda _: {})
    monkeypatch.setattr(origin,'source_rows',lambda *args:{'TE-01':'a'*64})
    origin.validate_export(session,CID,raw,sha)
    for source, digest in [(None,None),(raw,'b'*64)]:
        with pytest.raises(HTTPException) as exc:
            origin.validate_export(session,CID,source,digest)
        assert exc.value.status_code==409
    monkeypatch.setattr(origin,'source_rows',lambda *args:{'TE-OTHER':'a'*64})
    with pytest.raises(HTTPException) as exc:
        origin.validate_export(session,CID,raw,sha)
    assert exc.value.status_code==409
