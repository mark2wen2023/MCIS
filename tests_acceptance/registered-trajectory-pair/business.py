"""Direct production modules, real business tables/files, synthetic inputs only.
Run with an existing isolated (-I) Python containing SQLAlchemy/FastAPI/jsonschema.
No app, HTTP server/client, registry, seed, media, model or identity provider.
"""
import asyncio
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parents[2]
REF='ca8bb781545228a3333167b6188fcde1c53c2509'
MODULES='''__init__ config db common/__init__ common/contracts common/context common/timeutil common/csjson
cases/__init__ cases/models cases/service audit/__init__ audit/models audit/service
evidence/__init__ evidence/models evidence/service evidence_intake/__init__ evidence_intake/parser evidence_intake/router
redaction/__init__ redaction/models redaction/policy redaction/gateway reports/__init__ reports/models reports/access
interviews/__init__ interviews/models interviews/access manual_interviews/__init__ manual_interviews/models
working_records_archive/__init__ working_records_archive/models working_records_archive/validation working_records_archive/service
track_history/__init__ track_history/models track_history/service report_output/__init__ report_output/attachment_access
trajectory_exchange/__init__ trajectory_exchange/validation trajectory_exchange/registered_pair'''.split()
PATHS=tuple('service/mcis_service/'+p+'.py' for p in MODULES)+tuple(
    'contracts/schemas/'+n+'.schema.json' for n in ('case','common','evidence-item','shared-trajectory-v1'))+tuple(
    'tests_acceptance/shared-trajectory-cross-repo-expanded/'+n for n in ('vessel-a.json','vessel-b.json'))


def materialize(destination):
    for path in PATHS:
        entry=subprocess.check_output(['git','ls-tree',REF,'--',path],cwd=ROOT,text=True).split()
        if len(entry)!=4 or entry[0]!='100644' or entry[1]!='blob' or entry[3]!=path:
            raise RuntimeError('Expected fixed ordinary source file')
        raw=subprocess.check_output(['git','show',REF+':'+path],cwd=ROOT)
        current=subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT)
        if raw!=current: raise RuntimeError('Source changed; review and explicitly refreeze test')
        target=destination/path
        target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as f: f.write(raw)
    return destination


class Body:
    """Only request transport is a stub, consumed by production body_bounded."""
    headers={'content-type':'application/json'}
    def __init__(self,value): self.raw=json.dumps(value).encode()
    async def stream(self): yield self.raw


