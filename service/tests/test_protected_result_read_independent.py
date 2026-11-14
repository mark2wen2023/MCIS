"""Independent probes: authenticated result retrieval, not live network/LLM."""
import json
import pytest
from sqlalchemy import select
from .test_internal_unreviewed_save import setup, counts, OP
from .test_local_authority import provision
from .test_identity_http_trial_independent import invoke, check
from .conftest import C, CASE
from mcis_service.identity import local, http_trial as http
from mcis_service.timeline import unreviewed_storage as storage
from mcis_service.redaction.models import AccessPolicyRow


def saved(client,empty_client,monkeypatch):
    target,_,body=setup(client,empty_client,monkeypatch)
    subject,token=provision(target)
    result=storage.save_authenticated_unreviewed(target.app.state.db,target.app.state.settings,token,CASE,body,OP)
    return target,subject,token,C+'/timeline/unreviewed-runs/'+result['runId']


def test_read_membership_not_save_grant_no_recompute(client,empty_client,monkeypatch):
    target,subject,token,path=saved(client,empty_client,monkeypatch)
    with target.app.state.db.session() as s:
        local.set_membership(s,subject,CASE,role='LeadInvestigator',can_save_unreviewed=False)
    before=counts(target)
    monkeypatch.setattr(storage,'preview_alignment',lambda *_:pytest.fail('read recomputed'))
    sent,reads=invoke(target,token,path=path,method='GET')
    check(sent,200);assert not reads and counts(target)==before
    result=json.loads(sent[1]['body'])
    assert result['status']=='unreviewed' and not result['usableAsWriteCredential']
    assert 'operationId' not in result and 'operator' not in result and token.encode() not in sent[1]['body']


@pytest.mark.parametrize('variant',['revoked','disabled','membership','expired','no-member'])
def test_authority_fail_closed(client,empty_client,monkeypatch,variant):
    target,subject,token,path=saved(client,empty_client,monkeypatch)
    with target.app.state.db.session() as s:
        if variant=='revoked':local.revoke_session(s,token)
        elif variant=='disabled':local.disable_subject(s,subject)
        elif variant=='membership':local.set_membership(s,subject,CASE,role='LeadInvestigator',enabled=False)
        elif variant=='expired':
            local.begin(s);s.scalar(select(local.SessionRecord)).expires_at=0
        else:token=local.issue_session(s,local.create_subject(s))
    sent,_=invoke(target,token,path=path,method='GET')
    check(sent,403);assert counts(target)==(1,1)


@pytest.mark.parametrize('variant',['auth-duplicate','fake-role-only','cookie','origin','length','transfer'])
def test_transport_denials(client,empty_client,monkeypatch,variant):
    target,_,token,path=saved(client,empty_client,monkeypatch)
    headers=[(b'authorization',('Bearer '+token).encode())]
    if variant=='auth-duplicate':headers*=2
    elif variant=='fake-role-only':headers=[(b'x-mcis-role',b'LeadInvestigator')]
    elif variant in ('cookie','origin'):headers.append((variant.encode(),b'bad'))
    elif variant=='length':headers.append((b'content-length',b'1'))
    else:headers.append((b'transfer-encoding',b'chunked'))
    sent,reads=invoke(target,token,path=path,method='GET',headers=headers)
    check(sent,400);assert not reads


def test_revoked_between_http_check_and_fetch(client,empty_client,monkeypatch):
    target,_,token,path=saved(client,empty_client,monkeypatch)
    original=http.read_authenticated_unreviewed
    def revoked(*args):
        with target.app.state.db.session() as s:local.revoke_session(s,token)
        return original(*args)
    monkeypatch.setattr(http,'read_authenticated_unreviewed',revoked)
    sent,_=invoke(target,token,path=path,method='GET');check(sent,403)


def test_source_policy_not_inferred_from_member(client,empty_client,monkeypatch):
    target,_,token,path=saved(client,empty_client,monkeypatch)
    with target.app.state.db.session() as s:
        local.begin(s);row=s.scalar(select(AccessPolicyRow).where(AccessPolicyRow.case_id==CASE))
        from mcis_service.redaction.policy import default_policy
        doc=default_policy() if row is None else json.loads(json.dumps(row.doc))
        doc['matrix']['LeadInvestigator']['evidence_meta']='Deny'
        if row is None:s.add(AccessPolicyRow(case_id=CASE,key='policy',doc=doc))
        else:row.doc=doc
    sent,_=invoke(target,token,path=path,method='GET');check(sent,403)


def test_unknown_read_error_is_sanitized(client,empty_client,monkeypatch):
    target,_,token,path=saved(client,empty_client,monkeypatch)
    def error(*_):raise RuntimeError('/secret '+token)
    monkeypatch.setattr(http,'read_authenticated_unreviewed',error)
    sent,_=invoke(target,token,path=path,method='GET');check(sent,503)
    assert token.encode() not in sent[1]['body'] and b'secret' not in sent[1]['body']


def test_missing_current_index_cannot_activate_audit(client,empty_client,monkeypatch):
    target,_,token,path=saved(client,empty_client,monkeypatch)
    with target.app.state.db.session() as s:
        local.begin(s);s.delete(s.scalar(select(storage.UnreviewedRunRow)))
    sent,_=invoke(target,token,path=path,method='GET');check(sent,409)


def test_all_content_readonly_still_reads_but_cannot_save(client,empty_client,monkeypatch):
    target,subject,token,path=saved(client,empty_client,monkeypatch)
    from mcis_service.redaction.policy import default_policy
    with target.app.state.db.session() as s:
        local.set_membership(s,subject,CASE,role='LeadInvestigator',can_save_unreviewed=False)
        doc=default_policy()
        doc['matrix']['LeadInvestigator']={k:'ReadOnly' for k in doc['matrix']['LeadInvestigator']}
        s.add(AccessPolicyRow(case_id=CASE,key='policy',doc=doc))
    sent,_=invoke(target,token,path=path,method='GET');check(sent,200)
    sent,_=invoke(target,token,method='POST');check(sent,403)


def test_expiry_during_source_capture_discards_read(client,empty_client,monkeypatch):
    target,_,token,path=saved(client,empty_client,monkeypatch)
    original=storage.capture
    def expired(ctx,session,*args,**kwargs):
        result=original(ctx,session,*args,**kwargs)
        session.scalar(select(local.SessionRecord)).expires_at=0
        session.flush()
        return result
    monkeypatch.setattr(storage,'capture',expired)
    sent,_=invoke(target,token,path=path,method='GET');check(sent,403)


def test_unknown_header_does_not_change_identity(client,empty_client,monkeypatch):
    target,subject,token,path=saved(client,empty_client,monkeypatch)
    headers=[(b'authorization',('Bearer '+token).encode()),(b'x-mcis-role',b'Public'),(b'x-mcis-operator',b'FORGED')]
    sent,_=invoke(target,token,path=path,method='GET',headers=headers)
    check(sent,200);assert b'FORGED' not in sent[1]['body']
