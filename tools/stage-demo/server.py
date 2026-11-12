"""Only the runner calls this bootstrap with its inherited loopback socket."""
import os,socket,sys
from pathlib import Path
import uvicorn
from mcis_service.config import Settings
from mcis_service.main import create_app
if __name__=='__main__':
    data=Path(sys.argv[1]);fd=int(sys.argv[2]);sock=socket.socket(fileno=fd)
    if sock.getsockname()[0]!='127.0.0.1':raise RuntimeError('loopback required')
    app=create_app(Settings(data_dir=data,db_url=f'sqlite:///{data}/mcis.db',seed_demo=False,core_cmd='/bin/false',core_timeout_s=1))
    uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',log_level='warning')).run(sockets=[sock])
