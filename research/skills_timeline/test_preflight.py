"""Synthetic host-port tests, not production authorization or W2 execution."""
import unittest
from dataclasses import replace
from preview import preview, Rejected
from test_preview import Repository, FakeCore

class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.repo=Repository(); self.core=FakeCore()
        self.req={'caseId':'CASE-1','sourceIds':['A','B'],'caseEpochUtc':'2026-11-13T00:00:00Z'}
    def run_preview(self):
        return preview(self.req, principal='fixture-investigator', repository=self.repo, core=self.core)
    def test_revoke_while_resolving(self):
        resolve=self.repo.resolve
        def wrapped(*args):
            result=resolve(*args)
            if args[-1]=='B': self.repo.current=False
            return result
        self.repo.resolve=wrapped
        with self.assertRaises(Rejected): self.run_preview()
        self.assertEqual(self.core.calls,[])
    def test_changed_revision_before_compute(self):
        resolve=self.repo.resolve
        def wrapped(*args):
            result=resolve(*args)
            if args[-1]=='B': self.repo.records['A']=replace(self.repo.records['A'],revision='r2')
            return result
        self.repo.resolve=wrapped
        self.repo.recheck=lambda p,c,ss: all(self.repo.records[s.source_id]==s for s in ss)
        with self.assertRaises(Rejected): self.run_preview()
        self.assertFalse(self.core.calls)
    def test_falsey_and_truthy_nonbool_denied(self):
        for value in [False,None,0,1,'true',[],{}]:
            with self.subTest(value=value):
                self.repo.recheck=lambda *a:value
                with self.assertRaises(Rejected):self.run_preview()
                self.assertFalse(self.core.calls)
    def test_precheck_exception_never_calls_core(self):
        def denied(*a):raise PermissionError('fixture-denied')
        self.repo.recheck=denied
        with self.assertRaises(PermissionError):self.run_preview()
        self.assertFalse(self.core.calls)
    def test_pre_and_post_same_context(self):
        seen=[]
        self.repo.recheck=lambda *a: seen.append(a) or True
        self.run_preview()
        self.assertEqual(len(seen),2)
        self.assertEqual(seen[0],seen[1])
        self.assertEqual(seen[0][:2],('fixture-investigator','CASE-1'))
        self.assertIsInstance(seen[0][2],tuple)
    def test_postcheck_still_refuses_revocation(self):
        self.core.change=lambda:setattr(self.repo,'current',False)
        with self.assertRaises(Rejected):self.run_preview()
        self.assertEqual(len(self.core.calls),1)
    def test_no_second_compute(self):
        self.run_preview();self.assertEqual(len(self.core.calls),1)

if __name__=='__main__':unittest.main()
