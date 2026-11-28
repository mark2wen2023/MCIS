import json
import tempfile
import unittest
from pathlib import Path

from research_asset_audit import audit_equipment, audit_surfaces, sha256


class ResearchAssetAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.asset_root = self.root / "assets"
        self.asset_root.mkdir()
        self.patch = self.asset_root / "patch.glb"
        self.patch.write_bytes(b"synthetic-open-patch")
        self.evidence = self.root / "region.json"
        self.evidence.write_text("{}", encoding="utf-8")
        self.report = self.root / "patch-report.json"
        self.data = {
            "mode": "strict",
            "engineering_approved": False,
            "regions": [
                {"id": "r1", "status": "partial_surface", "faces": 3,
                 "evidence": "region.json", "evidence_sha256": sha256(self.evidence)},
                {"id": "r2", "status": "blocked", "reason": "missing-source-corners"},
            ],
            "assets": {
                "r1": {"path": "patch.glb", "sha256": sha256(self.patch), "faces": 3,
                       "quality": {"closed_verified": False}}
            },
        }
        self._write_report()

    def tearDown(self):
        self.temp.cleanup()

    def _write_report(self):
        self.report.write_text(json.dumps(self.data), encoding="utf-8")

    def test_accepts_open_patch_and_separate_blocked_region(self):
        result = audit_surfaces(self.report, self.asset_root)
        self.assertTrue(result["integrity_passed"])
        self.assertFalse(result["engineering_approved"])
        self.assertEqual(result["blocked_count"], 1)

    def test_rejects_blocked_region_with_asset(self):
        self.data["assets"]["r2"] = self.data["assets"]["r1"]
        self._write_report()
        result = audit_surfaces(self.report, self.asset_root)
        self.assertFalse(result["integrity_passed"])

    def test_rejects_asset_hash_mismatch(self):
        self.data["assets"]["r1"]["sha256"] = "0" * 64
        self._write_report()
        self.assertFalse(audit_surfaces(self.report, self.asset_root)["integrity_passed"])

    def test_rejects_asset_path_escape(self):
        self.data["assets"]["r1"]["path"] = "../region.json"
        self._write_report()
        with self.assertRaises(ValueError):
            audit_surfaces(self.report, self.asset_root)

    def test_accepts_demo_joints_when_unknown_limits_remain_null(self):
        model = self.root / "demo.glb"
        model.write_bytes(b"demo-model")
        joints = self.root / "joints.json"
        joints.write_text(json.dumps({
            "mode": "demo", "engineering_approved": False,
            "model_sha256": sha256(model),
            "joints": [{"id": "rudder", "mode": "demo", "engineering_approved": False,
                        "actual_limits_deg": None, "actual_rpm": None}],
        }), encoding="utf-8")
        result = audit_equipment(joints, model)
        self.assertTrue(result["integrity_passed"])
        self.assertEqual(result["engineering_verified_joint_count"], 0)

    def test_rejects_demo_joint_with_fabricated_limit_or_approval(self):
        model = self.root / "demo.glb"
        model.write_bytes(b"demo-model")
        joints = self.root / "joints.json"
        joints.write_text(json.dumps({
            "mode": "demo", "engineering_approved": False,
            "model_sha256": sha256(model),
            "joints": [{"id": "rudder", "mode": "demo", "engineering_approved": True,
                        "actual_limits_deg": [-25, 25], "actual_rpm": None}],
        }), encoding="utf-8")
        self.assertFalse(audit_equipment(joints, model)["integrity_passed"])


if __name__ == "__main__":
    unittest.main()
