import json,os,sys,tempfile,threading,socket
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'service'))
from fastapi.testclient import TestClient
from mcis_service.config import Settings
from mcis_service.main import create_app
RUN=Path(os.environ['MCIS_W20UI_RUN_DIR']);MODE=RUN/'model-mode';MODE.write_text('ok')
class Fake(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_POST(self):
  _=self.rfile.read(int(self.headers['Content-Length']));mode=MODE.read_text().strip()
  if mode=='failure':self.send_response(503);self.end_headers();return
  if mode=='delay':import time;time.sleep(4)
  content={'statements':[{'kind':'Observation','subject':'vessel.lookout','summary':'值班人员称发现目标船（合成测试草稿）','claim':{'valueType':'Occurrence','occurred':True},'round':1,'field':'Answer','quote':'发现目标船'}]}
  if mode=='bad':content['statements'][0]['quote']='不存在的引用'
  body=json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(content,ensure_ascii=False)}}]}).encode()
  self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
fake=ThreadingHTTPServer(('127.0.0.1',0),Fake);threading.Thread(target=fake.serve_forever,daemon=True).start()
os.environ['MCIS_AGENT_BASE_URL']=f'http://127.0.0.1:{fake.server_port}/v1';os.environ['MCIS_AGENT_MODEL']='controlled-http-fixture-not-real-LLM'
tmp=Path(tempfile.mkdtemp(prefix='database-',dir=RUN));app=create_app(Settings(data_dir=tmp,seed_demo=True))
with TestClient(app) as c:
 for cid in ['CASE-W202-QA','CASE-W202-OTHER']:
  body={'caseId':cid,'schemaVersion':'1.0.0','title':'W20.2 合成审核测试 '+cid,'accidentType':'Collision','incidentTimeUtc':'2026-11-12T00:00:00Z','caseEpochUtc':'2026-11-12T00:00:00Z','displayTimeZoneOffsetMinutes':0,'incidentLocation':{'latDeg':0,'lonDeg':0},'isFictionalDemo':True}
  r=c.post('/api/v1/cases',json=body);assert r.status_code==201,r.text
  for rid in ['IR-90','IR-91']:
   record={'recordId':rid,'interviewee':{'intervieweeId':rid,'name':'合成人员','role':'值班船员','affiliation':'虚构测试船'},'startUtc':'2026-11-12T00:00:00Z','turns':[{'round':1,'question':'请说明观察。','answer':'我发现目标船，随后持续瞭望。'}],'statements':[]}
   r=c.post(f'/api/v1/cases/{cid}/interviews',json=record);assert r.status_code==201,r.text
sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
(RUN/'session.json').write_text(json.dumps({'api':f'http://127.0.0.1:{port}','fakeModel':fake.server_port}))
import uvicorn
uvicorn.run(app,host='127.0.0.1',port=port,log_level='warning')
