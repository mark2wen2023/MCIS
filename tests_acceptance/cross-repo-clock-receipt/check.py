"""Synthetic MCIS-side reconciliation only; not a V1 extension or runtime API."""
import argparse
import asyncio
import base64
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
FIXTURE='2048c60fd6650c6f2c99a76a16be463a3895655d'
HARNESS='c7f933d9d5a3fea6c4f3d706fe1f091475c3eb24'
FOLDER='tests_acceptance/shared-trajectory-cross-repo-expanded/'
HASHES={'vessel-a.json':'a8f9109a33b8c80a6c41219473186e69c16fd59ee64ff325a5559c190028bb1c','vessel-b.json':'07e043fc227770b6aaa6f1b15a6118e46b85a52e5638ac1b514e9269c6b159ca','vessel-mismatch.json':'f785399311f5dd045eec6cc8a6a2105d95b376e9aa894342fd4da4f5985dc2f4'}

def git(ref,path):
    return subprocess.check_output(['git','show',ref+':'+path],cwd=ROOT)

# Existing harness and production allowlist remain fixed, not copied or broadened.
for name in ('business.py','business_query.py'):
    path='tests_acceptance/registered-trajectory-pair/'+name
    if (ROOT/path).read_bytes()!=git(HARNESS,path):raise RuntimeError('Harness bytes differ')
query=runpy.run_path(str(ROOT/'tests_acceptance/registered-trajectory-pair/business_query.py'))
base=query['base'];result=None
RAW={name:git(FIXTURE,FOLDER+name) for name in HASHES}
for name,raw in RAW.items():
    if hashlib.sha256(raw).hexdigest()!=HASHES[name]:raise RuntimeError('Fixture bytes differ')

