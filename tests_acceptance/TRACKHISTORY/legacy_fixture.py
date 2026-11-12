"""Run with an unchanged pre-fix service on PYTHONPATH to create genuine old databases."""
import json,sys
from pathlib import Path
from helpers import *
root=Path(sys.argv[1])
with client(root/'local') as c:
 b,d,report=populate(c);raw=export(c)
 response=c.post(BASE+'/reports',json={'templateId':'imo-cic','lang':'zh'},headers=H);assert response.status_code==201,response.text
 report_doc=response.json();working=export(c);assert json.loads(unzip(working)['manifest.json'])['packageVersion']=='1.2.0'
with client(root/'restored') as c:
 r=c.post('/api/v1/cases:import',content=raw,headers={**H,'Content-Type':'application/octet-stream'});assert r.status_code==201,r.text
with client(root/'restricted-restored') as c:
 r=intake(c,working,True);assert r.status_code==200,r.text
(root/'old-working.mcase').write_bytes(working)
(root/'report.json').write_text(json.dumps(report_doc))
(root/'info.json').write_text(json.dumps({'body':b,'receipt':d}))
(root/'old.mcase').write_bytes(raw)
