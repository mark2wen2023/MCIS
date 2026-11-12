"""W4.2 implementation tests: synthetic bytes and isolated databases only."""
import base64,json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from mcis_service.main import create_app
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.audit.models import AuditEventRow
from mcis_service.evidence.models import EvidenceRow,CustodyEventRow
from mcis_service.evidence_intake import router as module
from mcis_service.evidence_intake.parser import MAX_BODY,MAX_BYTES,PREFIX
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
from .conftest import H,make_settings
CASE='W42-SYNTHETIC';URL=f'/api/v1/cases/{CASE}/evidence-intakes'
RAW=b'\x00\xffsynthetic opaque\r\nnot parsed\x00'
@pytest.fixture
def local(tmp_path):
 app=create_app(make_settings(tmp_path,False))
 case={'caseId':CASE,'schemaVersion':'1.0.0','title':'synthetic','isFictionalDemo':True,'caseEpochUtc':'2026-01-01T00:00:00Z','incidentTimeUtc':'2026-01-01T00:00:00Z','incidentLocation':{'lonDeg':121,'latDeg':31},'displayTimeZoneOffsetMinutes':0}
 with app.state.db.session() as s:put_doc(s,CaseRow,CASE,CASE,case)
 with TestClient(app) as c:yield c,app

def body(raw=RAW,**changes):return {'profile':'mcis-evidence-intake-v1','fileName':'synthetic.bin','title':'  Synthetic <tag>  ','source':'Declared source\ntransfer not authenticated','extractedBy':'Synthetic collector','extractedUtc':'2020-02-29T23:59:59Z','category':'Other','confidentiality':'Restricted','note':'  original note\n  ','contentBase64':base64.b64encode(raw).decode(),**changes}
def prepared(c,b=None):
 b=b or body();r=c.post(URL+':preview',json=b);assert r.status_code==200,r.text
 return {**b,'requestDigest':r.json()['requestDigest'],'confirmed':True}
def counts(app):
 with app.state.db.session() as s:return tuple(s.query(m).count() for m in [EvidenceRow,CustodyEventRow,AuditEventRow])
def save(c,b=None):
 b=prepared(c,b);r=c.post(URL+':commit',json=b);assert r.status_code==200,r.text
 return b,r.json()
def test_happy(local):
 c,app=local;b=prepared(c);assert counts(app)==(0,0,0) and not list(app.state.settings.blob_dir.rglob('source.bin'))
 r=c.post(URL+':commit',json=b);assert r.status_code==200,r.text;x=r.json();d=x['requestDigest']
 assert x['metadata']['extractedUtc']=='2020-02-29T23:59:59Z' and x['registeredUtc']!=x['metadata']['extractedUtc']
 assert x['evidence']['status']=='Unverified' and not x['replayed'];assert counts(app)==(1,1,1)
 y=c.get(URL+'/'+d);assert y.status_code==200,y.text
 assert y.json()=={**x,'replayed':True};assert c.post(URL+':commit',json=b).json()==y.json()
 assert c.get(f'/api/v1/cases/{CASE}/evidence/{x["evidenceId"]}/intake').json()==y.json()
 assert counts(app)==(1,1,1)
 r=c.post(URL+'/'+d+':download',json={'purpose':'  Review copy\nnot external transfer  '});assert r.status_code==200 and r.content==RAW
 assert r.headers['x-sha256']==x['sourceSha256'];assert counts(app)==(1,2,2)
 assert c.get(URL+'/'+d).json()['evidence']['accessCount']==1
 with app.state.db.session() as s:assert s.query(CustodyEventRow).order_by(CustodyEventRow.seq.desc()).first().detail=='  Review copy\nnot external transfer  '
