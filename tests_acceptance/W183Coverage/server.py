import os
from pathlib import Path
import uvicorn
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.evidence.models import EvidenceRow
app=create_app(Settings(data_dir=Path(os.environ['MCIS_DATA_DIR']),seed_demo=False))
with app.state.db.session() as s:
    for cid in ['CASE-A','CASE-B']:
        put_doc(s,CaseRow,cid,cid,{'caseId':cid,'title':cid})
        put_doc(s,EvidenceRow,cid,'EV-001',{'caseId':cid,'evidenceId':'EV-001','title':cid+' 合成工休资料 🛳','sha256':'a'*64,'confidentiality':'Normal'})
uvicorn.run(app,host='127.0.0.1',port=15985,log_level='warning')
