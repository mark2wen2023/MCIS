import os
from pathlib import Path
import uvicorn
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.interviews.models import InterviewRow
app=create_app(Settings(data_dir=Path(os.environ['MCIS_DATA_DIR']),seed_demo=False))
with app.state.db.session() as s:
 put_doc(s,CaseRow,'SYN-W52B','SYN-W52B',{'caseId':'SYN-W52B','title':'Synthetic','isFictionalDemo':True})
uvicorn.run(app,host='127.0.0.1',port=15962,log_level='warning')
