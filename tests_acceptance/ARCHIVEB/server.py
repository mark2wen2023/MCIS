import os
from pathlib import Path
import uvicorn
from fastapi.testclient import TestClient
from helpers import seed,populate,create_app,Settings
app=create_app(Settings(data_dir=Path(os.environ['MCIS_DATA_DIR']),seed_demo=False))
if os.environ.get('ARCHIVE_SEED')=='1':
 with TestClient(app) as c:seed(c);populate(c)
uvicorn.run(app,host='127.0.0.1',port=int(os.environ['ARCHIVE_PORT']),log_level='warning')