@pytest.mark.parametrize('key,value',[('extractedUtc',None),('extractedUtc','0001-01-01T00:00:00Z'),('extractedUtc','0999-12-31T23:59:59Z'),('extractedUtc','2026-01-01T00:00:00'),('extractedUtc','2026-01-01T00:00:00.1Z'),('extractedUtc','2026-02-29T00:00:00Z'),('extractedUtc','2026-01-01T00:00:60Z'),('fileName','../x'),('fileName','x\\y'),('fileName','x\ny'),('fileName','.'),('source',' '),('title',''),('extractedBy',''),('confidentiality','Normal'),('category','unknown'),('note','x'*2001),('profile','other'),('contentBase64','!!'),('contentBase64','Zh=='),('contentBase64',None)])
def test_invalid(local,key,value):
 c,app=local;assert c.post(URL+':preview',json=body(**{key:value})).status_code==422;assert counts(app)==(0,0,0)
@pytest.mark.parametrize('mutate',[lambda b:{**b,'extra':1},lambda b:{k:v for k,v in b.items() if k!='extractedUtc'}])
def test_fields(local,mutate):
 c,app=local;assert c.post(URL+':preview',json=mutate(body())).status_code==422
@pytest.mark.parametrize('raw',[b'',b'\xef\xbb\xbftext\r\n',b'<script>alert(1)</script>'])
def test_opaque_empty(local,raw):
 c,_=local;b,r=save(c,body(raw));q=c.post(URL+'/'+r['requestDigest']+':download',json={'purpose':'synthetic'});assert q.content==raw and r['byteLength']==len(raw)
@pytest.mark.parametrize('role',['ExternalExpert','InterestedState','AgentService','Public'])
def test_roles(local,role):
 c,app=local;b,r=save(c);h=H(role);d=r['requestDigest']
 for suffix in [':preview',':commit']:assert c.post(URL+suffix,json=body() if suffix==':preview' else b,headers=h).status_code==403
 assert c.get(URL+'/'+d,headers=h).status_code==403
 assert c.get(f'/api/v1/cases/{CASE}/evidence/{r["evidenceId"]}/intake',headers=h).status_code==403
 assert c.post(URL+'/'+d+':download',json={'purpose':'x'},headers=h).status_code==403
 assert counts(app)==(1,1,1)
@pytest.mark.parametrize('kind',['readOnly','deny','restricted'])
def test_policy_changes(local,kind):
 c,app=local;b,r=save(c);p=default_policy()
 if kind=='readOnly':p['matrix']['Investigator']['evidence_meta']='ReadOnly'
 elif kind=='deny':p['matrix']['Investigator']['evidence_meta']='Deny'
 else:p['fieldRules'].append({'field':'evidence.restricted','method':'Remove','appliesTo':['Investigator']})
 with app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',p)
 assert c.post(URL+':preview',json=body()).status_code==403 and c.post(URL+':commit',json=b).status_code==403
 expected=200 if kind=='readOnly' else 403
 assert c.get(URL+'/'+r['requestDigest']).status_code==expected
 assert c.post(URL+'/'+r['requestDigest']+':download',json={'purpose':'x'}).status_code==expected
@pytest.mark.parametrize('confirm',[False,1,'true',None])
def test_confirm(local,confirm):
 c,app=local;b=prepared(c);assert c.post(URL+':commit',json={**b,'confirmed':confirm}).status_code==422;assert counts(app)==(0,0,0)
def test_binding(local):
 c,app=local;b=prepared(c)
 for changes in [{'source':'changed'},{'note':'changed'},{'fileName':'other.bin'},{'contentBase64':'eA=='}]:assert c.post(URL+':commit',json={**b,**changes}).status_code==409
 assert c.post(URL+':commit',json=b,headers=H(operator='other')).status_code==409
 assert c.post(URL+':commit',json=b,headers=H('LeadInvestigator')).status_code==409
 assert counts(app)==(0,0,0)
def test_same_request_race(local):
 c,app=local;b=prepared(c)
 with ThreadPoolExecutor(2) as pool:rs=list(pool.map(lambda _:c.post(URL+':commit',json=b),range(2)))
 assert [r.status_code for r in rs]==[200,200];assert sorted(r.json()['replayed'] for r in rs)==[False,True];assert counts(app)==(1,1,1)
