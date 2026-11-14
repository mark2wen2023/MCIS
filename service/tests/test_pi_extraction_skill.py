"""Offline Skill binding tests; substituted transport is not real inference."""
import copy,json,uuid
import pytest
from .test_extraction_working_store import working
from .test_host_extraction import extraction_case
from .test_pi_working_host import accepted
from .test_pi_remote import CFG
from mcis_service.agents import pi_extraction_skill as skill,pi_transcript_remote as remote
from mcis_service.agents.pi_working_result import validate_shape

def test_manifest_is_pinned_and_defensive(monkeypatch):
 m=skill.current_manifest();ref=skill.reference(m)
 assert ref['id']=='mcis.source-extraction.readonly' and ref['version']=='1.0.0'
 m['steps'].clear();assert skill.current_manifest()['steps']
 with pytest.raises(ValueError):skill.verify_current_snapshot(m)
 monkeypatch.setattr(skill,'_MANIFEST_JSON',skill._MANIFEST_JSON.replace('1.0.0','1.0.1'))
 with pytest.raises(ValueError):skill.current_manifest()

def test_disclosure_binds_full_skill_and_cannot_mutate_host(extraction_case):
 a,_=extraction_case;d=remote.describe_remote(*a,CFG)
 assert d['skillRef']==skill.reference(d['skillManifest'])
 assert d['messages'][0]['content']==d['skillManifest']['prompts']['exact']
 host=remote.RemoteTranscriptHost(*a,CFG,approved_disclosure_digest=d['approvalDigest'])
 d['skillManifest']['steps'].clear()
 assert host._skill_manifest['steps'];host.close()

def test_changed_skill_rejects_old_approval(extraction_case,monkeypatch):
 a,_=extraction_case;d=remote.describe_remote(*a,CFG);m=skill.current_manifest();m['version']='1.0.1'
 # Simulate a new trusted release, not an external/user supplied manifest.
 monkeypatch.setattr(skill,'_MANIFEST_JSON',json.dumps(m));monkeypatch.setattr(skill,'_PINNED_DIGEST',skill.e.digest(m))
 with pytest.raises(Exception):remote.RemoteTranscriptHost(*a,CFG,approved_disclosure_digest=d['approvalDigest'])

def test_current_save_v2_legacy_and_unknown_history(working,monkeypatch):
 a,_=working;host,_=accepted(working,monkeypatch);result=host.save(str(uuid.uuid4()))['proposal']['result']
 x=result['execution'];assert x['profile']=='pi-working-trial-v2' and x['skillRef']==skill.reference(skill.current_manifest())
 legacy=copy.deepcopy(result);legacy['execution']['profile']='pi-working-trial-v1';del legacy['execution']['skillRef']
 validate_shape(legacy,a[4],legacy['bindingDigest'])
 unknown=copy.deepcopy(result);unknown['execution']['skillRef']['version']='99.0.0'
 monkeypatch.setattr(skill,'current_manifest',lambda:(_ for _ in ()).throw(AssertionError('history must not load registry')))
 validate_shape(unknown,a[4],unknown['bindingDigest'])
 for ref in ({}, {'id':'x','version':'1.0.0','contentDigest':'0'*64,'prompt':'unsafe'}, {'id':'x','version':True,'contentDigest':'0'*64}):
  bad=copy.deepcopy(result);bad['execution']['skillRef']=ref
  with pytest.raises(ValueError):validate_shape(bad,a[4],bad['bindingDigest'])
 host.close()

def test_changed_execution_manifest_cannot_save(working,monkeypatch):
 host,_=accepted(working,monkeypatch)
 host._PiWorkingHost__host._skill_manifest['version']='2.0.0'
 with pytest.raises(ValueError):host.save(str(uuid.uuid4()))
 host.close()

def test_tool_schema_change_fails_closed(monkeypatch):
 monkeypatch.setattr(skill.transport,'TOOL_SCHEMAS',[])
 with pytest.raises(ValueError):skill.current_manifest()

@pytest.mark.parametrize('version',['1x0x0',r'1\x0\x0','1.0','1.0.0\n',True])
def test_reference_rejects_invalid_versions(version):
 ref=skill.reference(skill.current_manifest());ref['version']=version
 with pytest.raises(ValueError):skill.validate_reference(ref)

def test_semantic_limits_are_instructions_not_validation():
 m=skill.current_manifest()
 assert m['resultPolicy']['semanticSupportVerified'] is False
 for prompt in m['prompts'].values():
  assert 'absent record is not evidence of absence' in prompt
  assert 'signal is not proof' in prompt
  assert 'approximate values' in prompt
