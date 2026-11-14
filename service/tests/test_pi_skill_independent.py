"""Independent Skill snapshot/provenance tests, no real provider calls."""
import copy,json,uuid
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from .test_host_extraction import extraction_case
from .test_extraction_working_store import working
from .test_pi_working_host import accepted
from .test_pi_remote import CFG,response
from .test_pi_working_archive import pi_bundle
from .test_working_history_archive import permissions
from mcis_service.agents import pi_extraction_skill as s,pi_transcript_remote as r,pi_deepseek_transport as t,extraction_working_store as w,working_history_archive as archive
from mcis_service.agents.pi_working_result import validate_shape
from mcis_service.identity import local

def count(a):
 with a[0].session() as session:return len(list(session.scalars(select(w.WorkingProposal))))

def release(monkeypatch):
 m=s.current_manifest();m['version']='1.0.1'
 monkeypatch.setattr(s,'_MANIFEST_JSON',json.dumps(m));monkeypatch.setattr(s,'_PINNED_DIGEST',s.e.digest(m))

def host(case):
 a,_=case;disclosure=r.describe_remote(*a,CFG)
 return r.RemoteTranscriptHost(*a,CFG,approved_disclosure_digest=disclosure['approvalDigest'])

@pytest.mark.parametrize('when',['before','after'])
def test_independent_release_change_denies_request_or_response(extraction_case,monkeypatch,when):
 h=host(extraction_case);h.dispatch({'op':'model_start'});calls=[]
 def complete(*args,**kwargs):
  calls.append(True)
  if when=='after':release(monkeypatch)
  return response()
 monkeypatch.setattr(t,'complete',complete)
 if when=='before':release(monkeypatch)
 with pytest.raises(HTTPException):h.dispatch({'op':'model_request'})
 assert h._closed and h._accepted_content is None
 assert len(calls)==(1 if when=='after' else 0)


def test_independent_release_change_after_acceptance_prevents_save(working,monkeypatch):
 a,_=working;h,_=accepted(working,monkeypatch);release(monkeypatch)
 with pytest.raises(ValueError):h.save(str(uuid.uuid4()))
 assert count(a)==0;h.close()


def test_independent_revocation_still_overrides_skill_validity(working,monkeypatch):
 a,_=working;h,_=accepted(working,monkeypatch)
 with a[0].session() as session:local.revoke_session(session,a[2])
 with pytest.raises(HTTPException):h.save(str(uuid.uuid4()))
 assert count(a)==0;h.close()


def test_independent_disclosure_return_is_not_execution_authority(extraction_case):
 a,_=extraction_case;d=r.describe_remote(*a,CFG);h=r.RemoteTranscriptHost(*a,CFG,approved_disclosure_digest=d['approvalDigest'])
 original=copy.deepcopy(h._messages);ref=s.reference(h._skill_manifest)
 d['skillRef']['contentDigest']='0'*64;d['skillManifest']['prompts']['exact']='unsafe';d['skillManifest']['resultPolicy']['factActivationAllowed']=True;d['messages'][0]['content']='unsafe'
 assert h._messages==original and s.reference(h._skill_manifest)==ref
 assert h.dispatch({'op':'model_start'})['modelCall']==1;h.close()

@pytest.mark.parametrize('envelope',[{'op':'model_start','skillId':'external.plugin'},{'op':'model_start','skillManifest':{'permissionExpansionAllowed':True}}])
def test_independent_external_skill_cannot_be_submitted_as_protocol(extraction_case,monkeypatch,envelope):
 h=host(extraction_case);monkeypatch.setattr(t,'complete',lambda *a,**kw:pytest.fail('must not invoke model'))
 with pytest.raises(HTTPException):h.dispatch(envelope)
 assert h._closed


def test_independent_budget_drift_fails_before_remote(extraction_case,monkeypatch):
 from mcis_service.agents import pi_transcript_host as base
 h=host(extraction_case);monkeypatch.setattr(base,'MAX_TOOLS',9)
 with pytest.raises(ValueError):h.dispatch({'op':'model_start'})
 assert h._closed


def test_independent_unknown_historical_skill_never_loads_registry_or_activates(pi_bundle,monkeypatch):
 v,_,raw=pi_bundle;a,_=v;permissions(v);before=w.list_records(*a[:4]);wrap=json.loads(raw);execution=wrap['payload']['proposals'][0]['result']['execution']
 execution['skillRef']={'id':'uninstalled.external-skill','version':'99.2.7','contentDigest':'0'*64}
 wrap['sha256']=s.e.digest(wrap['payload'])
 monkeypatch.setattr(s,'current_manifest',lambda:pytest.fail('historical metadata must never execute/lookup Skill registry'))
 saved=archive.restore_bundle(a[0],a[2],a[3],archive.canonical(wrap));view=archive.read_imported(a[0],a[2],a[3],saved['sha256'])
 assert not saved['activated'] and not view['historicalClaimsVerified'];assert w.list_records(*a[:4])==before
 assert view['payload']['proposals'][0]['result']['execution']['skillRef']==execution['skillRef']

@pytest.mark.parametrize('damage',['legacy_extra','v2_missing','ref_extra','bad_digest','bad_id','bad_version'])
def test_independent_skill_versioned_shapes_reject_mixed_authority(pi_bundle,damage):
 v,saved,_=pi_bundle;a,_=v;result=copy.deepcopy(saved['proposal']['result']);x=result['execution']
 if damage=='legacy_extra':x['profile']='pi-working-trial-v1'
 elif damage=='v2_missing':x.pop('skillRef')
 elif damage=='ref_extra':x['skillRef']['tools']=['shell']
 elif damage=='bad_digest':x['skillRef']['contentDigest']='A'*64
 elif damage=='bad_id':x['skillRef']['id']='../../external'
 else:x['skillRef']['version']='1.0.0\n'
 with pytest.raises(ValueError):validate_shape(result,a[4],result['bindingDigest'])


def test_independent_old_v1_archive_remains_without_inferred_skill(pi_bundle):
 v,_,raw=pi_bundle;a,_=v;permissions(v);wrap=json.loads(raw);x=wrap['payload']['proposals'][0]['result']['execution'];x['profile']='pi-working-trial-v1';x.pop('skillRef');wrap['sha256']=s.e.digest(wrap['payload'])
 saved=archive.restore_bundle(a[0],a[2],a[3],archive.canonical(wrap));view=archive.read_imported(a[0],a[2],a[3],saved['sha256'])
 assert 'skillRef' not in view['payload']['proposals'][0]['result']['execution'];assert not saved['activated']
