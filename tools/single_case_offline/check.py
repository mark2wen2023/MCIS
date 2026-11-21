"""Ordinary preflight helper guards; no business execution."""
import hashlib
import importlib.util
from pathlib import Path
import unittest
import tempfile
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
    def test_required_local_files(self):
        digest=hashlib.sha256(b'synthetic').hexdigest()
        config={'baseline':'fixed','files':[{'ref':'fixed','path':name,'sha256':digest} for name in r.REQUIRED_LOCAL], 'localFiles':{}}
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in r.REQUIRED_LOCAL:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'synthetic')
            r.require_local_inputs(root,config) # no unrelated Git-materialized files needed
            for name in r.REQUIRED_LOCAL:
                p=root/name;p.unlink()
                with self.subTest(name=name),self.assertRaisesRegex(ValueError,'required_local_missing'):
                    r.require_local_inputs(root,config)
                p.mkdir()
                with self.assertRaisesRegex(ValueError,'required_local_not_regular'):r.require_local_inputs(root,config)
                p.rmdir();p.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError,'fixed_input_mismatch'):r.require_local_inputs(root,config)
                p.write_bytes(b'synthetic')
    def test_no_dynamic_command(self):
        self.assertEqual(r.STAGES,('business_query.py','pilot_prepare.py','t100_seat_crosscheck.py','raw_fixture_prepare.py'))
if __name__=='__main__':unittest.main(verbosity=2)
