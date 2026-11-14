import unittest
from copy import deepcopy
from dataclasses import replace
from test_preview import Repository, FakeCore
from preview import preview, Rejected

class BindingTests(unittest.TestCase):
    def setUp(self):
        self.repo=Repository(); self.core=FakeCore()
        self.conflict={'caseId':'CASE-1','conflictId':'C-01','a':{'sourceLabel':'A'},'b':{'sourceLabel':'B'}}
        self.entries=[self.conflict]
        self.core.align=lambda p: {'ok':True,'command':'align','coreVersion':'FAKE','result':{'caseId':'CASE-1','conflicts':self.entries}}
    def run_preview(self):
        return preview({'caseId':'CASE-1','sourceIds':['A','B'],'caseEpochUtc':'2026-11-13T00:00:00Z'},principal='fixture-investigator',repository=self.repo,core=self.core)
    def test_exact_binding(self):
        out=self.run_preview(); c=out['candidates'][0]
        self.assertEqual(c['a']['revision'],'r1');self.assertEqual(c['b']['sourceId'],'B')
        self.assertEqual(c['status'],'needs_human_review')
    def test_unknown_source(self):
        self.conflict['a']['sourceLabel']='C'
        with self.assertRaises(Rejected):self.run_preview()
    def test_no_alias_matching(self):
        for value in ['a',' A','A ','AIS-A',None,{},['A']]:
            self.conflict['a']['sourceLabel']=value
            with self.subTest(value=value), self.assertRaises(Rejected):self.run_preview()
    def test_no_same_source(self):
        self.conflict['b']['sourceLabel']='A'
        with self.assertRaises(Rejected):self.run_preview()
    def test_missing_side(self):
        del self.conflict['b']
        with self.assertRaises(Rejected):self.run_preview()
    def test_duplicate_conflict(self):
        self.entries.append(deepcopy(self.conflict))
        with self.assertRaises(Rejected):self.run_preview()
    def test_bad_conflict_id(self):
        for cid in [None, {}, 'C-1', 'C-01\n', 'C-'+'1'*33]:
            self.conflict['conflictId']=cid
            with self.subTest(cid=cid), self.assertRaises(Rejected):self.run_preview()
    def test_evidence_id_not_authority(self):
        self.conflict['a']['evidenceId']='A'
        with self.assertRaises(Rejected):self.run_preview()
    def test_unknown_text_not_forwarded(self):
        self.conflict['summary']='INJECT'; self.conflict['a']['valueText']='INJECT'
        self.assertNotIn('INJECT',str(self.run_preview()))
    def test_source_metadata_types(self):
        for field in ['revision','locator']:
            original=self.repo.records['A']
            self.repo.records['A']=replace(original,**{field:{'bad':'object'}})
            with self.subTest(field=field),self.assertRaises(Rejected):self.run_preview()
            self.repo.records['A']=original
    def test_recheck_after_binding(self):
        self.repo.current=False
        with self.assertRaises(Rejected):self.run_preview()
    def test_mutating_output_does_not_change_repository(self):
        out=self.run_preview();out['candidates'][0]['a']['revision']='changed'
        self.assertEqual(self.repo.records['A'].revision,'r1')
    def test_input_unchanged(self):
        before=deepcopy(self.entries); self.run_preview();self.assertEqual(before,self.entries)

if __name__=='__main__':unittest.main()