def test_different_request_race(local):
 c,app=local;bs=[prepared(c),prepared(c,body(source='distinct declaration'))]
 with ThreadPoolExecutor(2) as pool:rs=list(pool.map(lambda b:c.post(URL+':commit',json=b),bs))
 assert [r.status_code for r in rs]==[200,200] and len({r.json()['evidenceId'] for r in rs})==2;assert counts(app)==(2,2,2)
def test_commit_rollback(local,monkeypatch):
 c,app=local;b=prepared(c);real=module.exclusive_write
 def fail(s):raise RuntimeError('synthetic commit failure')
 def install(path,raw,created):real(path,raw,created);event.listen(app.state.db.SessionLocal.class_,'before_commit',fail,once=True)
 monkeypatch.setattr(module,'exclusive_write',install)
 with pytest.raises(RuntimeError):c.post(URL+':commit',json=b)
 assert counts(app)==(0,0,0) and not list(app.state.settings.blob_dir.rglob('source.bin'))
def test_file_failure_and_cleanup_failure(local,monkeypatch):
 c,app=local;b=prepared(c);real=module.exclusive_write
 def fail(path,raw,created):real(path,raw,created);raise OSError('synthetic')
 monkeypatch.setattr(module,'exclusive_write',fail)
 with pytest.raises(OSError):c.post(URL+':commit',json=b)
 assert counts(app)==(0,0,0) and not list(app.state.settings.blob_dir.rglob('source.bin'))
 unlink=Path.unlink
 def fail_unlink(p,*a,**k):
  if p.name=='source.bin':raise OSError('synthetic cleanup failure')
  return unlink(p,*a,**k)
 monkeypatch.setattr(Path,'unlink',fail_unlink)
 r=c.post(URL+':commit',json=b);assert r.status_code==500 and r.json()['code']=='INTAKE_CLEANUP_FAILED';assert counts(app)==(0,0,0)
def test_existing_and_symlink(local,tmp_path):
 c,app=local;b=prepared(c);p=app.state.settings.blob_dir/CASE/module.rel_for(b['requestDigest']);p.parent.mkdir(parents=True);p.write_bytes(b'untouched')
 assert c.post(URL+':commit',json=b).status_code==409 and p.read_bytes()==b'untouched'
 p.unlink();target=tmp_path/'outside';target.write_bytes(b'outside');p.symlink_to(target)
 assert c.post(URL+':commit',json=b).status_code==409 and target.read_bytes()==b'outside';assert counts(app)==(0,0,0)
@pytest.mark.parametrize('damage',['file','missing_file','title','source','path','hash','category','missing_evidence','duplicate_evidence','change'])
def test_integrity(local,damage):
 c,app=local;b,r=save(c);d=r['requestDigest'];p=app.state.settings.blob_dir/CASE/module.rel_for(d)
 if damage=='file':p.write_bytes(b'bad')
 elif damage=='missing_file':p.unlink()
 else:
  with app.state.db.session() as s:
   row=s.query(EvidenceRow).first()
   if damage=='missing_evidence':s.delete(row)
   elif damage=='duplicate_evidence':put_doc(s,EvidenceRow,CASE,'EV-999',{**row.doc,'evidenceId':'EV-999'})
   elif damage=='change':module.evidence.append_custody(s,case_id=CASE,evidence_id=r['evidenceId'],kind='Change',operator='synthetic',role='Investigator',sha256=r['sourceSha256'],detail='unsupported')
   else:row.doc={**row.doc,{'path':'relativePath','hash':'sha256'}.get(damage,damage):'changed'}
 assert c.get(URL+'/'+d).status_code==409
 assert c.post(URL+':commit',json=b).status_code==409
 assert c.post(URL+'/'+d+':download',json={'purpose':'x'}).status_code==409

def test_note_change_legal(local):
 c,app=local;b,r=save(c);eid=r['evidenceId'];q=c.patch(f'/api/v1/cases/{CASE}/evidence/{eid}',json={'note':'new note'});assert q.status_code==200
 q=c.get(URL+'/'+r['requestDigest']);assert q.status_code==200,q.text
 assert q.json()['metadata']['note']==body()['note'] and q.json()['evidence']['note']=='new note'
