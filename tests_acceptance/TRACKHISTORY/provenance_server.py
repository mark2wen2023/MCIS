"""Serve one genuine old-runtime restored synthetic database under new runtime."""
import os
from pathlib import Path
from mcis_service.main import create_app
from mcis_service.config import Settings
app=create_app(Settings(data_dir=Path(os.environ['MCIS_DATA_DIR']),seed_demo=False))
if __name__=='__main__':
 import uvicorn
 uvicorn.run(app,host='127.0.0.1',port=15996,log_level='error')
