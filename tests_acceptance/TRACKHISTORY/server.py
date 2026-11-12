"""Real service seeded exclusively through synthetic HTTP, not ORM insertion."""
import os,tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from mcis_service.main import create_app
from mcis_service.config import Settings
from helpers import *
root=Path(os.environ['MCIS_DATA_DIR'])
with client(root/'source') as c:
 b,d,report=populate(c);raw=export(c)
app=create_app(Settings(data_dir=root/'target',seed_demo=False))
with TestClient(app) as c:
 assert intake(c,raw,True).status_code==200
 vessel(c,'newship')
if __name__=='__main__':
 import uvicorn
 uvicorn.run(app,host='127.0.0.1',port=int(os.environ['ARCHIVE_PORT']),log_level='error')
