import os
from pathlib import Path
import uvicorn
from mcis_service.main import create_app
from mcis_service.config import Settings
app=create_app(Settings(data_dir=Path(os.environ['MCIS_DATA_DIR']),seed_demo=False))
if os.environ.get('W186_SEED')=='1':
 from helpers import seed
 from types import SimpleNamespace
 seed(SimpleNamespace(app=app))
uvicorn.run(app,host='127.0.0.1',port=int(os.environ['W186_PORT']),log_level='warning')
