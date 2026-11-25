"""Real create_app from pinned worktree, uvicorn 127.0.0.1 only, fresh SQLite, one fictional synthetic case."""
import argparse,json,signal,socket,sys,threading,time
from pathlib import Path
P=argparse.ArgumentParser()
P.add_argument('--repo',required=True)
P.add_argument('--data',required=True)
P.add_argument('--port',type=int,required=True)
P.add_argument('--case',default='SYN-W7-CREATE-BODY')
a=P.parse_args()
sys.path.insert(0,str(Path(a.repo)/'service'))
import uvicorn
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
data=Path(a.data)
data.mkdir(parents=True,exist_ok=False)
app=create_app(Settings(data_dir=data,seed_demo=False))
doc=dict(caseId=a.case,schemaVersion='1.0.0',title='合成 W7 建议正文案',accidentType='Collision',
         isFictionalDemo=True,caseEpochUtc='2026-01-01T00:00:00Z',incidentTimeUtc='2026-01-01T00:00:00Z',
         incidentLocation=dict(lonDeg=0,latDeg=0),displayTimeZoneOffsetMinutes=0,placeName='Synthetic waters')
with app.state.db.session() as s:
    put_doc(s,CaseRow,a.case,a.case,doc)
sock=socket.socket();sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);sock.bind(('127.0.0.1',a.port));sock.listen(64)
srv=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=a.port,log_level='info'))
th=threading.Thread(target=lambda:srv.run(sockets=[sock]),daemon=True);th.start()
while not srv.started:time.sleep(.05)
ready=data/'ready.json'
ready.write_text(json.dumps({'origin':f'http://127.0.0.1:{a.port}','db':str(data/'mcis.db'),'seed_demo':False,'caseId':a.case},indent=1)+'\n')
print('READY',ready,flush=True)
stop=threading.Event()
signal.signal(signal.SIGTERM,lambda *x:stop.set())
signal.signal(signal.SIGINT,lambda *x:stop.set())
while not stop.is_set() and th.is_alive():time.sleep(.2)
srv.should_exit=True;th.join(10)
try:app.state.db.engine.dispose()
except Exception:pass
