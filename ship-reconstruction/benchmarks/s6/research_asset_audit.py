"""Check research surface and equipment evidence packages without granting engineering approval."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_file(root: Path, name: str) -> Path:
    candidate = (root / name).resolve()
    if candidate != root.resolve() and root.resolve() not in candidate.parents:
        raise ValueError(f"asset path escapes package root: {name}")
    return candidate


def audit_surfaces(report_path: Path, asset_root: Path) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assets = report.get("assets", {})
    regions = report.get("regions", [])
    checked = []
    errors = []
    for region in regions:
        region_id = region.get("id")
        status = region.get("status")
        asset = assets.get(region_id)
        if status == "blocked":
            if asset is not None or region.get("evidence"):
                errors.append(f"{region_id}: blocked region carries deliverable asset/evidence")
            continue
        if status != "partial_surface":
            errors.append(f"{region_id}: unsupported region state {status!r}")
            continue
        if not asset or not region.get("evidence"):
            errors.append(f"{region_id}: partial surface lacks linked asset or evidence")
            continue
        asset_path = _relative_file(asset_root, asset.get("path", ""))
        evidence_path = _relative_file(report_path.parent, region["evidence"])
        if not asset_path.is_file():
            errors.append(f"{region_id}: asset file missing")
            continue
        if not evidence_path.is_file():
            errors.append(f"{region_id}: evidence file missing")
            continue
        actual_hash = sha256(asset_path)
        evidence_hash = sha256(evidence_path)
        if actual_hash != asset.get("sha256"):
            errors.append(f"{region_id}: asset SHA-256 mismatch")
        if evidence_hash != region.get("evidence_sha256"):
            errors.append(f"{region_id}: evidence SHA-256 mismatch")
        if asset.get("faces") != region.get("faces"):
            errors.append(f"{region_id}: face count mismatch")
        quality = asset.get("quality", {})
        if quality.get("closed_verified"):
            errors.append(f"{region_id}: open research patch is incorrectly marked closed")
        checked.append({
            "id": region_id,
            "status": status,
            "faces": asset.get("faces"),
            "asset_sha256": actual_hash,
            "evidence_sha256": evidence_hash,
            "closed_verified": quality.get("closed_verified"),
        })
    if set(assets) - {r.get("id") for r in regions}:
        errors.append("asset table includes an unregistered region")
    return {
        "integrity_passed": not errors,
        "engineering_approved": bool(report.get("engineering_approved", False)),
        "strict_mode": report.get("mode") == "strict",
        "region_count": len(regions),
        "partial_surface_count": sum(r.get("status") == "partial_surface" for r in regions),
        "blocked_count": sum(r.get("status") == "blocked" for r in regions),
        "blocked_regions": [
            {"id": r.get("id"), "reason": r.get("reason")}
            for r in regions if r.get("status") == "blocked"
        ],
        "checked_assets": checked,
        "errors": errors,
        "scope": "asset/evidence integrity only; does not approve geometry or release blocked regions",
    }


def audit_equipment(joints_path: Path, model_path: Path) -> dict[str, Any]:
    data = json.loads(joints_path.read_text(encoding="utf-8"))
    errors = []
    actual_hash = sha256(model_path)
    if data.get("model_sha256") != actual_hash:
        errors.append("GLB SHA-256 does not match joint evidence")
    mode = data.get("mode")
    if mode == "demo":
        if data.get("engineering_approved") is not False:
            errors.append("demo package must explicitly deny engineering approval")
        for joint in data.get("joints", []):
            if joint.get("mode") != "demo":
                errors.append(f"{joint.get('id')}: joint mode differs from demo package")
            if joint.get("engineering_approved") is not False:
                errors.append(f"{joint.get('id')}: demo joint carries engineering approval")
            for field in ("actual_limits_deg", "actual_rpm"):
                if joint.get(field) is not None:
                    errors.append(f"{joint.get('id')}: demo {field} must remain unknown")
    return {
        "integrity_passed": not errors,
        "mode": mode,
        "engineering_approved": bool(data.get("engineering_approved", False)),
        "joint_count": len(data.get("joints", [])),
        "research_demo_joint_count": sum(j.get("mode") == "demo" for j in data.get("joints", [])),
        "engineering_verified_joint_count": sum(j.get("engineering_approved") is True for j in data.get("joints", [])),
        "glb_sha256": actual_hash,
        "errors": errors,
        "scope": "package consistency only; does not validate installation geometry or motion limits",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--surface-report", type=Path, required=True)
    parser.add_argument("--surface-root", type=Path, required=True)
    parser.add_argument("--joints", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = {
        "surface_audit": audit_surfaces(args.surface_report, args.surface_root),
        "equipment_audit": audit_equipment(args.joints, args.model),
    }
    result["integrity_passed"] = all(
        result[name]["integrity_passed"] for name in ("surface_audit", "equipment_audit")
    )
    result["engineering_approved"] = False
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["integrity_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
