"""Independent probes of the preflight host boundary; synthetic ports only."""
import unittest
from preview import preview, Rejected
from test_preview import Repository, FakeCore

class IndependentPreflightTests(unittest.TestCase):
    def setUp(self):
        self.repo=Repository();self.core=FakeCore()
        self.request={'caseId':'CASE-1','sourceIds':['A','B'],'caseEpochUtc':'2026-11-13T00:00:00Z'}
    def run_preview(self):
        return preview(self.request,principal='fixture-investigator',repository=self.repo,core=self.core)
    def test_exact_order(self):
        events=[];resolve=self.repo.resolve;align=self.core.align
        def tracked_resolve(*a):events.append('resolve:'+a[-1]);return resolve(*a)
        def tracked_check(*a):events.append('check');return True
        def tracked_align(p):events.append('core');return align(p)
        self.repo.resolve=tracked_resolve;self.repo.recheck=tracked_check;self.core.align=tracked_align
        self.run_preview()
        self.assertEqual(events,['resolve:A','resolve:B','check','core','check'])
    def test_late_source_denial_no_preflight_or_core(self):
        resolve=self.repo.resolve;checks=[]
        def denied(*a):
            if a[-1]=='B':raise PermissionError('denied')
            return resolve(*a)
        self.repo.resolve=denied;self.repo.recheck=lambda *a:checks.append(a) or True
        with self.assertRaises(PermissionError):self.run_preview()
        self.assertEqual(checks,[]);self.assertEqual(self.core.calls,[])
    def test_preflight_error_is_generic(self):
        self.repo.recheck=lambda *a:False
        with self.assertRaises(Rejected) as caught:self.run_preview()
        self.assertEqual(str(caught.exception),'permission or evidence changed before compute')
        self.assertEqual(self.core.calls,[])
    def test_post_truthy_nonboolean_rejected(self):
        answers=iter([True,'yes']);self.repo.recheck=lambda *a:next(answers)
        with self.assertRaises(Rejected):self.run_preview()
        self.assertEqual(len(self.core.calls),1)
    def test_post_failure_exception_no_output(self):
        calls=[]
        def check(*a):
            calls.append(a)
            if len(calls)==2:raise RuntimeError('repository unavailable')
            return True
        self.repo.recheck=check
        with self.assertRaises(RuntimeError):self.run_preview()
        self.assertEqual(len(self.core.calls),1)
    def test_malformed_request_no_repository_call(self):
        self.request['allowed']=True
        self.repo.resolve=lambda *a:self.fail('resolve before request validation')
        self.repo.recheck=lambda *a:self.fail('check before request validation')
        with self.assertRaises(Rejected):self.run_preview()
        self.assertEqual(self.core.calls,[])

if __name__=='__main__':unittest.main()
