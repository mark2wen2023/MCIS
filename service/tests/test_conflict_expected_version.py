"""Synthetic same-identity stale-client tests; no restricted security probes."""
from concurrent.futures import ThreadPoolExecutor
import pytest
from mcis_service.db import put_doc
from mcis_service.timeline.models import ConflictRow
from .test_working_record_archive import client_at,checked,ROOT,CID,HEAD
from .test_conflict_archive_readiness import body
from .test_consultation_archive_readiness import state


def read(c):return checked(c,'get',ROOT+'/conflicts:editable').json()[0]


@pytest.mark.parametrize('legacy',[False,True])
def test_same_user_two_sessions_stale_save_refused(tmp_path,legacy):
    with client_at(tmp_path/'a',True) as c:
        if legacy:
            with c.app.state.db.session() as s:put_doc(s,ConflictRow,CID,'C-01',{**body(),'caseId':CID})
        else:checked(c,'post',ROOT+'/conflicts',body(),201)
        a,b=read(c),read(c);assert a==b
        checked(c,'patch',ROOT+'/conflicts/C-01',{'resolution':'Synthetic A','expectedVersion':a['version']})
        before=state(c)
        r=checked(c,'patch',ROOT+'/conflicts/C-01',{'resolution':'Synthetic B stale','expectedVersion':b['version']},412)
        assert r.json()['code']=='CONFLICT_VERSION_CHANGED' and state(c)==before
        assert read(c)['conflict']['resolution']=='Synthetic A'
        new=read(c)
        checked(c,'patch',ROOT+'/conflicts/C-01',{'resolution':'Synthetic compared B','expectedVersion':new['version']})
        coverage=checked(c,'get',ROOT+'/conflicts/C-01/revisions').json()['coverage']
        assert coverage==('unknown-before-capture' if legacy else 'captured-from-creation')


def test_legacy_client_missing_token_and_same_id_post_cannot_bypass(tmp_path):
    with client_at(tmp_path/'a',True) as c:
        checked(c,'post',ROOT+'/conflicts',body(),201);before=state(c)
        checked(c,'patch',ROOT+'/conflicts/C-01',{'resolution':'No version'},428)
        checked(c,'post',ROOT+'/conflicts',body('Old client overwrite'),428)
        checked(c,'patch',ROOT+'/conflicts/C-01',{'resolution':'Invalid','expectedVersion':'*'},422)
        assert state(c)==before
        token=read(c)['version']
        checked(c,'post',ROOT+'/conflicts',{**body('Versioned replacement'),'expectedVersion':token},201)
        before=state(c)
        checked(c,'post',ROOT+'/conflicts',{**body('Stale replacement'),'expectedVersion':token},412)
        assert state(c)==before


def test_aba_and_concurrent_reuse_rejected(tmp_path):
    with client_at(tmp_path/'a',True) as c:
        checked(c,'post',ROOT+'/conflicts',body(),201);first=read(c)
        checked(c,'post',ROOT+'/conflicts',{**body('Other'),'expectedVersion':first['version']},201)
        checked(c,'post',ROOT+'/conflicts',{**body(),'expectedVersion':read(c)['version']},201)
        assert read(c)['conflict']==first['conflict'] and read(c)['version']!=first['version']
        checked(c,'patch',ROOT+'/conflicts/C-01',{'resolution':'stale ABA','expectedVersion':first['version']},412)
        token=read(c)['version']
        def save(n):return c.patch(ROOT+'/conflicts/C-01',headers=HEAD,json={'resolution':f'Synthetic {n}','expectedVersion':token})
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(save,range(2)))
        assert sorted(r.status_code for r in results)==[200,412]
        assert len(checked(c,'get',ROOT+'/conflicts/C-01/revisions').json()['revisions'])==4
