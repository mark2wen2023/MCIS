"""Ordinary preflight helper guards; no business execution."""
import hashlib
import importlib.util
from pathlib import Path
import unittest
spec=importlib.util.spec_from_file_location('runner',Path(__file__).with_name('run.py'))
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
class Guards(unittest.TestCase):
    def test_bytes(self):
        digest=hashlib.sha256(b'synthetic').hexdigest()
        r.require_bytes(b'synthetic',digest)
        with self.assertRaises(ValueError):r.require_bytes(b'changed',digest)
    def test_dependencies(self):
        r.require_versions({'a':'1'},{'a':'1'})
        for actual in ({},{'a':'2'}):
            with self.assertRaises(ValueError):r.require_versions(actual,{'a':'1'})
    def test_no_dynamic_command(self):
        self.assertEqual(r.STAGES,('business_query.py','pilot_prepare.py','t100_seat_crosscheck.py','raw_fixture_prepare.py'))
if __name__=='__main__':unittest.main(verbosity=2)