@pytest.mark.parametrize('data',[b'{"x":1,"x":2}',b'{"x":NaN}',b'\xff',b'['*1100+b']'*1100])
def test_json(local,data):
 c,_=local;assert c.post(URL+':preview',content=data,headers={'content-type':'application/json'}).status_code==422

def test_limits(local):
 c,app=local
 assert c.post(URL+':preview',content=b' '*(MAX_BODY+1),headers={'content-type':'application/json'}).status_code==413
 assert c.post(URL+':preview',json=body(b'x'*(MAX_BYTES+1))).status_code==413
 q=c.post(URL+':preview',json=body(b'x'*MAX_BYTES));assert q.status_code==200,q.text;assert q.json()['byteLength']==MAX_BYTES
 assert counts(app)==(0,0,0)
@pytest.mark.parametrize('purpose',[None,'',' ',1,'x'*1001])
def test_download_purpose(local,purpose):
 c,app=local;b,r=save(c);assert c.post(URL+'/'+r['requestDigest']+':download',json={'purpose':purpose}).status_code==422;assert counts(app)==(1,1,1)
def test_package_roundtrip(local,tmp_path):
 c,app=local;b,r=save(c);d=r['requestDigest'];data=c.get(f'/api/v1/cases/{CASE}/export').content
 other=tmp_path/'other';other.mkdir();app2=create_app(make_settings(other,False))
 with TestClient(app2) as c2:
  q=c2.post('/api/v1/cases:import',content=data,headers={'Content-Type':'application/zip'});assert q.status_code==201,q.text
  q=c2.get(URL+'/'+d);assert q.status_code==200,q.text;assert q.json()=={**r,'replayed':True}
  q=c2.post(URL+'/'+d+':download',json={'purpose':'synthetic migrated copy'});assert q.status_code==200 and q.content==RAW

@pytest.mark.parametrize("stamp",["1000-01-01T00:00:00Z","9999-12-31T23:59:59Z"])
def test_year_boundaries(local,stamp):
 c,_=local;b,r=save(c,body(extractedUtc=stamp));assert c.get(URL+"/"+r["requestDigest"]).status_code==200


def test_request_exact_budget_and_type(local):
 c,app=local;b=json.dumps(body()).encode();padded=b+b' '*(MAX_BODY-len(b))
 assert c.post(URL+':preview',content=padded,headers={'content-type':'application/json'}).status_code==200
 assert c.post(URL+':preview',content=b,headers={'content-type':'text/plain'}).status_code==415
 assert counts(app)==(0,0,0)

@pytest.mark.parametrize('damage',['missing_register','detail','line','operator','duplicate_register'])
def test_registration_corruption(local,damage):
 c,app=local;b,r=save(c);d=r['requestDigest']
 from sqlalchemy import text as sqltext
 with app.state.db.engine.begin() as conn:
  conn.execute(sqltext('DROP TRIGGER custody_events_no_update'))
  conn.execute(sqltext('DROP TRIGGER custody_events_no_delete'))
 with app.state.db.session() as s:
  row=s.query(CustodyEventRow).first()
  if damage=='missing_register':s.delete(row)
  elif damage=='duplicate_register':
   module.evidence.append_custody(s,case_id=CASE,evidence_id=r['evidenceId'],kind='Register',operator=row.operator,role='Investigator',sha256=row.sha256,detail=row.detail,item=s.query(EvidenceRow).first().doc)
  elif damage=='detail':row.detail=row.detail.replace('Synthetic collector','Changed collector')
  elif damage=='line':row.line='{}'
  else:row.operator='other'
 assert c.get(URL+'/'+d).status_code==409
 assert c.post(URL+':commit',json=b).status_code==409
 assert c.post(URL+'/'+d+':download',json={'purpose':'x'}).status_code==409

def test_no_reference_orphan(local):
 c,app=local;b=prepared(c);p=app.state.settings.blob_dir/CASE/module.rel_for(b['requestDigest']);p.parent.mkdir(parents=True);p.write_bytes(RAW)
 assert c.get(URL+'/'+b['requestDigest']).status_code==409
 assert c.post(URL+':commit',json=b).status_code==409 and p.read_bytes()==RAW
 assert counts(app)==(0,0,0)

