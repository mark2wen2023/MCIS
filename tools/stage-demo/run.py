"""Real-loopback synthetic demonstration. No imports from business/ORM modules."""
import argparse,base64,hashlib,json,os,socket,subprocess,sys,tempfile,time,uuid
from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from urllib.error import HTTPError,URLError
ROOT=Path(__file__).resolve().parents[2]
FIX=Path(__file__).resolve().parent/'fixtures'
CID='STAGE-SYNTHETIC';VID='SYNTH-SHIP';BASE='/api/v1/cases/'+CID
HEAD={'X-MCIS-Role':'LeadInvestigator','X-MCIS-Operator':'Synthetic Stage Script'}
HTTP=build_opener(ProxyHandler({}))
def digest(raw):return hashlib.sha256(raw).hexdigest()
def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def process_start_ticks(pid):
 # Linux field 22. comm (field 2) can contain spaces and closing parentheses.
 raw=Path(f'/proc/{pid}/stat').read_text()
 fields=raw.rsplit(')',1)[1].split()
 ticks=fields[19]
 if not ticks.isascii()or not ticks.isdigit():raise RuntimeError('Cannot verify owned process start time')
 return ticks
class Run:
 def __init__(self,path):
  self.path=path;self.children=[];self.manifest={'status':'running','running':True,'caseId':CID,'vesselId':VID,'ids':{},'services':{},'artifacts':{},'limitations':['Synthetic scripted review actions, not real expert review','Template reports, no LLM','Isolated history, no online knowledge activation']};self.record()
 def record(self):dump(self.path/'run.json',self.manifest)
 def start(self,name):
  data=self.path/name;data.mkdir();sock=socket.socket()
  try:sock.bind(('127.0.0.1',0));sock.listen(128);port=sock.getsockname()[1]
  except BaseException:sock.close();raise
  log=open(self.path/(name+'.log'),'wb');env={k:os.environ[k]for k in ('PATH','LANG','LC_ALL','TMPDIR')if k in os.environ}
  env.update(PYTHONPATH=str(ROOT/'service'),MCIS_SEED_DEMO='0',MCIS_DATA_DIR=str(data))
  try:p=subprocess.Popen([sys.executable,str(Path(__file__).parent/'server.py'),str(data),str(sock.fileno())],pass_fds=(sock.fileno(),),env=env,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
  except BaseException:
   log.close();raise
  finally:sock.close()
  self.children.append((p,log));url=f'http://127.0.0.1:{port}';self.manifest['services'][name]={'url':url,'pid':p.pid,'processStartTicks':process_start_ticks(p.pid),'dataDir':name};self.record()
  for _ in range(100):
   if p.poll()is not None:raise RuntimeError(f'{name} startup failed, inspect its log')
   try:
    with HTTP.open(url+'/api/v1/health',timeout=.5)as r:
     if r.status==200:return url
   except (URLError,TimeoutError,ConnectionError):pass
   time.sleep(.1)
  raise RuntimeError(f'{name} startup timeout')
 def call(self,url,method,path,body=None,status=200,raw=None,extra=None):
  headers={**HEAD,**(extra or{})}
  if body is not None:raw=json.dumps(body,ensure_ascii=False).encode();headers['Content-Type']='application/json'
  req=Request(url+path,data=raw,headers=headers,method=method)
  try:
   with HTTP.open(req,timeout=60)as r:code=r.status;data=r.read();rh=dict(r.headers)
  except HTTPError as e:code=e.code;data=e.read();rh=dict(e.headers)
  with open(self.path/'steps.jsonl','a')as f:f.write(json.dumps({'method':method,'path':path,'status':code,'responseSha256':digest(data)})+'\n')
  if code!=status:raise RuntimeError(f'{method} {path}: expected {status}, got {code}: '+data[:1500].decode(errors='replace'))
  return data,rh
 def j(self,*args,**kwargs):return json.loads(self.call(*args,**kwargs)[0])
 def artifact(self,name,data):
  (self.path/name).write_bytes(data);self.manifest['artifacts'][name]={'sha256':digest(data),'bytes':len(data)};self.record()
 def stop(self):
  for p,log in reversed(self.children):
   if p.poll()is None:
    p.terminate()
    try:p.wait(timeout=10)
    except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
   log.close()
  self.manifest['running']=False;self.record()
 def execute(self):
  source=self.start('source');target=self.start('case-restored');history=self.start('knowledge-history')
  for url in(source,target,history):assert self.j(url,'GET','/api/v1/cases')==[]
  case={'caseId':CID,'schemaVersion':'1.0.0','title':'Synthetic stage demonstration ONLY','accidentType':'Collision','incidentTimeUtc':'2026-01-01T00:00:00Z','caseEpochUtc':'2026-01-01T00:00:00Z','displayTimeZoneOffsetMinutes':0,'incidentLocation':{'latDeg':31,'lonDeg':121,'heightM':0},'isFictionalDemo':True,'accidentCode':'','accidentGrade':'','seaLevelOffsetM':0,'leadInvestigator':'','agencyName':'','summaryNotes':''}
  self.j(source,'POST','/api/v1/cases',case,status=201)
  vessel={'caseId':CID,'vesselId':VID,'name':'Fictional Stage Ship'};self.j(source,'POST',BASE+'/vessels',vessel,status=201)
  evidence=(FIX/'source.txt').read_bytes();self.artifact('synthetic-source.txt',evidence)
  b={'profile':'mcis-evidence-intake-v1','fileName':'synthetic-source.txt','contentBase64':base64.b64encode(evidence).decode(),'title':'Synthetic witness material','source':'Fictional scripted fixture','extractedBy':'Synthetic Stage Script','extractedUtc':'2026-01-01T00:00:00Z','category':'Document','confidentiality':'Restricted','note':'No real accident or person'}
  p=self.j(source,'POST',BASE+'/evidence-intakes:preview',b);er=self.j(source,'POST',BASE+'/evidence-intakes:commit',{**b,'confirmed':True,'requestDigest':p['requestDigest']});eid=er['evidenceId']
  csv=(FIX/'track.csv').read_bytes();self.artifact('synthetic-track.csv',csv)
  b={'profile':'mcis-utc-v1','vesselId':VID,'fileName':'synthetic-track.csv','source':'Synthetic fixed UTC fixture','timeBasis':'Scripted UTC; not observed AIS','contentBase64':base64.b64encode(csv).decode()}
  p=self.j(source,'POST',BASE+'/track-imports:preview',b);assert p['canCommit']
  track_body={**b,'previewDigest':p['previewDigest'],'confirmed':True}
  track=self.j(source,'POST',BASE+'/track-imports:commit',track_body)
  create={'requestId':str(uuid.uuid4()),'backupAcknowledged':True,'interviewee':{'intervieweeId':'SYN-WITNESS','name':'Fictional Witness','role':'Witness','affiliation':'Synthetic stage fixture'},'startUtc':'2026-01-01T00:00:00Z','sourceEvidenceId':eid}
  r=self.j(source,'POST',BASE+'/manual-interviews',create,status=201);rid=r['receipt']['recordId'];current=self.j(source,'GET',BASE+'/manual-interviews/'+rid)
  turn={'requestId':str(uuid.uuid4()),'backupAcknowledged':True,'expectedDigest':current['documentDigest'],'question':'Synthetic question: what did the fictional witness see?','answer':'Synthetic answer only: no real observations are asserted.','sensitiveFragments':[]}
  self.j(source,'POST',BASE+'/manual-interviews/'+rid+'/turns',turn,status=201)
  report=self.j(source,'POST',BASE+'/reports',{'templateId':'imo-cic','lang':'bilingual'},status=201);rpt=report['reportId']
  for section in report['sections']:self.j(source,'PATCH',BASE+'/reports/'+rpt+'/sections/'+section['sectionId'],{'action':'confirm','reason':'SYNTHETIC SCRIPTED REVIEW SIMULATION ONLY; not expert approval or factual confirmation'})
  finalreport=self.j(source,'GET',BASE+'/reports/'+rpt)
  assert finalreport['sections'] and all(section['status']=='Confirmed'for section in finalreport['sections'])
  self.manifest['ids']={'evidenceId':eid,'interviewId':rid,'reportId':rpt,'manualCreateRequestId':create['requestId'],'manualTurnRequestId':turn['requestId'],'trackDigest':track['previewDigest']};self.record()
  before={key:self.j(source,'GET',BASE+suffix)for key,suffix in [('case',''),('vessels','/vessels'),('tracks','/tracks'),('interview','/interviews/'+rid),('report','/reports/'+rpt)]}
  self.artifact('source-state.json',json.dumps(before,ensure_ascii=False,indent=2).encode())
  raw=self.call(source,'GET',BASE+'/export')[0];self.artifact('synthetic-case.mcase',raw)
  p=self.j(target,'POST','/api/v1/packages/intakes:preview',{'contentBase64':base64.b64encode(raw).decode()});assert p['packageVersion']=='1.3.0'
  receipt=self.j(target,'POST','/api/v1/packages/intakes:commit',{'contentBase64':base64.b64encode(raw).decode(),'confirmed':True,'sourceSha256':digest(raw)})
  after={key:self.j(target,'GET',BASE+suffix)for key,suffix in [('case',''),('vessels','/vessels'),('tracks','/tracks'),('interview','/interviews/'+rid),('report','/reports/'+rpt)]}
  self.artifact('restored-state.json',json.dumps(after,ensure_ascii=False,indent=2).encode())
  assert before==after,'Restored API documents differ: '+','.join(k for k in before if before[k]!=after[k])
  self.call(target,'GET',BASE+'/manual-interviews/requests/'+turn['requestId'],status=409)
  self.call(target,'GET',BASE+'/evidence-intakes/'+er['requestDigest'],status=409)
  assert self.call(target,'GET',BASE+'/archive-history/evidence/'+eid+'/content')[0]==evidence
  prov=self.j(target,'GET',BASE+'/archive-history/provenance/report/'+rpt)['provenance'];assert prov['sourceArchiveSha256']==digest(raw)and prov['changedSinceImport']is False
  track_get=self.j(target,'GET',BASE+'/track-imports/'+track['previewDigest'],status=409)
  track_replay=self.j(target,'POST',BASE+'/track-imports:commit',track_body,status=409)
  track_list=self.j(target,'GET',BASE+'/track-imports?vesselId='+VID,status=409)
  checks={'get':track_get,'sameBodyCommit':track_replay,'list':track_list}
  self.artifact('restored-track-receipt-check.json',json.dumps(checks,ensure_ascii=False,indent=2).encode())
  assert all(v.get('code')=='ARCHIVE_HISTORY_ONLY'for v in checks.values()),'Restored W10 must refuse active receipt, not merely any error'
  hp=BASE+'/archive-history/track-imports/'+track['previewDigest']
  historic=self.j(target,'GET',hp)
  assert historic['mode']=='archive-only'and historic['digest']==track['previewDigest']
  assert self.call(target,'GET',hp+'/source')[0]==csv
  originalreport=self.call(source,'GET',BASE+'/track-imports/'+track['previewDigest']+'/report')[0]
  assert self.call(target,'GET',hp+'/report')[0]==originalreport
  self.manifest['trackReceiptReactivated']=False;self.record()
  card={'kind':'Case','title':'Synthetic stage knowledge','summary':'Fictional workflow test','body':'No real accident findings.','tags':['synthetic'],'applicability':'Software demonstration only','source':{'type':'Synthetic','title':'Stage fixture','locator':'paragraph1','excerpt':'No real accident findings.','rightsNote':'Synthetic fixture authored for testing'}}
  kb='/api/v1/knowledge';d=self.j(source,'POST',kb+'/cards',card,status=201);kid=d['cardId']
  review={'decision':'Published','expectedDigest':d['contentDigest'],'note':'SYNTHETIC SCRIPTED REVIEW SIMULATION, not real expert approval','sourceVerified':True,'rightsVerified':True,'releaseApproved':True}
  self.j(source,'POST',kb+'/cards/'+kid+'/review',review);assert self.j(source,'GET',kb+'/cards')['total']==1
  self.j(source,'POST',kb+'/cards/'+kid+'/review',{**review,'decision':'Withdrawn'});assert self.j(source,'GET',kb+'/cards')['total']==0
  archive=self.call(source,'GET',kb+'/archives:export')[0];self.artifact('synthetic-knowledge.json',archive);sha=digest(archive)
  kr=self.j(history,'POST',kb+'/archives',raw=archive,status=201,extra={'Content-Type':'application/json','X-Archive-Sha256':sha})
  assert self.call(history,'GET',kb+'/archives/'+sha+'/content')[0]==archive
  assert kr['archive']['summary']['restoreMode']=='isolated-read-only-history'
  for state in('Candidate','Published','Rejected','Withdrawn'):assert self.j(history,'GET',kb+'/cards?status='+state)['total']==0
  self.manifest['ids'].update(cardId=kid,knowledgeArchiveSha256=sha);self.record()
  if self.manifest.get('trackReceiptReactivated'):raise RuntimeError('Historical W10 receipt reactivated after restore; see restored-track-receipt-check.json')
  self.manifest['status']='passed';self.record()

def main():
 if not __debug__:raise RuntimeError("Optimized Python disables validation; run without -O or PYTHONOPTIMIZE")
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);parser.add_argument('--hold',action='store_true');args=parser.parse_args()
 if args.output:
  path=args.output.absolute()
  if '..'in path.parts or any(p.is_symlink()for p in (path,*path.parents)):raise ValueError('Symlink/traversal output paths are not allowed')
  path.mkdir(parents=False,exist_ok=False)
 else:path=Path(tempfile.mkdtemp(prefix='mcis-stage-demo-'))
 run=Run(path);print(str(path),flush=True)
 try:
  run.execute();print('Synthetic API verification passed. '+str(path/'run.json'),flush=True)
  if args.hold:
   print('Owned loopback services remain until Ctrl-C. See run.json.',flush=True)
   while True:time.sleep(1)
 except KeyboardInterrupt:
  if run.manifest['status']!='passed':run.manifest.update(status='interrupted')
 except Exception as exc:
  run.manifest.update(status='failed',error=str(exc));print(str(exc),file=sys.stderr);return 1
 finally:run.stop()
 return 0
if __name__=='__main__':raise SystemExit(main())
