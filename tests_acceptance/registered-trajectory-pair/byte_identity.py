"""Equivalent JSON, separately registered original bytes, fixed T+100 references.
No original tampering, report grant, report save or application startup.
"""
import asyncio
import base64
import hashlib
import json
from pathlib import Path
import runpy
import sys
import tempfile

base=runpy.run_path(str(Path(__file__).with_name('business.py')))
PRODUCT='db90fdf73de7bd26ba75819f0102fc03d0789faf'
PATHS=base['PATHS']+('service/mcis_service/trajectory_exchange/registered_query.py',)

class ByteIdentity:
    def test_equivalent_json_keeps_distinct_original_pin_after_reopen(self):
        from mcis_service.db import Database
        from mcis_service.evidence_intake import router as intake
        from mcis_service.trajectory_exchange.registered_query import _query_registered_pair
        from mcis_service.trajectory_exchange.registered_pair import _load_registered_pair
        from mcis_service.audit.service import verify_chain,all_lines
        from mcis_service.evidence.models import CustodyEventRow
        from sqlalchemy import select
        utc='2026-02-01T12:01:40.000Z'
        old_raw=json.dumps(self.docs[0],separators=(',',':')).encode()
        new_raw=(json.dumps(self.docs[0],indent=2,sort_keys=True)+'\n').encode()
        self.assertNotEqual(new_raw,old_raw)
        self.assertEqual(json.loads(new_raw),json.loads(old_raw))
        # Exactly the existing fixture metadata, only original byte representation changes.
        body={'profile':'mcis-evidence-intake-v1','fileName':'synthetic.json','title':'Synthetic V1',
              'source':'Handmade fixture, not authenticated evidence','extractedBy':'Synthetic author',
              'extractedUtc':'2026-02-01T00:00:00Z','category':'Other','confidentiality':'Restricted','note':'synthetic',
              'contentBase64':base64.b64encode(new_raw).decode()}
        preview=asyncio.run(intake.preview_input(self.cid,base['Body'](body),self.ctx))
        receipt=asyncio.run(intake.commit_input(self.cid,base['Body']({**body,'requestDigest':preview['requestDigest'],'confirmed':True}),self.ctx))
        new_pin={k:receipt[k] for k in ('caseId','evidenceId','requestDigest','sourceSha256')}
        old_pin=self.pins[0]
        for field in ('evidenceId','requestDigest','sourceSha256'):self.assertNotEqual(new_pin[field],old_pin[field])
        self.assertEqual(old_pin['sourceSha256'],hashlib.sha256(old_raw).hexdigest())
        self.assertEqual(new_pin['sourceSha256'],hashlib.sha256(new_raw).hexdigest())
        canonical=lambda raw:json.dumps(json.loads(raw),sort_keys=True,separators=(',',':')).encode()
        self.assertEqual(hashlib.sha256(canonical(old_raw)).hexdigest(),hashlib.sha256(canonical(new_raw)).hexdigest())
        self.assertEqual(self.counts(),(3,3,3))
        def query(pin):return _query_registered_pair(self.ctx,self.cid,[pin,self.pins[1]],'Synthetic byte identity check',utc)
        old=query(old_pin)['vessels'][0];new=query(new_pin)['vessels'][0]
        for item,pin in ((old,old_pin),(new,new_pin)):
            self.assertEqual(item['original'],pin)
            self.assertEqual(item['locator'],{'jsonPointer':'/points/7'})
            self.assertEqual(item['status'],'input_point')
            self.assertEqual(item['position']['kind'],'recorded') # synthetic source quality only
            self.assertEqual(item['time']['alignedUtc'],utc)
            self.assertIsNone(item['headingDeg']['value'])
            self.assertFalse(item['courseUsedAsHeading'])
        self.assertEqual({k:v for k,v in old.items() if k!='original'}, {k:v for k,v in new.items() if k!='original'})
        self.db.engine.dispose()
        self.db=Database('sqlite:///'+str(self.root/'fresh.sqlite'));self.addCleanup(self.db.engine.dispose)
        self.ctx.request.app.state.db=self.db
        self.assertEqual(query(old_pin)['vessels'][0],old)
        self.assertEqual(query(new_pin)['vessels'][0],new)
        for pin,expected_raw in ((old_pin,old_raw),(new_pin,new_raw)):
            batch=_load_registered_pair(self.ctx,self.cid,[pin,self.pins[1]],'Synthetic fixed point provenance')
            point=batch[0]['document']['points'][7]
            self.assertEqual(point['pointId'],'A-t100')
            self.assertEqual(point['time']['alignedUtc'],utc)
            self.assertEqual(point['position']['value'],old['position']['value'])
            # Read back via receipt integrity path, not an arbitrary raw file open.
            with self.db.session() as session:
                fixed,raw=intake.load_receipt(self.ctx,session,self.cid,pin['requestDigest'])
                self.assertEqual(raw,expected_raw)
                self.assertEqual(fixed['sourceSha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(self.counts(),(3,15,15)) # 3 Register, six pair reads = 12 Access
        with self.db.session() as session:
            self.assertTrue(verify_chain(all_lines(session,self.cid))['valid'])
            rows=session.scalars(select(CustodyEventRow).where(CustodyEventRow.case_id==self.cid).order_by(CustodyEventRow.seq)).all()
            self.assertTrue(verify_chain([r.line for r in rows])['valid'])
            accesses=[r for r in rows if r.kind=='Access']
            expected=[p for a in (old_pin,new_pin,old_pin,new_pin,old_pin,new_pin) for p in (a,self.pins[1])]
            self.assertEqual([(r.evidence_id,r.sha256) for r in accesses],[(p['evidenceId'],p['sourceSha256']) for p in expected])
        # Future sentence input, held only here; NOT a report pin, fact or saved binding.
        proposal={'text':'A 船在此 UTC 有一条已登记的位置记录','original':old['original'],
                  'alignedUtc':utc,'locator':old['locator'],'positionKind':old['position']['kind']}
        self.assertEqual(proposal['original'],old_pin)
        self.assertNotEqual(proposal['original'],new_pin)

if __name__=='__main__':
    if not sys.flags.isolated:raise SystemExit('Use existing Python -I')
    with tempfile.TemporaryDirectory(prefix='mcis-byte-identity-') as folder:
        source=base['materialize'](Path(folder),ref=PRODUCT,paths=PATHS)
        ok=base['run'](source,extra_cases=(ByteIdentity,),allowed_paths=PATHS)
    raise SystemExit(0 if ok else 1)
