import io, json, zipfile, os, tempfile
from pathlib import Path
import httpx
B='http://127.0.0.1:18883/api/v1'; C='CASE-2026-DEMO-LILY-MARY'; H={'X-MCIS-Role':'Investigator'}
OUT=Path(os.environ.get('MCIS_W83_ARTIFACT_DIR',tempfile.mkdtemp(prefix='w83-http-artifacts-')));OUT.mkdir(parents=True,exist_ok=True)
checks=[]
def ck(name,v):
 checks.append({'name':name,'passed':bool(v)});assert v,name
with httpx.Client(base_url=B,headers=H,trust_env=False) as c:
 before=c.get('/cases').json()
 r=c.get('/cases/'+C+'/export');ck('real export HTTP 200 ZIP',r.status_code==200 and r.headers['content-type']=='application/zip')
 package=r.content;(OUT/'valid.mcase').write_bytes(package)
 r=c.post('/packages:verify',content=package,headers={'Content-Type':'application/zip'});ck('export verifies actual SHA256',r.status_code==200 and r.json()['isValid'] and r.json()['caseId']==C)
 src=zipfile.ZipFile(io.BytesIO(package)); files={n:src.read(n) for n in src.namelist()}; manifest=json.loads(files['manifest.json']); target=manifest['files'][0]['relativePath']
 def zipit(data):
  out=io.BytesIO()
  with zipfile.ZipFile(out,'w') as z:
   for k,v in data.items():z.writestr(k,v)
  return out.getvalue()
 for name,data,field in [('tampered',{**files,target:b'changed'},'tamperedFiles'),('missing',{k:v for k,v in files.items() if k!=target},'missingFiles'),('extra',{**files,'unlisted.txt':b'extra'},'extraFiles')]:
  payload=zipit(data);(OUT/(name+'.mcase')).write_bytes(payload)
  result=c.post('/packages:verify',content=payload).json();ck(name+' reported',result[field] and result['isValid']==(name=='extra'))
 ck('bad ZIP rejected 422',c.post('/packages:verify',content=b'not zip').status_code==422)
 ck('empty body rejected 422',c.post('/packages:verify',content=b'').status_code==422)
 ck('missing case export 404',c.get('/cases/NO_SUCH_CASE/export').status_code==404)
 for role in ['Public','ExternalExpert','InterestedState','AgentService']:
  ck(role+' denied full export',c.get('/cases/'+C+'/export',headers={'X-MCIS-Role':role}).status_code==403)
 ck('LeadInvestigator exports',c.get('/cases/'+C+'/export',headers={'X-MCIS-Role':'LeadInvestigator'}).status_code==200)
 ck('verification did not import/change case list',c.get('/cases').json()==before)
(OUT/'http-results.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
print(f'{len(checks)} independent HTTP checks passed')
