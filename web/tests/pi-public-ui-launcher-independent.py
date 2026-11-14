import os,subprocess,json,tempfile,pathlib
root=pathlib.Path(__file__).resolve().parents[3]
env={**os.environ,'MCIS_PI_RUNTIME':str(root/'pi-transcript/runtime'),'MCIS_HOST_PYTHON':str(root/'mcis-work/service/.venv/bin/python'),'MCIS_HOST_SERVICE':str(root/'pi-transcript/service'),'MCIS_HAPPY_DOM_PATH':str(root/'w19-react-1600/node_modules/happy-dom/lib/index.js'),'DEEPSEEK_API_KEY':'ENV_SECRET_SENTINEL'}
with tempfile.TemporaryDirectory(prefix='pi-launcher-independent-') as tmp:
 env['TMPDIR']=tmp
 cases=[('--bad','PAYLOAD_SECRET_SENTINEL\n'),('--approved-public-ui','{"apiKey":null,"other":"PAYLOAD_SECRET_SENTINEL"}\n'),('--fixture','')]
 results=[]
 for flag,input in cases:
  run=subprocess.run(['node','tests/.pi-public-ui-live.mjs',flag],cwd=root/'issue-ui/web',env=env,input=input,text=True,capture_output=True,timeout=90)
  assert run.stderr == '', 'launcher must not echo raw diagnostics'
  assert 'ENV_SECRET_SENTINEL' not in run.stdout+run.stderr and 'PAYLOAD_SECRET_SENTINEL' not in run.stdout+run.stderr
  lines=[json.loads(x) for x in run.stdout.splitlines()];last=lines[-1]
  if flag=='--fixture':
   assert run.returncode==0 and last['status']=='accepted_pending_review'
   assert last['realModel'] is False and last['mockInference'] is True and last['providerRequests']==0 and last['browserEngine'] is False
   assert last['cleanupConfirmed'] and last['processExitVerified'] and last['reviewActor']=='scripted_test_not_human' and not last['factActivated']
   receipts=list(pathlib.Path(tmp).glob('pi-run-'+last['runId']+'/receipt.jsonl'));assert len(receipts)==1
   rows=[json.loads(x) for x in receipts[0].read_text().splitlines()];phases=[x['phase'] for x in rows]
   assert phases[-1]=='accepted_pending_review' and phases.index('cleanup_verified')<len(phases)-1
   assert 'ui_review_verified' in phases and 'archive_roundtrip_verified' in phases
   assert not list(pathlib.Path(tmp).glob('mcis-public-pi-ui-*'))
  else:assert run.returncode!=0 and last['status']=='not_accepted'
  results.append({'flag':flag,'exit':run.returncode,'status':last['status']})
 for file in pathlib.Path(tmp).rglob('*'):
  if file.is_file():assert 'SECRET_SENTINEL' not in file.read_text()
 print(json.dumps({'independentChecks':3,'passed':True,'results':results}))
