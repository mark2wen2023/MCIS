import os,json,sqlite3
from pathlib import Path
import httpx
BASE='http://127.0.0.1:18810/api/v1';OUT=Path(os.environ['MCIS_W101_ARTIFACT_DIR']);checks=[]
def ck(name,v):checks.append({'name':name,'passed':bool(v)});assert v,name
with httpx.Client(base_url=BASE,headers={'X-MCIS-Role':'Investigator'},trust_env=False) as c:
 before=c.get('/cases/QA-TRACK/overview').json()
 r=c.get('/cases/QA-TRACK/tracks');data=r.json();pts=data['tracks'][0]['points'];ck('real HTTP 2051 stored points',r.status_code==200 and len(pts)==2051)
 db=sqlite3.connect(Path(os.environ['MCIS_DATA_DIR'])/'mcis.db');raw=[json.loads(x[0]) for x in db.execute("select doc from track_points where case_id='QA-TRACK' order by vessel_id,time_sec")];ck('all returned points exactly DB JSON no interpolation',pts==raw)
 ck('negative time 0 speed 360 angle and date-line retained',pts[0]['timeSec']==-1 and pts[0]['sogKn']==0 and pts[0]['cogDeg']==360 and pts[0]['lonDeg']==-180 and pts[-1]['lonDeg']==180)
 subset=c.get('/cases/QA-TRACK/tracks?fromSec=0&toSec=100').json()['tracks'][0]['points'];ck('inclusive window returns original objects',subset==[p for p in raw if 0<=p['timeSec']<=100])
 ck('no samples empty response',c.get('/cases/QA-NOPOINT/tracks').json()['tracks']==[])
 ck('empty case empty vessels and tracks',c.get('/cases/QA-EMPTY/vessels').json()==[] and c.get('/cases/QA-EMPTY/tracks').json()['tracks']==[])
 ck('nonexistent case 404',c.get('/cases/NO-SUCH/tracks').status_code==404)
 for role in ['LeadInvestigator','Investigator','Public','AgentService','ExternalExpert','InterestedState']:
  r=c.get('/cases/QA-TRACK/tracks',headers={'X-MCIS-Role':role});ck(role+' access per actual gateway',r.status_code==200);checks[-1]['status']=r.status_code
 ck('read did not change overview/audit',c.get('/cases/QA-TRACK/overview').json()==before)
 ck('stored point JSON unchanged after reads',[json.loads(x[0]) for x in db.execute("select doc from track_points where case_id='QA-TRACK' order by vessel_id,time_sec")]==raw)
 db.close()
OUT.joinpath('http-results.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2));print(f'{len(checks)} HTTP checks passed')