class Reconciliation:
    def register_raw(self,raw):
        from mcis_service.evidence_intake import router as intake
        body={'profile':'mcis-evidence-intake-v1','fileName':'synthetic.json','title':'Synthetic V1',
              'source':'Handmade fixture, not authenticated evidence','extractedBy':'Synthetic author',
              'extractedUtc':'2026-02-01T00:00:00Z','category':'Other','confidentiality':'Restricted','note':'synthetic',
              'contentBase64':base64.b64encode(raw).decode()}
        preview=asyncio.run(intake.preview_input(self.cid,base['Body'](body),self.ctx))
        receipt=asyncio.run(intake.commit_input(self.cid,base['Body']({**body,'requestDigest':preview['requestDigest'],'confirmed':True}),self.ctx))
        self.assertEqual(receipt['sourceSha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(intake.file_path(self.ctx,self.cid,intake.rel_for(receipt['requestDigest'])).read_bytes(),raw)
        return {k:receipt[k] for k in ('caseId','evidenceId','requestDigest','sourceSha256')}

    def register(self,doc):
        name={'SYN-VESSEL-A':'vessel-a.json','SYN-VESSEL-B':'vessel-b.json'}[doc['vessel']['vesselId']]
        self.assertEqual(json.loads(RAW[name]),doc)
        return self.register_raw(RAW[name])

    def test_four_fixed_frames_and_mixed_case(self):
        global result
        from mcis_service.trajectory_exchange.registered_query import _query_registered_pair
        from mcis_service.trajectory_exchange.registered_pair import RegisteredPairError
        from mcis_service.evidence.models import CustodyEventRow
        from mcis_service.audit.service import verify_chain,all_lines
        from sqlalchemy import select
        frames=[]
        samples=[('12:01:40.000',[7,12]),('12:02:01.000',[10,None]),('12:02:04.250',[None,None]),('12:02:07.500',[11,None])]
        self.assertEqual(self.counts(),(2,2,2))
        for n,(clock,indices) in enumerate(samples,1):
            utc='2026-02-01T'+clock+'Z';before=self.counts()
            frame=_query_registered_pair(self.ctx,self.cid,self.pins,'Synthetic cross-repo clock review',utc)
            self.assertEqual(self.counts(),(2,2+2*n,2+2*n))
            vessels=[]
            for side,(v,index) in enumerate(zip(frame['vessels'],indices)):
                self.assertEqual(v['original'],self.pins[side]);self.assertFalse(v['courseUsedAsHeading'])
                if index is not None:
                    p=self.docs[side]['points'][index]
                    self.assertEqual(v['status'],'input_point');self.assertEqual(v['locator'],{'jsonPointer':f'/points/{index}'})
                    self.assertEqual(v['time'],{k:p['time'][k] for k in ('sourceUtc','alignedUtc','correctionSeconds','status')})
                    self.assertEqual(v['position']['kind'],'recorded')
                    self.assertEqual(v['headingDeg'],{k:p['headingDeg'][k] for k in ('value','kind')})
                elif side==0:
                    self.assertEqual(v['status'],'declared_gap');self.assertEqual(v['locator'],{'jsonPointer':'/sampling/missingIntervals/1'})
                else:
                    self.assertEqual(v['status'],'no_observation_at_time');self.assertIsNone(v['locator'])
                if index is None:
                    for key in ('time','position','headingDeg','courseDeg'):self.assertIsNone(v[key])
                # Allowlist only: no internal pin, evidence id, receipt digest or raw row.
                vessels.append({'vesselId':v['vesselId'],'status':v['status'],
                    'jsonPointer':v['locator']['jsonPointer'] if v['locator'] else None,
                    'fileSha256':v['original']['sourceSha256'],'time':v['time'],
                    'positionKind':v['position']['kind'] if v['position'] else None,
                    'headingKind':v['headingDeg']['kind'] if v['headingDeg'] else None,
                    'headingMissing':v['headingDeg']['value'] is None if v['headingDeg'] else None})
            frames.append({'utc':utc,'vessels':vessels,'accessAdded':self.counts()[1]-before[1],'accessTotal':2*n})
        self.assertEqual(frames[0]['vessels'][0]['time']['correctionSeconds'],0)
        self.assertTrue(frames[0]['vessels'][0]['headingMissing'])
        self.assertEqual(frames[0]['vessels'][1]['time']['correctionSeconds'],12)
        self.assertFalse(frames[0]['vessels'][1]['headingMissing'])
        different=json.loads(RAW['vessel-mismatch.json']);same=json.loads(RAW['vessel-b.json'])
        self.assertNotEqual(different['caseId'],self.cid);same['caseId']=different['caseId'];self.assertEqual(different,same)
        mismatch=self.register_raw(RAW['vessel-mismatch.json']);before=self.counts();delivered=None
        with self.assertRaisesRegex(RegisteredPairError,'DOCUMENT_CASE_MISMATCH'):
            delivered=_query_registered_pair(self.ctx,self.cid,[self.pins[0],mismatch],'Synthetic mixed-case review',frames[0]['utc'])
        self.assertIsNone(delivered);self.assertEqual(self.counts(),before)
        with self.db.session() as s:
            rows=s.scalars(select(CustodyEventRow).where(CustodyEventRow.case_id==self.cid).order_by(CustodyEventRow.seq)).all()
            accesses=[r for r in rows if r.kind=='Access']
            self.assertEqual([(r.evidence_id,r.sha256) for r in accesses],[(p['evidenceId'],p['sourceSha256']) for p in self.pins]*4)
            self.assertTrue(verify_chain([r.line for r in rows])['valid']);self.assertTrue(verify_chain(all_lines(s,self.cid))['valid'])
        result={'kind':'synthetic-offline-comparison-only','caseId':self.cid,'fixtureCommit':FIXTURE,
                'productCommit':query['PRODUCT'],'harnessCommit':HARNESS,'files':HASHES,'frames':frames,
                'mixedCase':{'result':'rejected','accessAdded':0},'accessTotal':8,
                'limitations':['No HTTP, real login, browser, model or 3D execution','Clock corrections are synthetic declarations, not signed review or event ordering','Recorded is fixture quality, not real observation','Not a runtime interface, permission or V1 contract extension']}

if __name__=='__main__':
    if not sys.flags.isolated:raise SystemExit('Use existing Python -I -B')
    parser=argparse.ArgumentParser();parser.add_argument('--receipt',type=Path,required=True);args=parser.parse_args()
    if args.receipt.exists():raise SystemExit('Receipt output must be new')
    with tempfile.TemporaryDirectory(prefix='mcis-clock-receipt-') as folder:
        source=base['materialize'](Path(folder),ref=query['PRODUCT'],paths=query['PATHS'])
        hashes={p:hashlib.sha256((source/p).read_bytes()).hexdigest() for p in query['PATHS'] if p.startswith('service/')}
        ok=base['run'](source,extra_cases=(Reconciliation,),allowed_paths=query['PATHS'])
    if not ok or result is None:raise SystemExit(1)
    result['productFileSha256']=hashes
    def check_keys(value):
        if isinstance(value,dict):
            if set(value)&{'requestDigest','evidenceId','operator','token','policy','original'}:raise RuntimeError('Internal field in receipt')
            for child in value.values():check_keys(child)
        elif isinstance(value,list):
            for child in value:check_keys(child)
    check_keys(result)
    with args.receipt.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print('Receipt complete: four fixed raw-byte frames, 8 Access; mixed case +0 Access; no runtime integration')
