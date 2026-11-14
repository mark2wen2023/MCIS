import unittest
from dataclasses import replace
from hashlib import sha256
from preview import Source, Rejected, preview

class Repository:
    """Synthetic trusted-host double; NOT production authentication."""
    def __init__(self):
        self.records = {x: Source('CASE-1', x, 'r1', sha256(b'fixture').hexdigest(), 'fixture:1', 'fixture') for x in ['A','B']}
        self.current = True
        self.denied = False
    def resolve(self, principal, case, source_id):
        if self.denied or principal != 'fixture-investigator':
            raise PermissionError('denied')
        return self.records[source_id]
    def recheck(self, principal, case, sources):
        return self.current

class FakeCore:
    """Synthetic protocol double; does NOT run W2 or an LLM."""
    def __init__(self): self.calls = []; self.change = lambda: None
    def align(self, payload):
        self.calls.append(payload)
        self.change()
        return {'ok': True, 'command': 'align', 'coreVersion':'FAKE-test-only',
                'result': {'caseId':'CASE-1', 'conflicts':[]}}

class Tests(unittest.TestCase):
    def setUp(self):
        self.repo=Repository(); self.core=FakeCore()
        self.request={'caseId':'CASE-1','sourceIds':['A','B'],'caseEpochUtc':'2026-11-13T00:00:00Z'}
    def run_preview(self):
        return preview(self.request, principal='fixture-investigator', repository=self.repo, core=self.core)
    def test_readonly_preview(self):
        r=self.run_preview()
        self.assertEqual(r['status'],'needs_human_review')
        self.assertEqual(r['sources'][0]['revision'],'r1')
        self.assertEqual(r['hypotheses'],[])
        self.assertFalse(self.core.calls[0]['calibrate'])
        self.assertNotIn('path',self.core.calls[0]['sources'][0])
    def test_permission_denied_before_core(self):
        self.repo.denied=True
        with self.assertRaises(PermissionError): self.run_preview()
        self.assertFalse(self.core.calls)
    def test_revoke_during_core(self):
        self.core.change=lambda: setattr(self.repo,'current',False)
        with self.assertRaises(Rejected): self.run_preview()
    def test_digest_tampering(self):
        self.repo.records['A']=replace(self.repo.records['A'],text='changed')
        with self.assertRaises(Rejected): self.run_preview()
        self.assertFalse(self.core.calls)
    def test_crosscase(self):
        self.repo.records['A']=replace(self.repo.records['A'],case_id='OTHER')
        with self.assertRaises(Rejected): self.run_preview()
    def test_unknown_fields(self):
        for key in ['principal','allowed','path','calibrate','revision']:
            with self.subTest(key=key):
                self.request[key]='forged'
                with self.assertRaises(Rejected): self.run_preview()
                del self.request[key]
    def test_epoch_reject(self):
        for t in ['2026-11-13T00:00:00','2026-02-30T00:00:00Z','2026-11-13T00:00:00.1234Z']:
            with self.subTest(t=t):
                self.request['caseEpochUtc']=t
                with self.assertRaises(Rejected): self.run_preview()
    def test_duplicate_source(self):
        self.request['sourceIds']=['A','A']
        with self.assertRaises(Rejected): self.run_preview()
    def test_single_source(self):
        self.request['sourceIds']=['A']
        with self.assertRaises(Rejected): self.run_preview()
    def test_empty_revision(self):
        self.repo.records['A']=replace(self.repo.records['A'],revision='')
        with self.assertRaises(Rejected): self.run_preview()
    def test_wrong_returned_source(self):
        self.repo.records['A']=replace(self.repo.records['A'],source_id='B')
        with self.assertRaises(Rejected): self.run_preview()
    def test_budget(self):
        t='x'*1000001
        self.repo.records['A']=replace(self.repo.records['A'],text=t,digest=sha256(t.encode()).hexdigest())
        with self.assertRaises(Rejected): self.run_preview()
    def test_core_wrong_case(self):
        self.core.align=lambda p:{'ok':True,'command':'align','result':{'caseId':'OTHER','conflicts':[]}}
        with self.assertRaises(Rejected): self.run_preview()
    def test_core_failure(self):
        self.core.align=lambda p:{'ok':False,'command':'align'}
        with self.assertRaises(Rejected): self.run_preview()
    def test_unsupported_format(self):
        self.repo.records['A']=replace(self.repo.records['A'],format='csv')
        with self.assertRaises(Rejected): self.run_preview()
    def test_bad_offset_minute(self):
        self.request['caseEpochUtc']='2026-11-13T00:00:00+00:99'
        with self.assertRaises(Rejected): self.run_preview()
    def test_core_object_version(self):
        self.core.align=lambda p:{'ok':True,'command':'align','coreVersion':{'secret':'bad'},'result':{'caseId':'CASE-1','conflicts':[]}}
        with self.assertRaises(Rejected): self.run_preview()
    def test_unbound_conflict(self):
        self.core.align=lambda p:{'ok':True,'command':'align','coreVersion':'FAKE','result':{'caseId':'CASE-1','conflicts':[None, {'caseId':'OTHER'}]}}
        with self.assertRaises(Rejected): self.run_preview()
    def test_zero_candidates_not_consistency(self):
        r=self.run_preview()
        self.assertIn('零候选不代表证据一致',r['warning'])
        self.assertIn('clock_correction',r['notChecked'])

if __name__=='__main__': unittest.main()
