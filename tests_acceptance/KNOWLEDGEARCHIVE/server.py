"""Loopback-only synthetic acceptance server."""
import os
from pathlib import Path
from fastapi.testclient import TestClient
from mcis_service.main import create_app
from mcis_service.config import Settings
from test_backend import create,review
app=create_app(Settings(data_dir=Path(os.environ['MCIS_DATA_DIR']),seed_demo=False))
if os.environ.get('ARCHIVE_SEED')=='1':
 with TestClient(app) as c:
  for kind in ('Case','Method','Challenge'):
   d=create(c,kind);assert review(c,d,'Published').status_code==200
   if kind=='Case':assert review(c,d,'Withdrawn').status_code==200
if __name__=='__main__':
 import uvicorn
 uvicorn.run(app,host='127.0.0.1',port=int(os.environ['ARCHIVE_PORT']),log_level='error')