def run(source):
    sys.path.insert(0,str(source/'service'))
    from fastapi import HTTPException
    from sqlalchemy import select, text
    from mcis_service.db import Database, Base, put_doc, APPEND_ONLY_TABLES
    from mcis_service.common.context import Ctx
    from mcis_service.common import contracts
    from mcis_service.cases.models import CaseRow
    from mcis_service.evidence.models import EvidenceRow,CustodyEventRow
    from mcis_service.audit.models import AuditEventRow
    from mcis_service.audit.service import verify_chain,all_lines
    from mcis_service.redaction.models import AccessPolicyRow
    from mcis_service.redaction.policy import default_policy
    from mcis_service.working_records_archive.models import ArchiveImportHistoryRow
    from mcis_service.track_history.models import LocalReceipt
    from mcis_service.evidence_intake import router as intake
    from mcis_service.trajectory_exchange.registered_pair import _load_registered_pair,RegisteredPairError

    class Business(unittest.TestCase):
        def setUp(self):
            self.tmp=tempfile.TemporaryDirectory(prefix='business-',dir=source)
            self.addCleanup(self.tmp.cleanup)
            self.root=Path(self.tmp.name); blobs=self.root/'blobs';blobs.mkdir()
            self.db=Database('sqlite:///'+str(self.root/'fresh.sqlite'))
            self.addCleanup(self.db.engine.dispose)
            tables=[m.__table__ for m in (CaseRow,EvidenceRow,CustodyEventRow,AuditEventRow,AccessPolicyRow,ArchiveImportHistoryRow,LocalReceipt)]
            Base.metadata.create_all(self.db.engine,tables=tables)
            # Same four SQL statements as Database.create_all; never call that
            # method because it imports the full model registry.
            with self.db.engine.begin() as c:
                for t in APPEND_ONLY_TABLES:
                    for op in ('UPDATE','DELETE'):
                        c.execute(text(f"CREATE TRIGGER IF NOT EXISTS {t}_no_{op.lower()} BEFORE {op} ON {t} "
                                       f"BEGIN SELECT RAISE(ABORT, '{t} is append-only'); END;"))
                triggers=set(c.execute(text("SELECT name FROM sqlite_master WHERE type='trigger'")).scalars())
                self.assertTrue({'audit_events_no_update','audit_events_no_delete','custody_events_no_update','custody_events_no_delete'}<=triggers)
            state=SimpleNamespace(db=self.db,settings=SimpleNamespace(blob_dir=blobs))
            # Explicit trusted-context fixture, NOT a login or authentication test.
            self.ctx=Ctx(role='Investigator',operator='Synthetic test operator',request=SimpleNamespace(app=SimpleNamespace(state=state)))
            self.docs=[json.loads((source/'tests_acceptance/shared-trajectory-cross-repo-expanded'/name).read_text()) for name in ('vessel-a.json','vessel-b.json')]
            self.cid=self.docs[0]['caseId']
            case={'caseId':self.cid,'schemaVersion':'1.0.0','title':'Synthetic pair test','accidentType':'Synthetic','isFictionalDemo':True,
                  'caseEpochUtc':'2026-02-01T12:00:00Z','incidentTimeUtc':'2026-02-01T12:00:00Z',
                  'incidentLocation':{'lonDeg':-130,'latDeg':-30},'displayTimeZoneOffsetMinutes':0}
            contracts.validate('case',case)
            with self.db.session() as s:
                put_doc(s,CaseRow,self.cid,self.cid,case)
                put_doc(s,AccessPolicyRow,self.cid,'policy',default_policy())
            self.pins=[self.register(doc) for doc in self.docs]

        def register(self,doc):
            raw=json.dumps(doc,separators=(',',':')).encode()
            body={'profile':'mcis-evidence-intake-v1','fileName':'synthetic.json','title':'Synthetic V1',
                  'source':'Handmade fixture, not authenticated evidence','extractedBy':'Synthetic author',
                  'extractedUtc':'2026-02-01T00:00:00Z','category':'Other','confidentiality':'Restricted','note':'synthetic',
                  'contentBase64':base64.b64encode(raw).decode()}
            preview=asyncio.run(intake.preview_input(self.cid,Body(body),self.ctx))
            receipt=asyncio.run(intake.commit_input(self.cid,Body({**body,'requestDigest':preview['requestDigest'],'confirmed':True}),self.ctx))
            self.assertEqual(receipt['sourceSha256'],hashlib.sha256(raw).hexdigest())
            path=intake.file_path(self.ctx,self.cid,intake.rel_for(receipt['requestDigest']))
            self.assertEqual(path.read_bytes(),raw)
            return {k:receipt[k] for k in ('caseId','evidenceId','requestDigest','sourceSha256')}

        def counts(self):
            with self.db.session() as s:
                return (s.query(EvidenceRow).count(),s.query(CustodyEventRow).count(),s.query(AuditEventRow).count())

        def read(self,pins=None):
            return _load_registered_pair(self.ctx,self.cid,self.pins if pins is None else pins,'Synthetic pair review')

        def test_success_real_files_receipts_audit(self):
            self.assertEqual(self.counts(),(2,2,2))
            result=self.read()
            self.assertEqual([r['document'] for r in result],self.docs)
            self.assertEqual(self.counts(),(2,4,4))
            with self.db.session() as s:
                accesses=s.scalars(select(CustodyEventRow).where(CustodyEventRow.kind=='Access').order_by(CustodyEventRow.seq)).all()
                self.assertEqual([r.evidence_id for r in accesses],[p['evidenceId'] for p in self.pins])
                self.assertEqual([r.sha256 for r in accesses],[p['sourceSha256'] for p in self.pins])
                self.assertTrue(verify_chain(all_lines(s,self.cid))['valid'])
                custody=s.scalars(select(CustodyEventRow).where(CustodyEventRow.case_id==self.cid).order_by(CustodyEventRow.seq)).all()
                self.assertTrue(verify_chain([r.line for r in custody])['valid'])
                found=[intake.load_receipt(self.ctx,s,self.cid,p['requestDigest'])[0] for p in self.pins]
                self.assertEqual([r['evidence']['accessCount'] for r in found],[1,1])

        def test_policy_denied_no_delivery_no_access(self):
            policy=default_policy();policy['matrix']['Investigator']['evidence_meta']='Deny'
            with self.db.session() as s: put_doc(s,AccessPolicyRow,self.cid,'policy',policy)
            before=self.counts()
            with self.assertRaises(HTTPException) as error:self.read()
            self.assertEqual(error.exception.status_code,403)
            self.assertEqual(self.counts(),before)

        def test_second_registered_wrong_case_rolls_back_real_access(self):
            doc=json.loads(json.dumps(self.docs[1]));doc['caseId']='SYN-OTHER'
            bad=self.register(doc)  # Real opaque-file registration, valid V1 but wrong document case.
            before=self.counts()
            with self.assertRaisesRegex(RegisteredPairError,'DOCUMENT_CASE_MISMATCH'):
                self.read([self.pins[0],bad])
            self.assertEqual(self.counts(),before)
            with self.db.session() as s:
                self.assertEqual(s.query(CustodyEventRow).filter_by(kind='Access').count(),0)
                self.assertEqual(s.query(AuditEventRow).filter_by(action='custody.access').count(),0)
                self.assertTrue(verify_chain(all_lines(s,self.cid))['valid'])
                custody=s.scalars(select(CustodyEventRow).where(CustodyEventRow.case_id==self.cid).order_by(CustodyEventRow.seq)).all()
                self.assertTrue(verify_chain([r.line for r in custody])['valid'])

    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Business)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    for name,module in tuple(sys.modules.items()):
        if name=='mcis_service' or name.startswith('mcis_service.'):
            path=Path(module.__file__).resolve()
            if not path.is_relative_to(source/'service/mcis_service') or str(path.relative_to(source)) not in PATHS:
                raise RuntimeError('Unexpected production module origin')
    if 'mcis_service.main' in sys.modules or 'mcis_service.models_registry' in sys.modules:
        raise RuntimeError('Forbidden application import')
    return result.wasSuccessful()

if __name__=='__main__':
    if not sys.flags.isolated: raise SystemExit('Use existing Python -I; no install or application startup')
    with tempfile.TemporaryDirectory(prefix='mcis-pair-source-') as folder:
        ok=run(materialize(Path(folder)))
    raise SystemExit(0 if ok else 1)
