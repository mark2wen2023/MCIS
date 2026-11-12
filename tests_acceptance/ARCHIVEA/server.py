import os
from pathlib import Path
import uvicorn
from mcis_service.main import create_app
from mcis_service.config import Settings
from test_boundary import seed
app=create_app(Settings(data_dir=Path(os.environ['MCIS_DATA_DIR']),seed_demo=False));seed(app)
uvicorn.run(app,host='127.0.0.1',port=15972,log_level='warning')
