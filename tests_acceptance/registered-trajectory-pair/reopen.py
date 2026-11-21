"""Real registration -> exact point -> fresh Database -> same fixed original.
Only reviewed source allowlist and handmade V1 files. No report binding, HTTP,
login provider, app, model registry, or business data. A reference held by this
test is not a persisted report or a grant; every reread uses production checks.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import runpy
import sys
import tempfile

base=runpy.run_path(str(Path(__file__).with_name('business.py')))
PRODUCT='db90fdf73de7bd26ba75819f0102fc03d0789faf'
PATHS=base['PATHS']+('service/mcis_service/trajectory_exchange/registered_query.py',)

class Reopen:
    def test_new_engine_fixed_point_survives_another_original(self):
        from sqlalchemy import select
        from mcis_service.db import Database
        from mcis_service.audit.models import AuditEventRow
        from mcis_service.audit.service import verify_chain,all_lines
        from mcis_service.evidence.models import CustodyEventRow
        from mcis_service.trajectory_exchange.registered_query import _query_registered_pair
        from mcis_service.trajectory_exchange.registered_pair import _load_registered_pair
        utc='2026-02-01T12:01:40.000Z'
        def query(pins):
            return _query_registered_pair(self.ctx,self.cid,pins,'Synthetic reopen check',utc)
        first=query(self.pins)
        self.assertEqual(self.counts(),(2,4,4))
        self.assertEqual(first['vessels'][0]['status'],'input_point')
        self.assertEqual(first['vessels'][0]['position']['kind'],'recorded')
        self.assertEqual(first['vessels'][0]['locator'],{'jsonPointer':'/points/7'})
        self.assertIsNone(first['vessels'][0]['headingDeg']['value'])
        # Held by the test, NOT a report document, new binding table or credential.
        held=json.loads(json.dumps({'caseId':self.cid,'alignedUtc':utc,'pins':self.pins,
                                   'point':first['vessels'][0]}))
        newer=deepcopy(self.docs[0]);newer['points'][7]['position']['value']['latDeg']+=0.0001
        newer_pin=self.register(newer) # original preview/commit; no direct evidence row insertion
        self.assertNotEqual(newer_pin['sourceSha256'],held['pins'][0]['sourceSha256'])
        self.assertNotEqual(newer_pin['requestDigest'],held['pins'][0]['requestDigest'])
        self.assertEqual(self.counts(),(3,5,5))
        old_db=self.db
        old_db.engine.dispose()
        self.db=Database('sqlite:///'+str(self.root/'fresh.sqlite'))
        self.addCleanup(self.db.engine.dispose)
        self.ctx.request.app.state.db=self.db
        self.assertIsNot(self.db,old_db)
        self.assertEqual(self.counts(),(3,5,5)) # persistent rows, no reinitialization
        reopened=query(held['pins'])
        self.assertEqual(reopened,first)
        self.assertEqual(self.counts(),(3,7,7))
        changed=query([newer_pin,held['pins'][1]])
        self.assertNotEqual(changed['vessels'][0]['position'],held['point']['position'])
        self.assertEqual(changed['vessels'][0]['original'],newer_pin)
        # New pin is independently addressable, not an in-place revision/latest pointer.
        originals=_load_registered_pair(self.ctx,self.cid,held['pins'],'Synthetic original pointer check')
        for i,item in enumerate(originals):
            self.assertEqual(item['pin'],held['pins'][i])
            self.assertEqual(item['document'],self.docs[i])
            raw=json.dumps(self.docs[i],separators=(',',':')).encode()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),held['pins'][i]['sourceSha256'])
            pointer=reopened['vessels'][i]['locator']['jsonPointer']
            point=item['document']['points'][int(pointer.split('/')[-1])]
            self.assertEqual(point['position']['value'],reopened['vessels'][i]['position']['value'])
            self.assertEqual(point['time']['alignedUtc'],held['alignedUtc'])
        self.assertEqual(self.counts(),(3,11,11))
        with self.db.session() as session:
            accesses=session.scalars(select(CustodyEventRow).where(CustodyEventRow.kind=='Access').order_by(CustodyEventRow.seq)).all()
            expected=held['pins']+held['pins']+[newer_pin,held['pins'][1]]+held['pins']
            self.assertEqual([x.evidence_id for x in accesses],[x['evidenceId'] for x in expected])
            self.assertEqual([x.sha256 for x in accesses],[x['sourceSha256'] for x in expected])
            self.assertEqual(session.query(AuditEventRow).filter_by(action='custody.access').count(),8)
            self.assertTrue(verify_chain(all_lines(session,self.cid))['valid'])
            chain=session.scalars(select(CustodyEventRow).where(CustodyEventRow.case_id==self.cid).order_by(CustodyEventRow.seq)).all()
            self.assertTrue(verify_chain([x.line for x in chain])['valid'])

if __name__=='__main__':
    if not sys.flags.isolated:raise SystemExit('Use existing Python -I')
    with tempfile.TemporaryDirectory(prefix='mcis-trajectory-reopen-') as folder:
        source=base['materialize'](Path(folder),ref=PRODUCT,paths=PATHS)
        ok=base['run'](source,extra_cases=(Reopen,),allowed_paths=PATHS)
    raise SystemExit(0 if ok else 1)
