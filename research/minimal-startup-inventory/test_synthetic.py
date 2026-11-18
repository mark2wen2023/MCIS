"""New ordinary directory fixtures only. No application, network, DB, or permission probes."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from check_inventory import inspect

class SyntheticInventory(unittest.TestCase):
    def test_exact_self_made_files_still_not_runnable(self):
        with tempfile.TemporaryDirectory() as d:
            content = b"SYNTHETIC INVENTORY TEXT\n"
            Path(d, "input.txt").write_bytes(content)
            r = inspect(d, {"format": 1, "files": [
                {"path": "input.txt", "sha256": hashlib.sha256(content).hexdigest()}]})
            self.assertTrue(r["inventory_matches"])
            self.assertFalse(r["startup_allowed"])
            self.assertEqual(r["reasons"], ["EXECUTABLE_CLOSURE_NOT_PROVEN"])

    def test_incomplete_preparation_remains_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            r = inspect(d, {"format": 1, "files": [
                {"path": "not-prepared.txt", "sha256": "0"*64}]})
            self.assertFalse(r["inventory_matches"])
            self.assertFalse(r["startup_allowed"])
            self.assertIn("FILE_SET_INCOMPLETE_OR_EXTRA", r["reasons"])

    def test_empty_inventory_does_not_prove_service(self):
        with tempfile.TemporaryDirectory() as d:
            r = inspect(d, {"format": 1, "files": []})
            self.assertTrue(r["inventory_matches"])
            self.assertFalse(r["startup_allowed"])
