import json,base64,tempfile
from pathlib import Path
from tests.test_report_timeline_archive import client_at,populate,exported,commit,checked,HEAD,ROOT,rows,rewrite
Path('/tmp/mcis-web14-qa').mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='mcis-web14-') as tmp:
 with client_at(Path(tmp)/'source',True)as source:
  populate(source);before=rows(source);raw=exported(source)
 with client_at(Path(tmp)/'target')as target:
  body={'contentBase64':base64.b64encode(raw).decode()}
  denied=target.post('/api/v1/packages/intakes:preview',json=body,headers={'X-MCIS-Role':'Investigator'})
  assert denied.status_code==403
  preview=checked(target,'post','/api/v1/packages/intakes:preview',body).json()
  receipt=commit(target,raw).json()
  lookup=checked(target,'get','/api/v1/packages/intakes/'+preview['sourceSha256']).json()
  assert rows(target)==before
  Path('/tmp/mcis-web14-qa/actual-responses.json').write_text(json.dumps({'preview':preview,'commit':receipt,'lookup':lookup}))
  Path('/tmp/mcis-web14-qa/synthetic.mcase').write_bytes(raw)
 with client_at(Path(tmp)/'negative')as target:
  def mix(files,m):m['packageVersion']='1.3.0'
  bad=rewrite(raw,mix)
  rejected=target.post('/api/v1/packages/intakes:preview',json={'contentBase64':base64.b64encode(bad).decode()},headers=HEAD)
  assert rejected.status_code==422
  assert target.get('/api/v1/cases').json()==[]
 print('Real ASGI HTTP: 1.4 preview200/commit200/lookup200 exact timeline rows; Investigator403; track-version mismatch422 zero cases')
