import os
from pathlib import Path
import uvicorn
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
app=create_app(Settings(data_dir=Path(os.environ['MCIS_DATA_DIR']),seed_demo=False))
with app.state.db.session() as s:
    for cid in ['CASE-A','CASE-B']:
        put_doc(s,CaseRow,cid,cid,{'caseId':cid,'title':cid})
        policy=default_policy();policy['version']=cid+'-VERSION'
        policy['fieldRules'].append({'ruleId':'INDEPENDENT','field':'synthetic','method':'Mask','appliesTo':['Public'],'description':cid+'-SECRET-CONFIG'})
        put_doc(s,AccessPolicyRow,cid,'policy',policy)
uvicorn.run(app,host='127.0.0.1',port=15971,log_level='warning')