def test_parent_symlink(local,tmp_path):
 c,app=local;b=prepared(c);folder=app.state.settings.blob_dir/CASE/'raw';folder.parent.mkdir(parents=True);outside=tmp_path/'outside';outside.mkdir();folder.symlink_to(outside,target_is_directory=True)
 assert c.post(URL+':commit',json=b).status_code==409;assert not list(outside.iterdir());assert counts(app)==(0,0,0)

def test_other_case_and_legacy(local):
 c,app=local;b,r=save(c)
 assert c.get('/api/v1/cases/OTHER/evidence-intakes/'+r['requestDigest']).status_code==404
 with app.state.db.session() as s:
  old={**s.query(EvidenceRow).first().doc,'evidenceId':'EV-999','relativePath':'raw/legacy.bin'};put_doc(s,EvidenceRow,CASE,'EV-999',old)
 assert c.get(f'/api/v1/cases/{CASE}/evidence/EV-999/intake').status_code==404

@pytest.mark.skipif(not __import__('os').path.isfile(__import__('os').environ.get('MCIS_DOTNET',str(Path.home()/'.dotnet/dotnet'))),reason='existing .NET SDK required')
def test_intake_csharp_custody_compatibility(local,tmp_path):
 import io,subprocess,zipfile
 c,_=local;b,r=save(c,body(source='合成来源 "quoted"\ntransfer',title='合成副本 🧭',note='原文\\尾'))
 assert c.post(URL+'/'+r['requestDigest']+':download',json={'purpose':'合成核查\n副本'}).status_code==200
 data=c.get(f'/api/v1/cases/{CASE}/export').content
 with zipfile.ZipFile(io.BytesIO(data)) as z:(tmp_path/'custody.jsonl').write_bytes(z.read('audit/custody.jsonl'))
 compat=Path(__file__).resolve().parents[2]/'tools/mcis-compat/mcis-compat.sh'
 out=subprocess.run([str(compat),'custody',str(tmp_path/'custody.jsonl')],capture_output=True,text=True,timeout=300)
 assert out.returncode==0,out.stderr
 res=json.loads(out.stdout.strip().splitlines()[-1]);assert res['ok'] and res['items']==1 and res['restricted']==[r['evidenceId']],res


@pytest.mark.parametrize('category',['evidence_meta','testimony'])
def test_redacted_is_not_full_read(local,category):
 c,app=local;b,r=save(c);p=default_policy();p['matrix']['Investigator'][category]='Redacted'
 with app.state.db.session() as s:put_doc(s,AccessPolicyRow,CASE,'policy',p)
 assert c.get(URL+'/'+r['requestDigest']).status_code==403
 assert c.get(f'/api/v1/cases/{CASE}/evidence/{r["evidenceId"]}/intake').status_code==403
 assert c.post(URL+'/'+r['requestDigest']+':download',json={'purpose':'synthetic'}).status_code==403
 assert c.post(URL+':preview',json=body()).status_code==403
 assert c.post(URL+':commit',json=b).status_code==403
 assert counts(app)==(1,1,1)

@pytest.mark.parametrize('operator',['x'*201,'bad\noperator','bad\toperator','   '])
def test_download_operator_validation(local,operator):
 c,app=local;b,r=save(c)
 assert c.post(URL+'/'+r['requestDigest']+':download',json={'purpose':'synthetic'},headers=H(operator=operator)).status_code==422
 assert counts(app)==(1,1,1)

def test_maximum_file_persist_and_download(local):
 c,app=local;raw=bytes(range(256))*(MAX_BYTES//256);b,r=save(c,body(raw))
 assert r['byteLength']==MAX_BYTES and counts(app)==(1,1,1)
 q=c.post(URL+'/'+r['requestDigest']+':download',json={'purpose':'synthetic exact budget boundary'})
 assert q.status_code==200 and q.content==raw and q.headers['x-sha256']==r['sourceSha256']
 assert counts(app)==(1,2,2)
