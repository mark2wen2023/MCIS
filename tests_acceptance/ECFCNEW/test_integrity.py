"""Independent synthetic ECFC boundary acceptance. Never changes implementation."""
import copy,importlib,uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from mcis_service.config import Settings
from mcis_service.main import create_app
from mcis_service.db import put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.ecfc_drafts.models import EcfcWorksheetRow
from mcis_service.redaction.models import AccessPolicyRow
from mcis_service.redaction.policy import default_policy
A='INDEPENDENT-ECFC';BASE=f'/api/v1/cases/{A}/ecfc/'
H={'X-MCIS-Role':'LeadInvestigator','X-MCIS-Operator':'Independent-synthetic'}
def payload():return {'requestId':str(uuid.uuid4()),'expectedDigest':None,'acknowledgeArchiveLimitation':True,'expectedSources':[], 'draft':{'scope':'Independent synthetic','nodes':[],'edges':[]}}
@pytest.fixture
def env(tmp_path):
 st=Settings();st.data_dir=tmp_path;st.db_url=f'sqlite:///{tmp_path}/accept.db';st.seed_demo=False
 app=create_app(st)
 with app.state.db.session() as s:put_doc(s,CaseRow,A,A,{'caseId':A,'title':'Independent synthetic'})
 with TestClient(app) as c:yield c,app.state.db
@pytest.mark.parametrize('mutation',['case','status','digest','futureField','coreVersion'])
def test_corrupt_or_future_saved_document_is_not_returned(env,mutation):
 c,db=env;r=c.post(BASE+'save',json=payload(),headers=H);assert r.status_code==200,r.text
 with db.session() as s:
  row=s.get(EcfcWorksheetRow,A);d=copy.deepcopy(row.doc)
  if mutation=='case':d['caseId']='OTHER-CASE'
  if mutation=='status':d['status']='Confirmed'
  if mutation=='digest':d['digest']='0'*64
  if mutation=='futureField':d['futureUnsupportedSecret']='MUST NOT RETURN'
  if mutation=='coreVersion':d['validation']['coreVersion']='future/99'
  row.doc=d
 r=c.get(BASE+'draft',headers=H)
 assert r.status_code==409,r.text
 assert 'MUST NOT RETURN' not in r.text

def test_valid_unicode_budget_graph_can_preview(env):
 c,db=env;b=payload();b['draft']['nodes']=[{'id':f'n{i}','kind':'Event','text':'😀'*1000,'timeSeconds':None,'lane':i%5+1,'isPrimaryIncident':False,'evidenceIds':[]}for i in range(25)]
 import json
 raw=json.dumps({k:b[k]for k in ('draft','expectedSources')},ensure_ascii=False).encode()
 assert len(raw)<128*1024
 r=c.post(BASE+'preview',content=raw,headers={**H,'Content-Type':'application/json'})
 assert r.status_code==200,r.text

@pytest.mark.parametrize('target',['receipt','audit'])
def test_polluted_historical_snapshot_is_not_exposed(env,target):
 c,db=env;r=c.post(BASE+'save',json=payload(),headers=H);assert r.status_code==200
 doc=copy.deepcopy(r.json()['document']);doc['caseId']='OTHER-CASE';b=payload()
 api=importlib.import_module('mcis_service.ecfc_drafts.router')
 from mcis_service.ecfc_drafts.models import EcfcRequestRow,EcfcAuditRow
 import hashlib
 with db.session() as s:
  if target=='receipt':s.add(EcfcRequestRow(case_id=A,request_id=b['requestId'],request_digest=hashlib.sha256(api.canonical(b)).hexdigest(),operator=H['X-MCIS-Operator'],role='LeadInvestigator',response={**r.json(),'document':doc}))
  else:s.add(EcfcAuditRow(case_id=A,revision=2,doc={'caseId':A,'revision':2,'utc':doc['savedUtc'],'operator':H['X-MCIS-Operator'],'role':'LeadInvestigator','action':'ecfc.draft.save','requestId':b['requestId'],'beforeDigest':None,'afterDigest':doc['digest'],'before':None,'after':doc,'prevHash':'0'*64,'hash':'0'*64}))
 r=c.post(BASE+'save',json=b,headers=H)if target=='receipt'else c.get(BASE+'audit',headers=H)
 assert r.status_code==409,r.text
 assert 'OTHER-CASE'not in r.text

def test_coherent_current_digest_without_audit_update_is_refused(env):
 c,db=env;r=c.post(BASE+'save',json=payload(),headers=H);assert r.status_code==200
 api=importlib.import_module('mcis_service.ecfc_drafts.router')
 import hashlib
 with db.session() as s:
  row=s.get(EcfcWorksheetRow,A);d=copy.deepcopy(row.doc);d['draft']['scope']='Coherently recomputed but unaudited synthetic change'
  d['digest']=hashlib.sha256(api.canonical({k:d[k]for k in ('caseId','revision','draft','sources','validation')})).hexdigest();row.doc=d
 r=c.get(BASE+'draft',headers=H);assert r.status_code==409,r.text


@pytest.mark.parametrize('value',['missing',False,1,'true',None])
def test_archive_limitation_requires_exact_explicit_true(env,value):
 c,db=env;b=payload()
 if value=='missing':b.pop('acknowledgeArchiveLimitation')
 else:b['acknowledgeArchiveLimitation']=value
 r=c.post(BASE+'save',json=b,headers=H);assert r.status_code==422,r.text
 from sqlalchemy import select,func
 from mcis_service.ecfc_drafts.models import EcfcAuditRow,EcfcRequestRow
 with db.session()as s:assert all(s.scalar(select(func.count()).select_from(m))==0 for m in (EcfcWorksheetRow,EcfcAuditRow,EcfcRequestRow))
