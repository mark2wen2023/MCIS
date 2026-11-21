"""Pure synthetic parity/shape tests; no application imports or source reads."""
import ast
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import runpy
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[2]
OLD='f9f4e599cdb670d864a5e7e986067216e7105636'


def functions(source,names,ns):
    nodes=[]
    for n in ast.parse(source).body:
        if isinstance(n,ast.FunctionDef) and n.name in names:
            n.body=[s for s in n.body if not isinstance(s,ast.ImportFrom)]
            nodes.append(n)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<production-ast>','exec'),ns)


class Query(unittest.TestCase):
    def setUp(self):
        self.docs=[json.loads((ROOT/'tests_acceptance/shared-trajectory-cross-repo-expanded'/n).read_text()) for n in ('vessel-a.json','vessel-b.json')]
        validator=runpy.run_path(str(ROOT/'service/mcis_service/trajectory_exchange/validation.py'))
        self.ns={'deepcopy':deepcopy,'re':re,'_stamp':validator['_stamp']}
        functions((ROOT/'service/mcis_service/trajectory_exchange/registered_query.py').read_text(),
                  {'_query_registered_pair','_point_from_committed_original'},self.ns)
        self.batch=[{'document':d,'pin':{'caseId':d['caseId'],'evidenceId':'SYN-'+str(i),
                    'requestDigest':str(i+1)*64,'sourceSha256':str(i+3)*64}} for i,d in enumerate(self.docs)]
        self.old={'deepcopy':deepcopy,'stamp':lambda s:datetime.fromisoformat(s.replace('Z','+00:00')),
                  'reference':lambda *a:None}
        functions(subprocess.check_output(['git','show',OLD+':tools/replay_evidence_clock/query.py'],cwd=ROOT,text=True),{'point_at'},self.old)

    def test_exact_selector_parity_and_boundaries(self):
        times=[0,20,60,80,100,121,124.25,127.5,220]
        for second in times:
            instant=datetime(2026,2,1,12)+timedelta(seconds=second)
            for item in self.batch:
                new=self.ns['_point_from_committed_original'](item,instant)
                old=self.old['point_at'](item,instant.replace(tzinfo=timezone.utc))
                self.assertEqual(new['status'],old['status'])
                self.assertEqual(new['position'],None if old['position'] is None else {k:old['position'][k] for k in ('value','kind')})
                self.assertFalse(new['courseUsedAsHeading'])
                if new['status']=='input_point':
                    index=int(new['locator']['jsonPointer'].split('/')[-1])
                    self.assertEqual(item['document']['points'][index]['time']['alignedUtc'],new['time']['alignedUtc'])
        self.assertEqual(self.ns['_point_from_committed_original'](self.batch[1],datetime(2026,2,1,12,0,20))['position']['kind'],'interpolated')

    def test_each_query_rereads_and_no_prose_or_git_output(self):
        calls=[]
        def load(*args): calls.append(args); return self.batch
        self.ns['_load_registered_pair']=load
        query=self.ns['_query_registered_pair'];cid=self.docs[0]['caseId']
        first=query(object(),cid,(), 'synthetic', '2026-02-01T12:00:20.000Z')
        second=query(object(),cid,(), 'synthetic', '2026-02-01T12:02:04.250Z')
        self.assertEqual(len(calls),2)
        self.assertEqual([v['status'] for v in second['vessels']],['declared_gap','no_observation_at_time'])
        self.assertTrue(all(v['position'] is None for v in second['vessels']))
        self.assertEqual(first['vessels'][1]['time']['correctionSeconds'],12)
        raw=json.dumps(first)
        for forbidden in ('rawRecord','gitRef','sources','sourceIds','basis','path'):
            self.assertNotIn('"'+forbidden+'"',raw)
        first['vessels'][0]['original']['evidenceId']='changed-result'
        self.assertEqual(self.batch[0]['pin']['evidenceId'],'SYN-0')

    def test_invalid_clock_no_read_and_failed_service_no_result(self):
        def fail(*args): raise RuntimeError('service did not commit')
        self.ns['_load_registered_pair']=fail
        for bad in ('2026-02-01', '2026-02-01T12:00:00+00:00','2026-02-01T12:00:00.0001Z'):
            with self.assertRaisesRegex(ValueError,'EXACT_UTC_REQUIRED'):
                self.ns['_query_registered_pair'](None,'SYN',(), 'synthetic',bad)
        with self.assertRaisesRegex(RuntimeError,'did not commit'):
            self.ns['_query_registered_pair'](None,'SYN',(), 'synthetic','2026-02-01T12:00:00Z')

if __name__=='__main__':unittest.main(verbosity=2)
