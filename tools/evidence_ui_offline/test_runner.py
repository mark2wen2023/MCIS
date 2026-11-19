"""Runner guard tests: fabricated paths/bytes and mocked subprocesses only."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import hashlib
spec=importlib.util.spec_from_file_location('offline_runner',Path(__file__).with_name('run.py'))
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
class Guards(unittest.TestCase):
    def test_fixed_source_missing_and_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();p=root/'test.js';p.write_text('synthetic')
            spec={'baseline':'synthetic-commit','files':{'test.js':hashlib.sha256(p.read_bytes()).hexdigest()}}
            def git(_, *args):return str(root) if '--show-toplevel' in args else 'commit' if '-t' in args else 'synthetic-head'
            with patch.object(r,'git',git),patch.object(r.subprocess,'run',return_value=SimpleNamespace(returncode=0)):
                r.verify(root,spec)
                p.write_text('different')
                with self.assertRaisesRegex(ValueError,'偏离'):r.verify(root,spec)
                p.unlink()
                with self.assertRaisesRegex(ValueError,'缺失'):r.verify(root,spec)
    def test_failed_process_and_missing_completion(self):
        for code,stdout in [(1,'PASS'),(0,'pending only')]:
            with patch.object(r.subprocess,'run',return_value=SimpleNamespace(returncode=code,stdout=stdout)):
                with self.assertRaises(ValueError):r.run(['synthetic'],'synthetic',{},'PASS')
    def test_missing_dependencies_fail_before_tests(self):
        with tempfile.TemporaryDirectory() as tmp:
            ui=Path(tmp)/'ui';media=Path(tmp)/'media';ui.mkdir();media.mkdir()
            with patch.object(r.sys,'argv',['run.py','--workbench',str(ui),'--media',str(media)]),patch.object(r,'verify'),patch.object(r.shutil,'which',return_value='synthetic-node'),patch.object(r,'run') as run:
                with self.assertRaisesRegex(ValueError,'离线依赖'):r.main()
                run.assert_not_called()
    def test_same_checkout_cli_fails_before_work(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(r.sys,'argv',['run.py','--workbench',tmp,'--media',tmp]),patch.object(r,'verify') as verify:
            with self.assertRaisesRegex(ValueError,'独立'):r.main()
            verify.assert_not_called()
if __name__=='__main__':unittest.main()
