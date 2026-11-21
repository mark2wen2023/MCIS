"""Register exact fixed synthetic Git bytes; no changes to prior compact fixtures."""
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
pilot=runpy.run_path(str(Path(__file__).with_name('pilot_prepare.py')))
REF='2048c60fd6650c6f2c99a76a16be463a3895655d'

class Raw(pilot['Pilot']):
    def register(self,doc):
        from mcis_service.evidence_intake import router as intake
        side={'SYN-VESSEL-A':'a','SYN-VESSEL-B':'b'}[doc['vessel']['vesselId']]
        path='tests_acceptance/shared-trajectory-cross-repo-expanded/vessel-'+side+'.json'
        raw=subprocess.check_output(['git','show',REF+':'+path],cwd=ROOT)
        self.assertEqual(json.loads(raw),doc)
        compact=json.dumps(doc,separators=(',',':')).encode()
        self.assertNotEqual(hashlib.sha256(raw).hexdigest(),hashlib.sha256(compact).hexdigest())
        body={'profile':'mcis-evidence-intake-v1','fileName':'synthetic.json','title':'Synthetic V1',
              'source':'Handmade fixture, not authenticated evidence','extractedBy':'Synthetic author',
              'extractedUtc':'2026-02-01T00:00:00Z','category':'Other','confidentiality':'Restricted','note':'synthetic',
              'contentBase64':base64.b64encode(raw).decode()}
        preview=asyncio.run(intake.preview_input(self.cid,pilot['base']['Body'](body),self.ctx))
        receipt=asyncio.run(intake.commit_input(self.cid,pilot['base']['Body']({**body,'requestDigest':preview['requestDigest'],'confirmed':True}),self.ctx))
        self.assertEqual(receipt['sourceSha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(intake.file_path(self.ctx,self.cid,intake.rel_for(receipt['requestDigest'])).read_bytes(),raw)
        return {k:receipt[k] for k in ('caseId','evidenceId','requestDigest','sourceSha256')}

    def test_raw_fixed_files_prepare(self):
        # Inherits actual session/policy/RA/Access checks, not a substituted grant.
        super().test_scoped_prepare_and_denials()

if __name__=='__main__':
    if not sys.flags.isolated:raise SystemExit('Use Python -I')
    with tempfile.TemporaryDirectory(prefix='raw-fixture-') as folder:
        source=pilot['base']['materialize'](Path(folder),ref=pilot['REF'],paths=pilot['BASE'])
        for path in pilot['NEW']:
            target=source/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/path).read_bytes())
        ok=pilot['base']['run'](source,extra_cases=(Raw,),allowed_paths=pilot['BASE']+pilot['NEW'])
    raise SystemExit(0 if ok else 1)
