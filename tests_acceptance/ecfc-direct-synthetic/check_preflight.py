"""Subprocess checks of the real preflight only. No simulated core or DB."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('check.py')
REPO = Path(__file__).resolve().parents[2]


class Preflight(unittest.TestCase):
    def call(self, *args):
        return subprocess.run([sys.executable, '-I', '-B', str(SCRIPT), *args],
                              text=True, capture_output=True, timeout=30)

    def test_pinned_sources_real_imports_and_fixture(self):
        result = self.call('--repo', str(REPO))
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        record = json.loads(lines[0])
        self.assertEqual(record['phase'], 'preflight')
        self.assertTrue(record['passed'])
        self.assertFalse(record['databaseCreated'])
        self.assertFalse(record['coreRun'])
        self.assertTrue(lines[1].startswith('PENDING:'))
        self.assertNotIn('real_save_reopen_and_read', result.stdout)

    def test_missing_git_objects_fail_without_fallback(self):
        with tempfile.TemporaryDirectory() as empty:
            result = self.call('--repo', empty)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('"passed": true', result.stdout)
        self.assertFalse(json.loads(result.stderr.splitlines()[-1])['passed'])

    def test_run_needs_explicit_existing_sdk(self):
        result = self.call('--repo', str(REPO), '--run')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertFalse(json.loads(result.stderr)['passed'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
