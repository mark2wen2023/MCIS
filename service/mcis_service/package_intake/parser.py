"""Bounded, read-only intake of explicitly supported basic .mcase packages.

Original members and chain lines are retained; unsupported content fails closed.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
import zlib
import lzma
import re
import stat
import zipfile
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..common import contracts
from ..common.context import problem
from ..environment.service import validate_observations
from ..package.mcase import CASE_FIELDS, CASE_EXT_FIELDS, PACKAGE_FORMAT, PACKAGE_VERSION, infer_role, REQUIRED_DIRS
from ..redaction.policy import default_policy

MAX_COMPRESSED = 32 * 1024 * 1024
MAX_EXPANDED = 64 * 1024 * 1024
MAX_MEMBER = 16 * 1024 * 1024
MAX_MEMBERS = 2048
MAX_DEPTH = 64


def fail(detail: str):
    raise problem(422, "PACKAGE_INTAKE_INVALID", detail)


def strict_json(raw: bytes) -> Any:
    if raw.startswith(b"\xef\xbb\xbf"):
        fail("本切片仅支持无 BOM 的 UTF-8 JSON/JSONL")
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError("duplicate JSON key")
            out[k] = v
        return out
    try:
        value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite JSON")))
        stack = [(value, 0)]
        while stack:
            node, depth = stack.pop()
            if depth > MAX_DEPTH:
                raise ValueError("JSON too deep")
            if isinstance(node, float) and not math.isfinite(node):
                raise ValueError("non-finite JSON")
            if isinstance(node, str):
                node.encode("utf-8")  # reject unpaired surrogate escapes
            if isinstance(node, dict):
                stack.extend((v, depth + 1) for v in node.values())
                for k in node:
                    k.encode("utf-8")
            elif isinstance(node, list):
                stack.extend((v, depth + 1) for v in node)
        return value
    except (ValueError, UnicodeError, RecursionError, OverflowError) as exc:
        fail(f"无效 JSON：{exc}")


def safe_path(name: str) -> str:
    if not isinstance(name, str) or not name or "\\" in name or any(ord(c) < 32 for c in name):
        fail("无效包路径")
    if any(p in ("", ".", "..") or ":" in p or p.endswith((" ", ".")) for p in name.split("/")):
        fail("不安全的包路径")
    return name


def read_bounded(data: bytes) -> dict[str, bytes]:
    if len(data) > MAX_COMPRESSED:
        fail("压缩包超过 32 MiB")
    files = {}
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_MEMBERS:
                fail("包成员超过 2048")
            seen = set()
            total = 0
            for info in infos:
                original = info.orig_filename
                name = safe_path(original[:-1] if info.is_dir() else original)
                folded = name.casefold()
                mode = info.external_attr >> 16
                if info.flag_bits & 1 or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)):
                    fail("拒绝加密成员或特殊文件")
                if folded in seen:
                    fail("包路径重复")
                seen.add(folded)
                if info.file_size > MAX_MEMBER or info.file_size < 0:
                    fail("单个成员超过 16 MiB")
                total += info.file_size
                if total > MAX_EXPANDED:
                    fail("展开内容超过 64 MiB")
            file_names = {i.orig_filename.casefold() for i in infos if not i.is_dir()}
            for name in seen:
                parts = name.split("/")
                if any("/".join(parts[:i]) in file_names for i in range(1, len(parts))):
                    fail("文件与目录路径冲突")
            for info in infos:
                with archive.open(info) as member:
                    blob = member.read(MAX_MEMBER + 1)
                if len(blob) != info.file_size or len(blob) > MAX_MEMBER:
                    fail("成员大小不一致")
                if info.is_dir():
                    if blob:
                        fail("目录含内容")
                else:
                    files[info.orig_filename] = blob
    except (zipfile.BadZipFile, zipfile.LargeZipFile, NotImplementedError, RuntimeError, EOFError, ValueError, OSError, zlib.error, lzma.LZMAError) as exc:
        fail(f"无效 ZIP：{exc}")
    return files


@dataclass
class ParsedPackage:
    files: dict[str, bytes]
    manifest: dict
    case: dict
    vessels: list
    tracks: dict[str, list]
    observations: list
    evidence: list
    audit_lines: list[str]
    custody_lines: list[str]
    summary: dict
    hfacs_archive: Any = None
    working_archive: Any = None


def parse_package(data: bytes, *, validated_hfacs=None) -> ParsedPackage:
    files = read_bounded(data)
    required = {"manifest.json", "case.json", "case.ext.json", "vessels.json", "evidence/index.json",
                "audit/audit.jsonl", "audit/custody.jsonl", "access-policy.json"}
    if required - files.keys():
        fail("缺少必要文件：" + ", ".join(sorted(required - files.keys())))
    def load(path):
        return strict_json(files[path])
    manifest = load("manifest.json")
    if not isinstance(manifest, dict) or manifest.get("packageFormat") != PACKAGE_FORMAT or manifest.get("packageVersion") not in (PACKAGE_VERSION, "1.1.0", "1.2.0", "1.3.0", "1.4.0"):
        fail("不支持的包格式或版本")
    if set(manifest) != {"packageFormat", "packageVersion", "caseId", "createdAtUtc", "lastModifiedAtUtc", "generatorVersion", "files"}:
        fail("未知或不完整清单字段")
    for field in ("createdAtUtc", "lastModifiedAtUtc"):
        if not isinstance(manifest[field], str) or not contracts.validator("case").format_checker.conforms(manifest[field], "date-time"):
            fail("清单时间无效")
    from ..hfacs_drafts.archive import PATH as hfacs_path, ValidatedArchive, validate as validate_hfacs
    has_hfacs = hfacs_path in files
    from ..working_records_archive.validation import PATH as working_path
    has_working = working_path in files
    from ..working_records_archive import timeline as timeline_archive
    has_timeline = timeline_archive.PATH in files
    if (manifest['packageVersion']=='1.4.0') != has_timeline:
        fail('外层版本与时间线扩展不匹配')
    if (manifest['packageVersion'] in ('1.2.0','1.3.0','1.4.0')) != has_working:
        fail('外层版本与工作记录扩展不匹配')
    if manifest['packageVersion'] not in ('1.2.0','1.3.0','1.4.0') and ((manifest["packageVersion"] == "1.1.0") != has_hfacs):
        fail("外层版本与HFACS扩展不匹配")
    from ..track_history.validation import markers
    if markers(files)and manifest['packageVersion']!='1.3.0':
        raise problem(422, 'PACKAGE_INTAKE_INVALID', '旧包包含W10凭证，尚不支持安全迁移；原包未修改',
                      {'reason': 'TRACK_HISTORY_MIGRATION_UNSUPPORTED'})
    entries = manifest.get("files")
    if not isinstance(entries, list):
        fail("缺少完整清单")
    listed = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"relativePath", "role", "sizeBytes", "sha256"}:
            fail("无效清单条目")
        path = safe_path(entry["relativePath"])
        if path in listed or path == "manifest.json" or path not in files:
            fail("清单重复或引用缺失成员")
        if entry["role"] != infer_role(path):
            fail("无效文件角色")
        listed.add(path)
        blob = files[path]
        if type(entry["sizeBytes"]) is not int or entry["sizeBytes"] != len(blob) or entry["sha256"] != hashlib.sha256(blob).hexdigest():
            fail("清单大小或 SHA-256 不匹配")
    if listed != files.keys() - {"manifest.json"}:
        fail("存在清单外文件")
    case = load("case.json")
    ext = load("case.ext.json")
    if not isinstance(case, dict) or set(case) != set(CASE_FIELDS) or not isinstance(ext, dict) or set(ext) - set(CASE_EXT_FIELDS):
        fail("案件基础字段必须完整且无未知字段")
    case = {**case, **ext}
    contracts.validate("case", case)
    if case["schemaVersion"] != "1.0.0" or manifest.get("caseId") != case["caseId"]:
        fail("案件标识或 schemaVersion 不匹配")
    cid = case["caseId"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", cid):
        fail("不安全案件标识")
    if not -840 <= case["displayTimeZoneOffsetMinutes"] <= 840 or case.get("durationSec", 0) < 0:
        fail("案件时区或时长无效")
    if load("access-policy.json") != default_policy():
        fail("仅支持默认权限策略")
    vessels = load("vessels.json")
    evidence = load("evidence/index.json")
    observations = load("environment/observations.json") if "environment/observations.json" in files else []
    validate_observations(observations, cid)
    def index(items, schema, key):
        if not isinstance(items, list):
            fail(f"{schema} 必须为数组")
        out = {}
        for item in items:
            contracts.validate(schema, item)
            ident = item[key]
            if item.get("caseId") != cid or ident in out:
                fail(f"{schema} 案件引用错误或标识重复")
            out[ident] = item
        return out
    vi = index(vessels, "vessel", "vesselId")
    ei = index(evidence, "evidence-item", "evidenceId")
    for vid in vi:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", vid):
            fail("不安全船舶标识")
    hfacs_archive = None
    if has_hfacs:
        if validated_hfacs is not None:
            if not isinstance(validated_hfacs, ValidatedArchive) or validated_hfacs.raw != files[hfacs_path] or validated_hfacs.data["caseId"] != cid:
                fail("HFACS验证状态不匹配")
            hfacs_archive = validated_hfacs
        else:
            hfacs_archive = validate_hfacs(files[hfacs_path], cid, set(ei))
    allowed = required | {"environment/observations.json", "audit/agent.jsonl"}
    if has_hfacs: allowed.add(hfacs_path)
    if has_timeline: allowed.add(timeline_archive.PATH)
    if has_working:
        allowed.add(working_path)
        wdata = strict_json(files[working_path])
        if not isinstance(wdata, dict) or not isinstance(wdata.get('historicalArtifacts'), list): fail('历史文件索引无效')
        for a in wdata['historicalArtifacts']:
            if not isinstance(a, dict) or not isinstance(a.get('relativePath'), str): fail('历史文件索引无效')
            allowed.add(a['relativePath'])
    empty_sections = {"analysis/timeline.json": {"events": []}, "analysis/time-alignment.json": {"conflicts": []},
                      "analysis/colreg.json": {}, "recommendations.json": [], "consultation/rounds.json": [], "agents/drafts.json": []}
    for path, empty in empty_sections.items():
        if path in files:
            if path=='analysis/timeline.json' and has_timeline:
                allowed.add(path)
                continue # checked against authoritative rows after full working validation
            if load(path) != empty:
                fail(f"暂不支持非空业务内容：{path}")
            allowed.add(path)
    tracks = {}
    for path in files:
        if path.startswith("derived/tracks/") and path.endswith(".track.json"):
            doc = load(path)
            if not isinstance(doc, dict) or set(doc) != {"vesselId", "points"} or not isinstance(doc["vesselId"], str) or doc["vesselId"] not in vi or not isinstance(doc["points"], list):
                fail("航迹结构或船舶引用错误")
            vid = doc["vesselId"]
            if path != f"derived/tracks/{vid}.track.json" or vid in tracks:
                fail("航迹文件与船舶标识不一致")
            last = -math.inf
            for point in doc["points"]:
                contracts.validate("track-point", point)
                if point["vesselId"] != vid or point["timeSec"] <= last or not -90 <= point["latDeg"] <= 90 or not -180 <= point["lonDeg"] <= 180:
                    fail("航迹引用、坐标或时序错误")
                epoch = datetime.fromisoformat(case["caseEpochUtc"].replace("Z", "+00:00"))
                stamp = datetime.fromisoformat(point["utc"].replace("Z", "+00:00"))
                if abs((stamp - epoch).total_seconds() - point["timeSec"]) > 1e-6:
                    fail("航迹 UTC 与案件纪元偏移不一致")
                last = point["timeSec"]
            tracks[vid] = doc["points"]
            allowed.add(path)
    used_paths = set()
    for item in evidence:
        path = item.get("relativePath", "")
        if path:
            safe_path(path)
            if not path.startswith(("raw/", "evidence/")) or path in allowed or path.endswith("/.keep") or path in used_paths:
                fail("证据路径冲突或不受支持")
            if path not in files or hashlib.sha256(files[path]).hexdigest() != item["sha256"]:
                fail("证据原件缺失或登记哈希不匹配")
            used_paths.add(path)
    allowed |= used_paths
    for path, blob in files.items():
        if path not in allowed and not (path in {directory + "/.keep" for directory in REQUIRED_DIRS} and blob == b""):
            fail(f"不支持的包成员：{path}")
    def chain(path, custody=False):
        try:
            text = files[path].decode("utf-8")
            if any(c in text for c in "\r\v\f\x1c\x1d\x1e\x85\u2028\u2029"):
                fail("本切片审计链仅支持 LF 换行，拒绝可能改变原行的分隔符")
            lines = text.split("\n")
        except UnicodeError:
            fail("审计链不是 UTF-8")
        if lines[-1] == "":
            lines.pop()
        prev = "0" * 64
        registered = set()
        current_hash = {}
        for seq, line in enumerate(lines, 1):
            rec = strict_json(line.encode("utf-8"))
            if not isinstance(rec, dict) or rec.get("prev") != prev or type(rec.get("seq")) is not int or rec["seq"] != seq:
                fail("审计/保管链断裂或缺少序号")
            if any(not isinstance(rec.get(k), str) for k in ("utc", "operator", "action", "category", "command", "before", "after")):
                fail("审计/保管字段缺失或类型错误")
            if not contracts.validator("case").format_checker.conforms(rec["utc"], "date-time"):
                fail("审计时间无效")
            for field in ("role", "entity_type", "entity_id", "detail", "sha256", "result", "case_id", "caseId"):
                if field in rec and not isinstance(rec[field], str):
                    fail("审计扩展字段类型错误")
            if rec.get("case_id", cid) != cid or rec.get("caseId", cid) != cid:
                fail("审计/保管链案件引用错误")
            if custody:
                eid = rec.get("evidence_id")
                if not isinstance(eid, str) or eid not in ei or rec.get("action") not in {"custody.register", "custody.access", "custody.change", "custody.verify", "custody.review"}:
                    fail("保管链证据引用或动作错误")
                if rec["action"] == "custody.register":
                    if eid in registered:
                        fail("重复证据登记")
                    registered.add(eid)
                    current_hash[eid] = ei[eid]["sha256"]
                    for src, dest in (("sha256", "sha256"), ("path", "relativePath"), ("title", "title"), ("source", "source"), ("extracted_by", "extractedBy"), ("extracted_utc", "extractedUtc")):
                        if rec.get(src, "") != ei[eid].get(dest, ""):
                            fail("保管链登记与证据索引不一致")
                    if rec.get("confidentiality", "Normal") != ei[eid]["confidentiality"]:
                        fail("证据保密等级不一致")
                elif eid not in registered:
                    fail("保管事件早于登记")
                if rec["action"] in ("custody.change", "custody.verify"):
                    if rec.get("before") != current_hash[eid] or not re.fullmatch(r"[0-9a-f]{64}", rec.get("sha256", "")):
                        fail("保管链哈希状态不一致")
                    if rec["action"] == "custody.change":
                        current_hash[eid] = rec["sha256"]
                    elif rec.get("result") not in ("match", "mismatch") or (rec["result"] == "match") != (rec["sha256"] == current_hash[eid]):
                        fail("保管链校验结果矛盾")
                if rec["action"] == "custody.review" and rec.get("result") not in ("needs_review", "cleared"):
                    fail("无效保管链复核状态")
            prev = hashlib.sha256(line.encode("utf-8")).hexdigest()
        if custody and any(current_hash[eid] != ei[eid]["sha256"] for eid in current_hash):
            fail("暂不支持已替换原件的证据版本历史")
        if custody and registered != ei.keys():
            fail("证据缺少登记来源链")
        return lines
    audit_lines = chain("audit/audit.jsonl")
    custody_lines = chain("audit/custody.jsonl", True)
    if "audit/agent.jsonl" in files:
        expected = "".join(line + "\n" for line in audit_lines if strict_json(line.encode()).get("category") == "Agent").encode()
        if files["audit/agent.jsonl"] != expected:
            fail("智能体审计副本与主审计不一致")
    working_archive = None
    from ..evidence_intake.parser import PREFIX as intake_prefix
    if not has_working and any(intake_prefix in line for line in custody_lines):
        fail('旧包包含证据导入凭证但无历史禁用索引，不能恢复为活跃请求')
    if has_working:
        from ..working_records_archive.validation import validate as validate_working
        with zipfile.ZipFile(io.BytesIO(data)) as outer_zip:
            outer_members = len(outer_zip.infolist())
        working_archive = validate_working(files[working_path], cid, files, ei, audit_lines, custody_lines, outer_member_count=outer_members)
        if (manifest['packageVersion']=='1.3.0')!=(working_archive.data['version']==2):fail('外层版本与航迹历史扩展不匹配')
        if has_timeline: timeline_archive.validate(files,cid)
    summary = {"caseId": cid, "title": case["title"], "files": len(files), "vessels": len(vessels),
               "trackPoints": sum(map(len, tracks.values())), "observations": len(observations), "evidence": len(evidence),
               "auditEvents": len(audit_lines), "custodyEvents": len(custody_lines)}
    return ParsedPackage(files, manifest, case, vessels, tracks, observations, evidence, audit_lines, custody_lines, summary, hfacs_archive, working_archive)
