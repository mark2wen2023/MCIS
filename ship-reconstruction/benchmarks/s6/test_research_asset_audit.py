import json
import struct
import tempfile
import unittest
from pathlib import Path

from research_asset_audit import audit_equipment, audit_surfaces, glb_triangle_count, sha256


def write_glb(path, triangle_count=3):
    count = triangle_count * 3
    positions = bytes(count * 3 * 4)
    indices = struct.pack("<" + "H" * count, *range(count))
    binary = positions + indices
    byte_length = len(binary)
    binary += b"\0" * ((-len(binary)) % 4)
    document = {
        "asset": {"version": "2.0"},
        "buffers": [{"byteLength": byte_length}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(positions)},
            {"buffer": 0, "byteOffset": len(positions), "byteLength": len(indices)},
        ],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": count, "type": "VEC3"},
            {"bufferView": 1, "componentType": 5123, "count": count, "type": "SCALAR"},
        ],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
    }
    chunk = json.dumps(document, separators=(",", ":")).encode("utf-8")
    chunk += b" " * ((-len(chunk)) % 4)
    binary_chunk = struct.pack("<II", len(binary), 0x004E4942) + binary
    json_chunk = struct.pack("<II", len(chunk), 0x4E4F534A) + chunk
    total = 12 + len(json_chunk) + len(binary_chunk)
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, total) + json_chunk + binary_chunk)


class ResearchAssetAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.asset_root = self.root / "assets"
        self.asset_root.mkdir()
        self.patch = self.asset_root / "patch.glb"
        write_glb(self.patch, 3)
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
        self.assertIsNone(result["precision_gate_passed"])
        self.assertEqual(result["blocked_count"], 1)

    def test_failed_accuracy_gate_never_becomes_engineering_approval(self):
        accuracy = {"holdout_policy_passed": False, "status": "rejected", "reason": "residual_limit"}
        self.evidence.write_text(json.dumps({"accuracy": accuracy}), encoding="utf-8")
        self.data["regions"][0]["accuracy"] = accuracy
        self.data["regions"][0]["evidence_sha256"] = sha256(self.evidence)
        self._write_report()
        result = audit_surfaces(self.report, self.asset_root)
        self.assertTrue(result["integrity_passed"])
        self.assertFalse(result["precision_gate_passed"])
        self.assertFalse(result["engineering_approved"])

    def test_accuracy_gate_must_match_linked_evidence(self):
        self.evidence.write_text(json.dumps({"accuracy": {"status": "passed", "holdout_policy_passed": True}}), encoding="utf-8")
        self.data["regions"][0]["accuracy"] = {"status": "rejected", "holdout_policy_passed": False}
        self.data["regions"][0]["evidence_sha256"] = sha256(self.evidence)
        self._write_report()
        result = audit_surfaces(self.report, self.asset_root)
        self.assertFalse(result["integrity_passed"])
        self.assertFalse(result["precision_gate_passed"])

    def test_rejects_empty_regions_and_empty_assets(self):
        self.data["regions"] = []
        self.data["assets"] = {}
        self._write_report()
        result = audit_surfaces(self.report, self.asset_root)
        self.assertFalse(result["integrity_passed"])
        self.assertEqual(result["checked_assets"], [])

    def test_rejects_empty_assets_even_when_regions_are_blocked(self):
        self.data["regions"] = [{"id": "r2", "status": "blocked", "reason": "unknown"}]
        self.data["assets"] = {}
        self._write_report()
        self.assertFalse(audit_surfaces(self.report, self.asset_root)["integrity_passed"])

    def test_reported_surface_approval_is_not_accepted_by_research_auditor(self):
        self.data["engineering_approved"] = True
        self._write_report()
        result = audit_surfaces(self.report, self.asset_root)
        self.assertFalse(result["integrity_passed"])
        self.assertFalse(result["engineering_approved"])
        self.assertTrue(result["declared_engineering_approved"])

    def test_rejects_blocked_region_with_asset(self):
        self.data["assets"]["r2"] = self.data["assets"]["r1"]
        self._write_report()
        result = audit_surfaces(self.report, self.asset_root)
        self.assertFalse(result["integrity_passed"])

    def test_rejects_asset_hash_mismatch(self):
        self.data["assets"]["r1"]["sha256"] = "0" * 64
        self._write_report()
        self.assertFalse(audit_surfaces(self.report, self.asset_root)["integrity_passed"])

    def test_rejects_reported_face_count_that_disagrees_with_glb(self):
        self.data["assets"]["r1"]["faces"] = 4
        self.data["regions"][0]["faces"] = 4
        self._write_report()
        result = audit_surfaces(self.report, self.asset_root)
        self.assertFalse(result["integrity_passed"])
        self.assertEqual(glb_triangle_count(self.patch), 3)

    def test_rejects_invalid_glb_even_when_digest_matches(self):
        self.patch.write_bytes(b"not-a-glb")
        self.data["assets"]["r1"]["sha256"] = sha256(self.patch)
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

    def _strict_package(self, model, *, evidence=True, approved=False):
        ref = {"source_sha256": "a" * 64, "handles": ["A12"], "basis": "cross_view_registered"}
        joint_evidence = {"installation": ref, "axis": ref, "limits": ref} if evidence else {}
        return {
            "mode": "strict", "engineering_approved": approved,
            "model_sha256": sha256(model),
            "joints": [{"id": "rudder", "node": "Rudder", "parent": "Ship",
                        "mode": "strict", "type": "revolute", "axis_local": [0, 1, 0],
                        "pivot_parent_m": [1, 2, 3], "limits_deg": [-20, 20],
                        "engineering_approved": approved, "evidence": joint_evidence}],
        }

    def test_strict_mode_requires_installation_axis_and_limit_evidence(self):
        model = self.root / "strict.glb"
        model.write_bytes(b"strict-model")
        joints = self.root / "strict.json"
        joints.write_text(json.dumps(self._strict_package(model, evidence=False)), encoding="utf-8")
        result = audit_equipment(joints, model)
        self.assertFalse(result["integrity_passed"])
        self.assertFalse(result["engineering_approved"])

    def test_valid_strict_evidence_does_not_auto_approve_unapproved_package(self):
        model = self.root / "strict.glb"
        model.write_bytes(b"strict-model")
        joints = self.root / "strict.json"
        joints.write_text(json.dumps(self._strict_package(model, approved=False)), encoding="utf-8")
        result = audit_equipment(joints, model)
        self.assertTrue(result["integrity_passed"])
        self.assertFalse(result["engineering_approved"])

    def test_approval_flags_must_match_between_package_and_joints(self):
        model = self.root / "strict.glb"
        model.write_bytes(b"strict-model")
        data = self._strict_package(model, approved=False)
        data["joints"][0]["engineering_approved"] = True
        joints = self.root / "strict.json"
        joints.write_text(json.dumps(data), encoding="utf-8")
        self.assertFalse(audit_equipment(joints, model)["integrity_passed"])

    def test_strict_source_approval_is_not_granted_or_accepted_by_auditor(self):
        model = self.root / "strict.glb"
        model.write_bytes(b"strict-model")
        joints = self.root / "strict.json"
        joints.write_text(json.dumps(self._strict_package(model, approved=True)), encoding="utf-8")
        result = audit_equipment(joints, model)
        self.assertFalse(result["integrity_passed"])
        self.assertFalse(result["engineering_approved"])
        self.assertEqual(result["declared_approved_joint_count"], 1)


if __name__ == "__main__":
    unittest.main()
