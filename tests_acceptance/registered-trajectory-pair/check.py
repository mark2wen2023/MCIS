"""No app imports: AST-extracted production functions + handwritten dependencies."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = 'f9f4e599cdb670d864a5e7e986067216e7105636'
ROUTER = 'service/mcis_service/evidence_intake/router.py'
PAIR = 'service/mcis_service/trajectory_exchange/registered_pair.py'

def compile_functions(source, names, namespace):
    tree = ast.parse(source)
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    # Only internal function's lazy router import is replaced by its explicit
    # extracted production helper; no FastAPI/ORM/package initializer executes.
    for node in nodes:
        if isinstance(node, ast.FunctionDef):
            node.body = [n for n in node.body if not isinstance(n, ast.ImportFrom)]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<production-ast>', 'exec'), namespace)

class Checks(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.rows = {}
        self.fail_digest = None
        self.deny_authorization = False
        self.deny_container = False
        self.ctx = types.SimpleNamespace(role='synthetic-role', operator='synthetic-subject')
        self.session = object()
        self.docs = [json.loads((ROOT / 'tests_acceptance/shared-trajectory-cross-repo-expanded' / name).read_text())
                     for name in ('vessel-a.json', 'vessel-b.json')]
        self.cid = self.docs[0]['caseId']
        self.pins = [self.put(i, doc) for i, doc in enumerate(self.docs)]
        def authorize(ctx, s, cid):
            self.assertIs(s, self.session)
            self.calls.append(('authorize', cid))
            if self.deny_authorization: raise PermissionError('synthetic authorization denial')
        def load(ctx, s, cid, digest):
            self.calls.append(('load', digest))
            if digest == self.fail_digest:
                raise PermissionError('synthetic denial')
            return self.rows[digest]
        def protect(s, cid, role, raw):
            self.calls.append(('container', hashlib.sha256(raw).hexdigest()))
            if self.deny_container: raise ValueError('synthetic container denial')
        def audit(s, **kw): self.calls.append(('audit', kw['evidence_id']))
        ns = dict(authorize=authorize, load_receipt=load, protect_container=protect,
                  evidence=types.SimpleNamespace(append_custody=audit),
                  problem=lambda *a: ValueError('missing'))
        # The helper's container import is the only import removed here.
        compile_functions((ROOT / ROUTER).read_text(), {'_read_original_for_access'}, ns)
        self.ns = ns
        ns.update(runpy.run_path(str(ROOT / 'service/mcis_service/trajectory_exchange/validation.py')))
        ns.update(hashlib=hashlib, json=json, re=__import__('re'))
        compile_functions((ROOT / PAIR).read_text(),
                          {'RegisteredPairError', '_fail', '_object', '_read_registered_pair', '_reject_replay'}, ns)

    def put(self, i, doc):
        raw = json.dumps(doc, separators=(',', ':')).encode()
        pin = dict(caseId=self.cid, evidenceId='SYN-E'+str(i), requestDigest=str(i+1)*64,
                   sourceSha256=hashlib.sha256(raw).hexdigest())
        self.rows[pin['requestDigest']] = (dict(pin), raw)
        return pin

    def read(self, pins=None):
        return self.ns['_read_registered_pair'](self.ctx, self.session, self.cid,
                                                self.pins if pins is None else pins, 'synthetic review')

    def test_existing_download_equivalence(self):
        old = ast.parse(subprocess.check_output(['git','show',BASE+':'+ROUTER], cwd=ROOT, text=True))
        new = ast.parse((ROOT / ROUTER).read_text())
        helper = next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='_read_original_for_access')
        download = next(n for n in new.body if isinstance(n,ast.AsyncFunctionDef) and n.name=='download')
        body = download.body[-1].body[0].body
        self.assertEqual(ast.unparse(body[-1]), 'receipt, raw = _read_original_for_access(ctx, s, case_id, digest, purpose)')
        body[-1:] = copy.deepcopy(helper.body[1:-1])
        new.body.remove(helper)
        self.assertEqual(ast.dump(old,include_attributes=False), ast.dump(new,include_attributes=False))

    def test_valid_pair_preserves_gaps_and_unknown_heading(self):
        result = self.read()
        self.assertEqual([r['document'] for r in result], self.docs)
        self.assertEqual([c[0] for c in self.calls], ['authorize','load','container','audit']*2)
        self.assertEqual(result[0]['document']['sampling']['missingIntervals'], self.docs[0]['sampling']['missingIntervals'])
        self.assertTrue(any(p['headingDeg']['value'] is None and p['courseDeg']['value'] is not None for p in self.docs[0]['points']))

    def test_wrong_case_before_read(self):
        bad = copy.deepcopy(self.pins); bad[1]['caseId']='SYN-OTHER'
        with self.assertRaisesRegex(ValueError,'CASE_MISMATCH'): self.read(bad)
        self.assertEqual(self.calls, [])

    def test_denial_propagates_without_pair(self):
        self.fail_digest = self.pins[1]['requestDigest']
        with self.assertRaises(PermissionError): self.read()
        self.assertEqual([c[0] for c in self.calls], ['authorize','load','container','audit','authorize','load'])

    def test_authorization_and_container_fail_before_audit(self):
        self.deny_authorization=True
        with self.assertRaises(PermissionError): self.read()
        self.assertEqual([k for k,v in self.calls], ['authorize'])
        self.deny_authorization=False; self.deny_container=True; self.calls.clear()
        with self.assertRaisesRegex(ValueError,'container denial'): self.read()
        self.assertEqual([k for k,v in self.calls], ['authorize','load','container'])

    def test_wrong_sha_and_receipt(self):
        p=copy.deepcopy(self.pins); p[0]['sourceSha256']='f'*64
        with self.assertRaisesRegex(ValueError,'PIN_MISMATCH'): self.read(p)
        receipt, raw=self.rows[self.pins[0]['requestDigest']]
        self.rows[self.pins[0]['requestDigest']]=(receipt,raw+b' ')
        with self.assertRaisesRegex(ValueError,'SHA_MISMATCH'): self.read()

    def test_contract_and_same_vessel(self):
        self.pins[1]=self.put(1, {})
        with self.assertRaisesRegex(ValueError,'TRAJECTORY_INVALID'): self.read()
        self.pins[1]=self.put(1, self.docs[0])
        with self.assertRaisesRegex(ValueError,'DUPLICATE_VESSEL'): self.read()

    def test_document_case(self):
        doc=copy.deepcopy(self.docs[1]); doc['caseId']='SYN-OTHER'
        self.pins[1]=self.put(1,doc)
        with self.assertRaisesRegex(ValueError,'DOCUMENT_CASE_MISMATCH'): self.read()

    def test_finite_replay_diagnostics(self):
        for code, change in [
            ('POSITION_MISSING', lambda d: d['points'][0].update(position={**d['points'][0]['position'], 'kind':'missing', 'value':None})),
            ('IDENTITY_UNRESOLVED', lambda d: d['vessel'].update(identityStatus='unresolved')),
            ('TIME_UNRESOLVED', lambda d: d['points'][0]['time'].update(status='unresolved', alignedUtc=None, correctionSeconds=None)),
            ('TIME_CONFLICT', lambda d: d['points'][0]['time'].update(status='conflict', alignedUtc=None, correctionSeconds=None)),
        ]:
            with self.subTest(code=code):
                doc=copy.deepcopy(self.docs[1]); change(doc)
                self.pins[1]=self.put(1,doc)
                with self.assertRaisesRegex(ValueError,'REPLAY_BLOCKED:'+code): self.read()
        doc=copy.deepcopy(self.docs[1])
        doc['points'][1]['time']=copy.deepcopy(doc['points'][0]['time'])
        self.pins[1]=self.put(1,doc)
        with self.assertRaisesRegex(ValueError,'REPLAY_BLOCKED:TIME_NOT_INCREASING'): self.read()
        doc=copy.deepcopy(self.docs[1]); doc['vessel']['identityStatus']='unresolved'
        doc['points'][0]['position'].update(kind='missing',value=None)
        self.pins[1]=self.put(1,doc)
        with self.assertRaisesRegex(ValueError,'REPLAY_BLOCKED:IDENTITY_UNRESOLVED,POSITION_MISSING'): self.read()
        with self.assertRaisesRegex(ValueError,'REPLAY_VALIDATION_UNKNOWN'):
            self.ns['_reject_replay']({'issues':[{'code':'future'}]})

    def test_old_pins_no_latest_fallback(self):
        expected=self.read()
        self.rows['9'*64]=({'caseId':self.cid},b'new unrelated revision')
        self.calls.clear()
        self.assertEqual(self.read(),expected)
        self.assertEqual([v for k,v in self.calls if k=='load'],[p['requestDigest'] for p in self.pins])

if __name__=='__main__': unittest.main(verbosity=2)
