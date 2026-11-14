"""Independent broker state/cleanup tests. Explicit fixture only, no credentials/network."""
import json,os,select,subprocess,sys,uuid
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]

class Broker:
 def __init__(self,tmp_path):
  self.tmp=tmp_path
  self.p=subprocess.Popen([sys.executable,str(ROOT/'runtime/public-ui-host.py'),'--fixture'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env={'PATH':os.environ['PATH'],'PYTHONPATH':str(ROOT/'service'),'TMPDIR':str(tmp_path),'DEEPSEEK_API_KEY':'ENV_SENTINEL_NOT_USED'},text=True,bufsize=1)
  self.ready=self.read()
 def read(self):
  assert select.select([self.p.stdout],[],[],20)[0],'timeout'
  raw=self.p.stdout.readline();assert raw,'eof';assert 'ENV_SENTINEL_NOT_USED' not in raw and 'fixture-not-a-credential' not in raw
  return json.loads(raw)
 def send(self,v):self.p.stdin.write(json.dumps(v)+'\n');self.p.stdin.flush();return self.read()
 def accepted(self):
  for _ in range(3):
   self.send({'op':'model_start'});result=self.send({'op':'model_request'});self.send({'op':'model_end'})
   for c in result['message'].get('tool_calls',[]):self.send({'op':'tool','callId':c['id'],'name':c['function']['name'],'args':json.loads(c['function']['arguments'])})
  return self.send({'op':'final','payload':'MCIS_COMPLETE_VALIDATED_PROPOSAL'})
 def req(self,channel,action,**extra):
  scope={k:v for k,v in self.ready[channel+'Scope'].items() if k!='productionLogin'}
  return {'channel':channel,'request':{**scope,'requestId':str(uuid.uuid4()),'action':action,**extra}}
 def stopped(self,result):
  assert result=={'ok':False,'errorCode':'PUBLIC_UI_HOST_STOPPED'}
  self.p.wait(timeout=10);assert self.p.returncode==2;assert self.p.stderr.read()==''
  assert list(self.tmp.iterdir())==[]
 def cleanup(self):
  if self.p.poll() is None:self.p.kill();self.p.wait()

@pytest.mark.parametrize('envelope',[{'channel':'review','request':{'action':'list'}},{'channel':'archive','request':{'action':'export'}},{'op':'final','payload':'MCIS_COMPLETE_VALIDATED_PROPOSAL'},{'channel':'close','extra':'forbidden'}])
def test_independent_before_accepted_ui_and_forged_final_deny_and_cleanup(tmp_path,envelope):
 b=Broker(tmp_path)
 try:b.stopped(b.send(envelope))
 finally:b.cleanup()

@pytest.mark.parametrize('kind',['pi_after','generate','unexported_import','wrong_channel'])
def test_independent_after_accepted_phase_boundaries(tmp_path,kind):
 b=Broker(tmp_path)
 try:
  accepted=b.accepted();assert accepted['workingReady']['saved']
  if kind=='pi_after':command={'op':'model_start'}
  elif kind=='generate':command=b.req('review','generate',operationId=str(uuid.uuid4()))
  elif kind=='unexported_import':command=b.req('archive','import',bundleBase64='e30=')
  else:command={'channel':'shell','request':{}}
  b.stopped(b.send(command))
 finally:b.cleanup()


def test_independent_server_origin_and_exact_export_pin(tmp_path):
 b=Broker(tmp_path)
 try:
  saved=b.accepted();pid=saved['workingReady']['proposalId']
  op=str(uuid.uuid4());command=b.req('review','review',proposalId=pid,operationId=op,expectedRevision=0,decisions=[{'index':1,'decision':'needs_verification','note':'自动化测试，不是人工意见'}],reviewOrigin='user_submission_unverified')
  assert b.send(command)['ok'] is False
  current=b.send(b.req('review','read',proposalId=pid));assert current['body']['revision']==0
  command['request'].pop('reviewOrigin');command['request']['requestId']=str(uuid.uuid4());saved=b.send(command)
  assert saved['body']['reviews'][0]['reviewOrigin']=='scripted_test'
  exported=b.send(b.req('archive','export'));package=exported['body']['bundleBase64'];assert package
  b.stopped(b.send(b.req('archive','import',bundleBase64=package+'A')))
 finally:b.cleanup()


def test_independent_explicit_close_before_model_proves_cleanup_not_inference(tmp_path):
 b=Broker(tmp_path)
 try:
  assert b.ready['fixture'] and not b.ready['inferencePerformed'] and not b.ready['remoteProviderSelected'] and b.ready['transportMocked']
  assert list(tmp_path.iterdir())
  assert b.send({'channel':'close'})=={'closed':True,'cleanupConfirmed':True,'temporaryStorageRemoved':True}
  assert list(tmp_path.iterdir())==[];b.p.wait(timeout=10);assert b.p.returncode==0
 finally:b.cleanup()


def test_independent_buffered_line_cannot_bypass_expired_total_deadline(monkeypatch):
 import importlib.util,time
 spec=importlib.util.spec_from_file_location('reviewed_public_ui_broker',ROOT/'runtime/public-ui-host.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 lines=module.Lines();lines.pending=b'{}\n'
 with pytest.raises(TimeoutError):lines.read(time.monotonic()-1)


def test_independent_buffered_line_still_obeys_maximum_and_total_budget(monkeypatch):
 import importlib.util,time
 spec=importlib.util.spec_from_file_location('reviewed_public_ui_limits',ROOT/'runtime/public-ui-host.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 lines=module.Lines();lines.pending=b'12345\n'
 with pytest.raises(ValueError):lines.read(time.monotonic()+10,4)
 lines=module.Lines();monkeypatch.setattr(module,'TOTAL_LIMIT',4)
 monkeypatch.setattr(module.sys,'stdin',type('Input',(),{'fileno':lambda self:3})())
 monkeypatch.setattr(module.select,'select',lambda *a:([3],[],[]));monkeypatch.setattr(module.os,'read',lambda *a:b'12345\n')
 with pytest.raises(ValueError):lines.read(time.monotonic()+10)
