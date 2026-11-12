import os
from pathlib import Path
import uvicorn
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
app=create_app(Settings(data_dir=Path(os.environ['MCIS_DATA_DIR']),seed_demo=False))
with app.state.db.session() as s:
 for cid in ['SYN-162','SYN-B']:put_doc(s,CaseRow,cid,cid,{'caseId':cid,'title':cid,'isFictionalDemo':True})
uvicorn.run(app,host='127.0.0.1',port=15962,log_level='warning')
