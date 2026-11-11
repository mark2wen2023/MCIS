"""Loopback-only canonical-source report HTTP acceptance, not browser acceptance.
Requires MCIS_HTTP_OUT (new directory), optional MCIS_REPO, MCIS_DOTNET.
Uses fresh disposable service data; generated exports remain local.
"""
from pathlib import Path
import os,tempfile,socket,subprocess,urllib.request,time,json,hashlib,zipfile,io,signal
ROOT=Path(os.environ.get('MCIS_REPO', str(Path(__file__).resolve().parents[2]))).resolve()
OUT=Path(os.environ['MCIS_HTTP_OUT']).resolve();OUT.mkdir(parents=True,exist_ok=False)
SHA='bca8f8b8ba04a5d0669a121bc6c9380c8cd6f8397f67be2d0b30b38871c22ef2'
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
data=tempfile.mkdtemp(prefix='canonical-report-http-');env=dict(os.environ,MCIS_DATA_DIR=data,MCIS_PORT=str(port),MCIS_CORE=str(ROOT/'tools/mcis-core/mcis-core.sh'));env.pop('MCIS_DB_URL',None)
log=open(OUT/'service.log','w');p=subprocess.Popen([str(ROOT/'service/.venv/bin/python'),'-m','mcis_service'],cwd=ROOT/'service',env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
base=f'http://127.0.0.1:{port}/api/v1';pre='/cases/CJK-2024-1230-YangZe22-VegaDream';checks=[]
def req(path,body=None):
 r=urllib.request.Request(base+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json','X-MCIS-Role':'Investigator','X-MCIS-Operator':'CanonicalHTTPReview'})
 return urllib.request.urlopen(r,timeout=60)
def check(name,ok):checks.append({'name':name,'passed':bool(ok)});assert ok,name
try:
 for _ in range(150):
  try:req('/health').close();break
  except Exception:time.sleep(.2)
 check('source canonical sha',hashlib.sha256((ROOT/'reports/yangze22/report.txt').read_bytes()).hexdigest()==SHA)
 evidence=json.load(req(pre+'/evidence'));ev=next(e for e in evidence if e['evidenceId']=='EV-201');check('fresh evidence canonical sha',ev['sha256']==SHA)
 r=req(pre+'/reports',{'templateId':'cn-msa','lang':'zh'});check('report create HTTP201',r.status==201);doc=json.load(r);text=json.dumps(doc,ensure_ascii=False);check('canonical sha in generated report',SHA in text);check('public report has source sections',bool(doc['sections']) and '长江口' in text)
 rid=doc['reportId'];details={}
 for fmt,magic in [('pdf',b'%PDF'),('docx',b'PK')]:
  r=req(pre+f'/reports/{rid}/export?format={fmt}&lang=zh');raw=r.read();check(fmt+' export HTTP200',r.status==200);check(fmt+' signature',raw.startswith(magic));check(fmt+' response sha matches bytes',r.headers['x-sha256']==hashlib.sha256(raw).hexdigest());(OUT/('report.'+fmt)).write_bytes(raw);details[fmt]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
  if fmt=='docx':check('DOCX embeds canonical source sha',SHA in zipfile.ZipFile(io.BytesIO(raw)).read('word/document.xml').decode())
 subprocess.run(['pdftotext',str(OUT/'report.pdf'),str(OUT/'pdf-text.txt')],check=True);check('PDF readable source excerpt', '长江口' in (OUT/'pdf-text.txt').read_text())
 (OUT/'summary.json').write_text(json.dumps({'checks':checks,'exports':details,'sourceSha':SHA,'root':str(ROOT),'dataDir':data},ensure_ascii=False,indent=2))
finally:
 (OUT/'checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2));os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=15);log.close()
