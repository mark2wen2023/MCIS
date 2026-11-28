"""Check research surface and equipment evidence packages without granting engineering approval."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
import re
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


def glb_triangle_count(path: Path) -> int:
    """Count triangles from GLB primitives and validate referenced index data."""
    raw = path.read_bytes()
    if len(raw) < 20:
        raise ValueError("GLB is shorter than its header and JSON chunk")
    magic, version, total_length = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF" or version != 2 or total_length != len(raw):
        raise ValueError("invalid GLB 2.0 header or declared length")
    offset = 12
    document = None
    binary = None
    while offset < len(raw):
        if offset + 8 > len(raw):
            raise ValueError("truncated GLB chunk header")
        chunk_length, chunk_type = struct.unpack_from("<II", raw, offset)
        offset += 8
        end = offset + chunk_length
        if end > len(raw):
            raise ValueError("truncated GLB chunk payload")
        if chunk_type == 0x4E4F534A:
            if document is not None:
                raise ValueError("GLB has multiple JSON chunks")
            document = json.loads(raw[offset:end].decode("utf-8").rstrip(" \t\r\n\0"))
        elif chunk_type == 0x004E4942:
            if binary is not None:
                raise ValueError("GLB has multiple BIN chunks")
            binary = memoryview(raw)[offset:end]
        offset = end
    if document is None or document.get("asset", {}).get("version") != "2.0":
        raise ValueError("GLB lacks a valid glTF 2.0 JSON document")
    buffers = document.get("buffers", [])
    buffer_views = document.get("bufferViews", [])
    accessors = document.get("accessors", [])
    meshes = document.get("meshes", [])
    if (not meshes or len(buffers) != 1 or binary is None or buffers[0].get("uri") is not None
            or not isinstance(buffers[0].get("byteLength"), int)
            or buffers[0]["byteLength"] > len(binary) or len(binary) - buffers[0]["byteLength"] > 3):
        raise ValueError("GLB must contain meshes and one valid embedded binary buffer")

    component_formats = {5121: ("<B", 1), 5123: ("<H", 2), 5125: ("<I", 4), 5126: ("<f", 4)}
    dimensions = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}

    def read_accessor(index: Any, *, indices: bool = False) -> tuple[dict[str, Any], list[int] | None]:
        if not isinstance(index, int) or index < 0 or index >= len(accessors):
            raise ValueError("mesh primitive references an invalid accessor")
        accessor = accessors[index]
        view_index = accessor.get("bufferView")
        if not isinstance(view_index, int) or view_index < 0 or view_index >= len(buffer_views):
            raise ValueError("accessor has no valid embedded bufferView")
        view = buffer_views[view_index]
        if view.get("buffer", 0) != 0:
            raise ValueError("accessor references a non-embedded buffer")
        count = accessor.get("count")
        component = component_formats.get(accessor.get("componentType"))
        item_count = dimensions.get(accessor.get("type"))
        if not isinstance(count, int) or count < 0 or component is None or item_count is None:
            raise ValueError("accessor has invalid type or count")
        if indices and (accessor.get("type") != "SCALAR" or accessor.get("componentType") not in (5121, 5123, 5125)):
            raise ValueError("index accessor must use an unsigned scalar type")
        fmt, component_size = component
        element_size = component_size * item_count
        stride = view.get("byteStride", element_size)
        view_length = view.get("byteLength")
        view_offset = view.get("byteOffset", 0)
        accessor_offset = accessor.get("byteOffset", 0)
        if (not isinstance(stride, int) or stride < element_size or stride % component_size
                or not isinstance(view_length, int) or not isinstance(view_offset, int)
                or not isinstance(accessor_offset, int) or min(view_length, view_offset, accessor_offset) < 0):
            raise ValueError("bufferView/accessor offsets or stride are invalid")
        required = accessor_offset if count == 0 else accessor_offset + (count - 1) * stride + element_size
        if required > view_length or view_offset + view_length > buffers[0]["byteLength"]:
            raise ValueError("accessor data extends beyond its bufferView")
        if not indices:
            return accessor, None
        values = [struct.unpack_from(fmt, binary, view_offset + accessor_offset + n * stride)[0] for n in range(count)]
        return accessor, values

    triangles = 0
    for mesh in meshes:
        for primitive in mesh.get("primitives", []):
            mode = primitive.get("mode", 4)
            if mode not in range(7):
                raise ValueError(f"invalid glTF primitive mode {mode!r}")
            attributes = primitive.get("attributes", {})
            position = attributes.get("POSITION")
            if position is None:
                raise ValueError("mesh primitive has no valid POSITION accessor")
            position_accessor, _ = read_accessor(position)
            index = primitive.get("indices")
            if index is None:
                count = position_accessor["count"]
            else:
                index_accessor, values = read_accessor(index, indices=True)
                if any(value >= position_accessor["count"] for value in values):
                    raise ValueError("mesh index references a missing POSITION vertex")
                count = index_accessor["count"]
            if mode == 4:
                if count % 3:
                    raise ValueError("triangle primitive element count is not divisible by three")
                triangles += count // 3
            elif mode in (5, 6):
                triangles += max(0, count - 2)
    if triangles <= 0:
        raise ValueError("GLB contains no triangle primitives")
    return triangles


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _finite_vector(value: Any, size: int) -> bool:
    return (isinstance(value, list) and len(value) == size
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in value))


def _source_reference(value: Any) -> bool:
    return (isinstance(value, dict) and _is_sha256(value.get("source_sha256"))
            and isinstance(value.get("handles"), list) and bool(value["handles"])
            and all(isinstance(h, str) and h.strip() for h in value["handles"])
            and value.get("basis") in {"direct", "cross_view_registered", "surveyed", "derived"})


def _audit_strict_joints(data: dict[str, Any], errors: list[str]) -> None:
    joints = data.get("joints")
    if not isinstance(joints, list) or not joints:
        errors.append("strict package must contain at least one evidenced joint")
        return
    ids = [j.get("id") for j in joints if isinstance(j, dict)]
    nodes = [j.get("node") for j in joints if isinstance(j, dict)]
    if len(ids) != len(joints) or any(not isinstance(v, str) or not v.strip() for v in ids) or len(set(ids)) != len(ids):
        errors.append("strict joint ids must be non-empty and unique")
    if any(not isinstance(v, str) or not v.strip() for v in nodes) or len(set(nodes)) != len(nodes):
        errors.append("strict joint nodes must be non-empty and unique")
    package_approval = data.get("engineering_approved")
    for joint in joints:
        if not isinstance(joint, dict):
            errors.append("strict joint entry must be an object")
            continue
        joint_id = joint.get("id", "<unknown>")
        if joint.get("mode") != "strict":
            errors.append(f"{joint_id}: joint mode differs from strict package")
        if joint.get("engineering_approved") is not package_approval:
            errors.append(f"{joint_id}: package and joint engineering approval differ")
        if joint.get("engineering_approved") is True:
            errors.append(f"{joint_id}: this research asset auditor cannot accept engineering approval")
        if not isinstance(joint.get("parent"), str) or not joint["parent"].strip() or joint.get("parent") == joint.get("node"):
            errors.append(f"{joint_id}: invalid parent node")
        if joint.get("type") not in ("revolute", "continuous"):
            errors.append(f"{joint_id}: unsupported joint type")
        axis = joint.get("axis_local")
        if not _finite_vector(axis, 3) or abs(math.sqrt(sum(v * v for v in axis)) - 1.0) > 1e-6:
            errors.append(f"{joint_id}: strict joint axis must be a finite unit vector")
        if not _finite_vector(joint.get("pivot_parent_m"), 3):
            errors.append(f"{joint_id}: strict joint pivot must be a finite 3-vector")
        evidence = joint.get("evidence")
        if not isinstance(evidence, dict):
            errors.append(f"{joint_id}: strict joint lacks evidence object")
            continue
        for field in ("installation", "axis"):
            if not _source_reference(evidence.get(field)):
                errors.append(f"{joint_id}: strict joint lacks source-backed {field} evidence")
        limits = joint.get("limits_deg")
        if limits is not None:
            if (joint.get("type") != "revolute" or not _finite_vector(limits, 2)
                    or limits[0] >= limits[1] or not _source_reference(evidence.get("limits"))):
                errors.append(f"{joint_id}: limits require ordered revolute values and source evidence")


def audit_surfaces(report_path: Path, asset_root: Path) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        return {"integrity_passed": False, "engineering_approved": False,
                "region_count": 0, "partial_surface_count": 0, "blocked_count": 0,
                "blocked_regions": [], "checked_assets": [],
                "errors": ["surface report root must be an object"],
                "scope": "asset/evidence integrity only; does not approve geometry or release blocked regions"}
    assets = report.get("assets", {})
    regions = report.get("regions", [])
    checked = []
    errors = []
    if not isinstance(regions, list) or not regions:
        errors.append("surface report must contain at least one region")
        regions = []
    if not isinstance(assets, dict) or not assets:
        errors.append("surface report must contain at least one asset")
        assets = {}
    if not isinstance(report.get("engineering_approved"), bool):
        errors.append("surface report must declare engineering_approved as a boolean")
    elif report["engineering_approved"]:
        errors.append("this research asset auditor cannot accept or grant engineering approval")
    for region in regions:
        if not isinstance(region, dict):
            errors.append("surface report region entries must be objects")
            continue
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
        if not isinstance(asset, dict):
            errors.append(f"{region_id}: asset entry must be an object")
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
        try:
            actual_faces = glb_triangle_count(asset_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{region_id}: invalid GLB geometry: {exc}")
            continue
        evidence_hash = sha256(evidence_path)
        if actual_hash != asset.get("sha256"):
            errors.append(f"{region_id}: asset SHA-256 mismatch")
        if evidence_hash != region.get("evidence_sha256"):
            errors.append(f"{region_id}: evidence SHA-256 mismatch")
        if asset.get("faces") != region.get("faces"):
            errors.append(f"{region_id}: report face count mismatch")
        if asset.get("faces") != actual_faces:
            errors.append(f"{region_id}: reported face count differs from GLB triangle count")
        quality = asset.get("quality", {})
        if quality.get("closed_verified"):
            errors.append(f"{region_id}: open research patch is incorrectly marked closed")
        checked.append({
            "id": region_id,
            "status": status,
            "faces": actual_faces,
            "asset_sha256": actual_hash,
            "evidence_sha256": evidence_hash,
            "closed_verified": quality.get("closed_verified"),
        })
    if set(assets) - {r.get("id") for r in regions}:
        errors.append("asset table includes an unregistered region")
    return {
        "integrity_passed": not errors,
        "engineering_approved": False,
        "declared_engineering_approved": report.get("engineering_approved"),
        "strict_mode": report.get("mode") == "strict",
        "region_count": len(regions),
        "partial_surface_count": sum(isinstance(r, dict) and r.get("status") == "partial_surface" for r in regions),
        "blocked_count": sum(isinstance(r, dict) and r.get("status") == "blocked" for r in regions),
        "blocked_regions": [
            {"id": r.get("id"), "reason": r.get("reason")}
            for r in regions if isinstance(r, dict) and r.get("status") == "blocked"
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
    if mode not in ("demo", "strict"):
        errors.append("package mode must be demo or strict")
    if not isinstance(data.get("engineering_approved"), bool):
        errors.append("equipment package must declare engineering_approved as a boolean")
    elif data["engineering_approved"]:
        errors.append("this research asset auditor cannot accept or grant engineering approval")
    joints = data.get("joints")
    if not isinstance(joints, list):
        errors.append("joints must be an array")
        joints = []
    if any(not isinstance(joint, dict) for joint in joints):
        errors.append("joint entries must be objects")
        joints = [joint for joint in joints if isinstance(joint, dict)]
    if mode == "demo":
        if data.get("engineering_approved") is not False:
            errors.append("demo package must explicitly deny engineering approval")
        for joint in joints:
            if joint.get("mode") != "demo":
                errors.append(f"{joint.get('id')}: joint mode differs from demo package")
            if joint.get("engineering_approved") is not False:
                errors.append(f"{joint.get('id')}: demo joint carries engineering approval")
            for field in ("actual_limits_deg", "actual_rpm"):
                if joint.get(field) is not None:
                    errors.append(f"{joint.get('id')}: demo {field} must remain unknown")
    elif mode == "strict":
        _audit_strict_joints(data, errors)
    return {
        "integrity_passed": not errors,
        "mode": mode,
        "engineering_approved": False,
        "declared_engineering_approved": data.get("engineering_approved"),
        "joint_count": len(joints),
        "research_demo_joint_count": sum(isinstance(j, dict) and j.get("mode") == "demo" for j in joints),
        "engineering_verified_joint_count": 0,
        "declared_approved_joint_count": sum(isinstance(j, dict) and j.get("engineering_approved") is True for j in joints),
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
    result["engineering_approved"] = (
        result["integrity_passed"]
        and result["surface_audit"]["engineering_approved"]
        and result["equipment_audit"]["engineering_approved"]
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["integrity_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
