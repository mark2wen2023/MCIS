"""New ordinary directory fixtures only. No application, network, DB, or permission probes."""
import hashlib
import tempfile
import unittest
from unittest.mock import patch
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

    def test_scan_callback_error_cannot_match_empty_inventory(self):
        def fake_walk(root, *, followlinks, onerror):
            self.assertFalse(followlinks)
            onerror(OSError("synthetic scanner failure"))
            yield str(root), [], []
        with tempfile.TemporaryDirectory() as d, patch("check_inventory.os.walk", fake_walk):
            r = inspect(d, {"format": 1, "files": []})
        self.assertFalse(r["inventory_matches"])
        self.assertFalse(r["startup_allowed"])
        self.assertIn("SCAN_INCOMPLETE", r["reasons"])

    def test_partial_scan_error_never_hashes_discovered_files(self):
        def fake_walk(root, *, followlinks, onerror):
            yield str(root), [], ["input.txt"]
            onerror(OSError("synthetic late scanner failure"))
        with tempfile.TemporaryDirectory() as d:
            content = b"SYNTHETIC ONLY"
            Path(d, "input.txt").write_bytes(content)
            manifest = {"format": 1, "files": [
                {"path": "input.txt", "sha256": hashlib.sha256(content).hexdigest()}]}
            with patch("check_inventory.os.walk", fake_walk):
                r = inspect(d, manifest)
        self.assertFalse(r["inventory_matches"])
        self.assertFalse(r["startup_allowed"])
        self.assertEqual(r["files"], [])
        self.assertIn("SCAN_INCOMPLETE", r["reasons"])

    def test_iterator_exception_reports_incomplete(self):
        def fake_walk(root, **kwargs):
            raise OSError("synthetic iterator error")
            yield
        with tempfile.TemporaryDirectory() as d, patch("check_inventory.os.walk", fake_walk):
            r = inspect(d, {"format": 1, "files": []})
        self.assertFalse(r["inventory_matches"])
        self.assertFalse(r["startup_allowed"])
        self.assertIn("SCAN_INCOMPLETE", r["reasons"])
