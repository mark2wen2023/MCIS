"""Loopback-only synthetic two-process SQLite reservation probe."""
import sys,time
from pathlib import Path
import uvicorn
from mcis_service.config import Settings
from mcis_service.main import create_app
from mcis_service.evidence import service
st=Settings();st.data_dir=Path(sys.argv[1]);st.db_url=f'sqlite:///{st.data_dir / "test.db"}';st.seed_demo=False
app=create_app(st)
original=service.next_id
def delayed(*args,**kwargs):
    value=original(*args,**kwargs)
    time.sleep(.12)  # expose overlap; independent processes do not share WRITE_LOCK
    return value
service.next_id=delayed
uvicorn.run(app,host='127.0.0.1',port=int(sys.argv[2]),log_level='error')
