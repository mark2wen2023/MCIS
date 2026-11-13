import time
import pytest
from fastapi import HTTPException
from sqlalchemy import select, func
from .test_internal_unreviewed_save import setup, counts, OP
from .conftest import CASE,C,H,make_settings
from .test_archive_generation_boundary import upload
from mcis_service.identity import local as auth
from mcis_service.timeline import unreviewed_storage as storage


def provision(target):
    with target.app.state.db.session() as s:
        subject=auth.create_subject(s)
        token=auth.issue_session(s,subject)
        auth.set_membership(s,subject,CASE,role='LeadInvestigator',can_save_unreviewed=True)
    return subject,token


def call(target,body,token):
    return storage.save_authenticated_unreviewed(target.app.state.db,target.app.state.settings,token,CASE,body,OP)


def test_save_replay_actor_from_store(client,empty_client,monkeypatch):
    target,_,body=setup(client,empty_client,monkeypatch);subject,token=provision(target)
    one=call(target,body,token);two=call(target,body,token)
    assert two['replayed'] and two['runId']==one['runId']
    assert counts(target)==(1,1)
    with target.app.state.db.session() as s:
        from mcis_service.audit.service import all_lines
        assert any('"operator":"'+subject+'"' in x.replace(' ','') for x in all_lines(s,CASE))
        assert token not in ''.join(all_lines(s,CASE))


@pytest.mark.parametrize('bad',['',None,'LeadInvestigator','X-MCIS-Role: LeadInvestigator','a'*43])
def test_fake_tokens_denied(client,empty_client,monkeypatch,bad):
    target,_,body=setup(client,empty_client,monkeypatch);provision(target)
    with pytest.raises(HTTPException) as error:call(target,body,bad)
    assert error.value.status_code==403 and counts(target)==(0,0)


@pytest.mark.parametrize('change',['session','subject','expiry','membership','grant','role','regrant'])
@pytest.mark.parametrize('stage',['before','during','replay'])
def test_current_and_midflight_authority(client,empty_client,monkeypatch,change,stage):
    target,_,body=setup(client,empty_client,monkeypatch);subject,token=provision(target)
    def mutate():
        with target.app.state.db.session() as s:
            if change=='session':auth.revoke_session(s,token)
            elif change=='subject':auth.disable_subject(s,subject)
            elif change=='expiry':
                auth.begin(s);row=s.scalar(select(auth.SessionRecord));row.expires_at=int(time.time())-1
            else:
                args={'role':'LeadInvestigator','can_save_unreviewed':True}
                if change=='membership':args['enabled']=False
                if change=='grant':args['can_save_unreviewed']=False
                if change=='role':args['role']='Investigator'
                auth.set_membership(s,subject,CASE,**args)
    if stage=='replay':call(target,body,token)
    if stage=='during':
        original=storage.preview_alignment
        def compute(*args):
            result=original(*args);mutate();return result
        monkeypatch.setattr(storage,'preview_alignment',compute)
    else:mutate()
    # Current valid grant updates before a NEW attempt are allowed. They are not
    # allowed to silently change authority across a running computation.
    if change=='regrant' and stage=='before':
        assert call(target,body,token)['saved'];return
    if change=='regrant' and stage=='replay':
        assert call(target,body,token)['replayed'];return
    with pytest.raises(HTTPException) as error:call(target,body,token)
    assert error.value.status_code in (403,409)
    assert counts(target)==((1,1) if stage=='replay' else (0,0))


def test_archive_carries_no_local_identity(client,empty_client,tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from mcis_service.main import create_app
    target,_,body=setup(client,empty_client,monkeypatch);subject,token=provision(target)
    call(target,body,token)
    package=target.get(C+'/export',headers=H('LeadInvestigator'));assert package.status_code==200,package.text
    assert token.encode() not in package.content
    with TestClient(create_app(make_settings(tmp_path/'restored',seed=False))) as restored:
        assert upload(restored,package.content).status_code==200
        with restored.app.state.db.session() as s:
            for model in (auth.Subject,auth.SessionRecord,auth.Membership):
                assert s.scalar(select(func.count()).select_from(model))==0
        with pytest.raises(HTTPException):call(restored,body,token)
