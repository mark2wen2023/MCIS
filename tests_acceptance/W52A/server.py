import os
from pathlib import Path
import uvicorn
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.interviews.models import InterviewRow
from test_boundary import record
app=create_app(Settings(data_dir=Path(os.environ['MCIS_DATA_DIR']),seed_demo=False))
with app.state.db.session() as s:
 put_doc(s,CaseRow,'SYN-W52A','SYN-W52A',{'caseId':'SYN-W52A','title':'Synthetic','isFictionalDemo':True})
 for rid in ['IR-01','IR-02']:
  d=record();d['recordId']=rid;d['interviewee']['name']='Synthetic '+rid;d['turns'][0]['answer']='SYNTHETIC-ANSWER-'+rid
  put_doc(s,InterviewRow,'SYN-W52A',rid,d)
uvicorn.run(app,host='127.0.0.1',port=15952,log_level='warning')
