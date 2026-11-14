import unittest, tempfile, sys
from pathlib import Path
from fastapi.testclient import TestClient
from mcis_service.main import create_app
from mcis_service.config import Settings
from mcis_service.common.case_identity import Principal, CaseMember
from mcis_service.cases.models import CaseRow
from mcis_service.db import put_doc

class HttpTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.st=Settings(data_dir=Path(self.tmp.name),seed_demo=False)
  self.users={'a':Principal('issuer','a','same','server-session'),'b':Principal('issuer','b','same','server-session'),'c':Principal('issuer','c','other','server-session')}
  self.app=create_app(self.st,identity_mode='authenticated',identity_verifier=lambda t:self.users[t]);self.c=TestClient(self.app)
  with self.app.state.db.session() as s:
   for cid in ('A','B','LEGACY'):put_doc(s,CaseRow,cid,cid,{'caseId':cid,'title':cid+' hidden','accidentGrade':'minor'})
   s.add_all([CaseMember(case_id='A',issuer='issuer',subject='a'),CaseMember(case_id='B',issuer='issuer',subject='b')])
 def tearDown(self): self.c.close();self.app.state.db.engine.dispose();self.tmp.cleanup()
 def h(self,t='a'):return {'Authorization':'Bearer '+t,'X-MCIS-Role':'LeadInvestigator','X-MCIS-Operator':'b'}
 def test_authenticated_missing_verifier_denied(self):
  with self.assertRaises(ValueError):create_app(self.st,identity_mode='authenticated')
 def test_anonymous_and_spoof_denied(self):
  self.assertEqual(self.c.get('/api/v1/cases',headers={'X-MCIS-Role':'LeadInvestigator'}).status_code,401)
 def test_two_subject_lists(self):
  for t,cid in [('a','A'),('b','B')]:self.assertEqual([r['caseId'] for r in self.c.get('/api/v1/cases',headers=self.h(t)).json()],[cid])
 def test_nonmember_list_empty(self):self.assertEqual(self.c.get('/api/v1/cases',headers=self.h('c')).json(),[])
 def test_detail_and_counts_denied(self):
  for suffix in ('','/overview'):
   b=self.c.get('/api/v1/cases/B'+suffix,headers=self.h());missing=self.c.get('/api/v1/cases/missing'+suffix,headers=self.h())
   self.assertEqual(b.status_code,404);self.assertEqual(b.json(),missing.json());self.assertNotIn('hidden',b.text)
 def test_own_counts_allowed(self):self.assertEqual(self.c.get('/api/v1/cases/A/overview',headers=self.h()).status_code,200)
 def test_revoke(self):
  with self.app.state.db.session() as s:s.query(CaseMember).filter_by(subject='a').update({'active':False})
  self.assertEqual(self.c.get('/api/v1/cases/A',headers=self.h()).status_code,404)
 def test_unintegrated_and_write_denied(self):
  self.assertEqual(self.c.get('/api/v1/cases/A/evidence',headers=self.h()).status_code,403)
  self.assertEqual(self.c.post('/api/v1/cases',headers=self.h(),json={}).status_code,403)
 def test_source_variant_denied(self):
  self.users['a']=Principal('issuer','a','same','Demo ')
  self.assertEqual(self.c.get('/api/v1/cases',headers=self.h()).status_code,401)
 def test_legacy_denied(self):self.assertEqual(self.c.get('/api/v1/cases/LEGACY',headers=self.h()).status_code,404)
 def test_explicit_demo(self):
  app=create_app(self.st,identity_mode='local-demo')
  with TestClient(app) as c:
   r=c.get('/api/v1/cases');self.assertEqual(len(r.json()),3);self.assertEqual(r.headers['X-MCIS-Identity-Mode'],'local-demo')
  app.state.db.engine.dispose()
 def test_legacy_factory_compatible_and_warned(self):
  with self.assertWarns(RuntimeWarning):app=create_app(self.st)
  with TestClient(app) as c:
   self.assertEqual(c.get('/api/v1/health').status_code,200)
   self.assertEqual(c.get('/api/v1/cases').headers['X-MCIS-Identity-Mode'],'local-demo')
  app.state.db.engine.dispose()
 def test_verifier_without_explicit_authenticated_mode_rejected(self):
  with self.assertRaises(ValueError):
   create_app(self.st,identity_verifier=lambda t:self.users[t])
 def test_explicit_demo_rejects_any_non_none_verifier(self):
  for verifier in (lambda t:self.users[t], False, '', 0, object()):
   with self.subTest(verifier=type(verifier)),self.assertRaises(ValueError):
    create_app(self.st,identity_mode='local-demo',identity_verifier=verifier)
 def test_preflight_is_not_authorization(self):
  p='/api/v1/cases/A/evidence'
  r=self.c.options(p,headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'GET','Access-Control-Request-Headers':'authorization'})
  self.assertEqual(r.status_code,200)
  self.assertEqual(self.c.get(p).status_code,401)
  self.assertEqual(self.c.get(p,headers=self.h()).status_code,403)
 def test_cli_default_loopback_demo(self):
  from unittest.mock import patch, MagicMock
  from mcis_service.__main__ import main
  with patch('mcis_service.__main__.create_app') as factory,patch('mcis_service.__main__.uvicorn.run') as run:
   main([])
   self.assertEqual(factory.call_args.kwargs['identity_mode'],'local-demo')
   self.assertEqual(run.call_args.kwargs['host'],'127.0.0.1')
 def test_cli_authenticated_never_falls_back(self):
  from unittest.mock import patch
  from mcis_service.__main__ import main
  with patch('mcis_service.__main__.create_app') as factory,patch('mcis_service.__main__.uvicorn.run') as run:
   with self.assertRaises(SystemExit) as error:main(['--identity-mode','authenticated'])
   self.assertEqual(error.exception.code,2);factory.assert_not_called();run.assert_not_called()
if __name__=='__main__':unittest.main(verbosity=2)

