"""Synthetic W17 evidence backend: real create_app from --repo, real uvicorn on 127.0.0.1:<port>.
Seeds two fictional cases via the actual intake preview/commit HTTP endpoints (title SOURCE-<case>, both EV-001).
Test-only ASGI wrapper: optional response delay (control file) and /__w17ctl/denyB (Deny evidence_meta for
LeadInvestigator on SYN-B, as in the repo receipt.py control). Runs until SIGTERM."""
import argparse,asyncio,base64,json,signal,socket,sys,threading,time,urllib.request
from pathlib import Path
P=argparse.ArgumentParser();P.add_argument('--repo',required=True);P.add_argument('--data',required=True);P.add_argument('--port',type=int,required=True);a=P.parse_args()
sys.path.insert(0,str(Path(a.repo)/'service'))
import uvicorn
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
data=Path(a.data);data.mkdir(parents=True,exist_ok=False);DELAY=data/'delay.json'
app=create_app(Settings(data_dir=data,seed_demo=False))
with app.state.db.session() as s:
 for c in ('SYN-A','SYN-B'):
  put_doc(s,CaseRow,c,c,dict(caseId=c,schemaVersion='1.0.0',title='Synthetic '+c,accidentType='Synthetic',isFictionalDemo=True,caseEpochUtc='2026-01-01T00:00:00Z',incidentTimeUtc='2026-01-01T00:00:00Z',incidentLocation=dict(lonDeg=-130,latDeg=-30),displayTimeZoneOffsetMinutes=0))
class W:
 def __init__(s,i):s.i=i
 async def __call__(s,scope,receive,send):
  if scope['type']=='http':
   p=scope['path']
   if p=='/__w17ctl/denyB':
    pol=default_policy();pol['matrix']['LeadInvestigator']['evidence_meta']='Deny'
    with app.state.db.session() as x:put_doc(x,AccessPolicyRow,'SYN-B','policy',pol)
    await send({'type':'http.response.start','status':200,'headers':[(b'content-type',b'application/json')]});await send({'type':'http.response.body','body':b'{"denied":true}'});return
   if DELAY.exists():
    rule=json.loads(DELAY.read_text())
    if p in rule['paths'] and rule.get('remaining',0)>0:
     rule['remaining']-=1;DELAY.write_text(json.dumps(rule))
     async def late(m,_s=send):
      if m['type']=='http.response.start':await asyncio.sleep(rule['seconds'])
      await _s(m)
     return await s.i(scope,receive,late)
  return await s.i(scope,receive,send)
sock=socket.socket();sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);sock.bind(('127.0.0.1',a.port));sock.listen(64)
srv=uvicorn.Server(uvicorn.Config(W(app),host='127.0.0.1',port=a.port,log_level='warning'))
th=threading.Thread(target=lambda:srv.run(sockets=[sock]),daemon=True);th.start()
while not srv.started:time.sleep(.05)
o=f'http://127.0.0.1:{a.port}';h={'Content-Type':'application/json','X-MCIS-Role':'LeadInvestigator','X-MCIS-Operator':'synthetic-reader'}
def post(path,body):
 with urllib.request.urlopen(urllib.request.Request(o+path,data=json.dumps(body).encode(),headers=h),timeout=20) as r:return json.loads(r.read())
reg={}
for c in ('SYN-A','SYN-B'):
 body={'profile':'mcis-evidence-intake-v1','fileName':c+'.txt','contentBase64':base64.b64encode(('Invented opaque bytes '+c).encode()).decode(),'title':'SOURCE-'+c,'source':'Synthetic '+c,'extractedBy':'synthetic','extractedUtc':'2026-01-01T00:00:00Z','category':'Other','confidentiality':'Restricted','note':'Visible synthetic receipt test'}
 pv=post(f'/api/v1/cases/{c}/evidence-intakes:preview',body);reg[c]=post(f'/api/v1/cases/{c}/evidence-intakes:commit',{**body,'requestDigest':pv['requestDigest'],'confirmed':True})
(data/'ready.json').write_text(json.dumps({'origin':o,'db':str(data/'mcis.db'),'delayFile':str(DELAY),'registered':reg},indent=1))
stop=threading.Event();signal.signal(signal.SIGTERM,lambda *x:stop.set());signal.signal(signal.SIGINT,lambda *x:stop.set())
while not stop.is_set() and th.is_alive():time.sleep(.2)
srv.should_exit=True;th.join(10);app.state.db.engine.dispose()
