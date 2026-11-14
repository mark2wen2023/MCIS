import asyncio,json,os,select,subprocess,sys,uuid
from pathlib import Path
import pytest
from .test_host_extraction import extraction_case
from .test_extraction_working_store import working,decisions
from mcis_service.agents import host_extraction as h
from mcis_service.agents.extraction_review_fixture import fixture_content
from mcis_service.agents.persistent_extraction_review_host import PersistentExtractionReviewHost
from mcis_service.agents.persistent_extraction_rpc import PersistentExtractionRPC
from .test_agents_w20 import ITEM

@pytest.mark.parametrize('origin',['user_submission_unverified','scripted_test'])
def test_trusted_review_origin_is_fixed_and_rpc_cannot_override(working,origin):
 a,_=working
 with PersistentExtractionReviewHost(db=a[0],settings=a[1],session_token=a[2],case_id=a[3],record_id=a[4],provider=h.FixtureProvider(json.dumps({'statements':[ITEM]})),review_origin=origin) as host:
  pid=host.generate(str(uuid.uuid4()))['proposalId']
  rpc=PersistentExtractionRPC(host);scope={k:v for k,v in rpc.scope.items() if k!='productionLogin'}
  request={**scope,'requestId':str(uuid.uuid4()),'action':'review','proposalId':pid,'operationId':str(uuid.uuid4()),'expectedRevision':0,'decisions':decisions()}
  bad=asyncio.run(rpc.dispatch({**request,'reviewOrigin':'user_submission_unverified' if origin=='scripted_test' else 'scripted_test'}))
  assert bad['ok'] is False
  good=asyncio.run(rpc.dispatch(request));assert good['ok'] and good['body']['reviews'][0]['reviewOrigin']==origin


def test_broker_fixture_full_protocol_no_key_no_network():
 root=Path(__file__).resolve().parents[2]
 child=subprocess.Popen([sys.executable,str(root/'runtime/public-ui-host.py'),'--fixture'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={'PATH':os.environ['PATH'],'PYTHONPATH':str(root/'service')},text=True,bufsize=1)
 def receive():
  assert select.select([child.stdout],[],[],15)[0],'broker timeout'
  line=child.stdout.readline();assert line,'broker ended';return json.loads(line)
 def send(value):child.stdin.write(json.dumps(value,ensure_ascii=False)+'\n');child.stdin.flush();return receive()
 try:
  ready=receive();assert ready['fixture'] and ready['transportMocked'] and not ready['remoteProviderSelected'] and not ready['inferencePerformed'] and ready['mode']=='fixture'
  assert not any(k in json.dumps(ready) for k in ['apiKey','fixture-not-a-credential','session_token'])
  for n in range(3):
   send({'op':'model_start'});response=send({'op':'model_request'});send({'op':'model_end'})
   calls=response['message'].get('tool_calls',[])
   for c in calls:send({'op':'tool','callId':c['id'],'name':c['function']['name'],'args':json.loads(c['function']['arguments'])})
  accepted=send({'op':'final','payload':'MCIS_COMPLETE_VALIDATED_PROPOSAL'})
  assert accepted['workingReady']['saved'] and not accepted['workingReady']['factActivated'];pid=accepted['workingReady']['proposalId']
  def rpc(channel,action,**extra):
   scope={k:v for k,v in ready[channel+'Scope'].items() if k!='productionLogin'}
   return send({'channel':channel,'request':{**scope,'requestId':str(uuid.uuid4()),'action':action,**extra}})
  current=rpc('review','read',proposalId=pid);assert current['ok']
  reviewed=rpc('review','review',proposalId=pid,operationId=str(uuid.uuid4()),expectedRevision=0,decisions=[{'index':1,'decision':'needs_verification','note':'脚本待核实'}])
  assert reviewed['body']['reviews'][0]['reviewOrigin']=='scripted_test'
  exported=rpc('archive','export');assert exported['ok'] and exported['body']['format']=='extraction-working-supplement-v2'
  imported=rpc('archive','import',bundleBase64=exported['body']['bundleBase64']);assert imported['ok'] and not imported['body']['activated']
  historical=rpc('archive','read',sha256=imported['body']['sha256']);assert historical['ok'] and not historical['body']['historicalClaimsVerified']
  assert historical['body']['payload']['proposals'][0]['reviews'][0]['reviewOrigin']=='scripted_test'
  assert send({'channel':'close'})=={'closed':True,'cleanupConfirmed':True,'temporaryStorageRemoved':True}
  child.wait(timeout=10);assert child.returncode==0 and child.stderr.read()==''
 finally:
  if child.poll() is None:child.kill();child.wait()
