""".mcase 导入/导出（兼容 Unity 侧 Mcis.Data.CasePackage：ZIP + manifest.json + 小写 SHA-256）。

导出布局 = ARCHITECTURE §11.1 + §15.4（只增不改）：
  manifest.json / case.json（CaseJson 字段与顺序）/ case.ext.json（服务扩展字段）/ vessels.json
  derived/tracks/<vesselId>.track.json / evidence/index.json / raw/** 与 evidence/** 原件
  analysis/timeline.json / analysis/time-alignment.json / analysis/colreg.json
  testimony/IR-xx.json / recommendations.json / consultation/rounds.json / agents/drafts.json / access-policy.json
  audit/audit.jsonl / audit/custody.jsonl（C# CustodyEvent 行格式）/ audit/agent.jsonl
"""
from __future__ import annotations

import io
import json
import zipfile
import zlib
import lzma
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import __version__
from ..agents.models import AgentDraftRow
from ..audit import service as audit
from ..audit.models import AuditEventRow
from ..cases.models import CaseRow, TrackPointRow, VesselRow
from ..colreg.models import ColregAnalysisRow
from ..common.context import problem
from ..common.csjson import quote, sha256_hex
from ..common.timeutil import iso, now_utc, parse_iso
from ..db import get_doc, list_docs, put_doc
from ..environment.models import EnvironmentObservationRow
from ..environment.service import validate_observations
from ..evidence.models import CustodyEventRow, EvidenceRow
from ..evidence import service as evidence_service
from ..interviews.models import InterviewRow
from ..recommendations.models import ConsultationRoundRow, RecommendationRow
from ..redaction.models import AccessPolicyRow
from ..redaction.policy import default_policy
from ..timeline.models import ConflictRow, TimelineEventRow

PACKAGE_FORMAT = "MCIS-MCASE"
PACKAGE_VERSION = "1.0.0"
GENERATOR = f"MCIS-Service-{__version__}"
REQUIRED_DIRS = ["raw", "raw/ais", "raw/charts", "derived", "derived/tracks", "derived/cpa", "derived/damage_bake",
                 "evidence", "audit", "exports", "thumbnails"]
CASE_FIELDS = ["caseId", "schemaVersion", "title", "accidentCode", "accidentType", "accidentGrade", "incidentTimeUtc",
               "caseEpochUtc", "displayTimeZoneOffsetMinutes", "incidentLocation", "seaLevelOffsetM", "leadInvestigator",
               "agencyName", "isFictionalDemo", "summaryNotes"]
CASE_EXT_FIELDS = ["durationSec", "placeName"]


def _num(v: float | int) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    return repr(float(v))


def case_json(c: dict[str, Any]) -> str:
    """与 C# CaseJson.ToJson 相同的键顺序与缩进。"""
    loc = c.get("incidentLocation", {})
    L = ["{",
         f'  "caseId": {quote(c["caseId"])},',
         f'  "schemaVersion": {quote(c.get("schemaVersion", "1.0.0"))},',
         f'  "title": {quote(c.get("title", ""))},',
         f'  "accidentCode": {quote(c.get("accidentCode", ""))},',
         f'  "accidentType": {quote(c.get("accidentType", ""))},',
         f'  "accidentGrade": {quote(c.get("accidentGrade", ""))},',
         f'  "incidentTimeUtc": {quote(iso(parse_iso(c["incidentTimeUtc"])))},',
         f'  "caseEpochUtc": {quote(iso(parse_iso(c["caseEpochUtc"])))},',
         f'  "displayTimeZoneOffsetMinutes": {int(c.get("displayTimeZoneOffsetMinutes", 480))},',
         '  "incidentLocation": {',
         f'    "lonDeg": {_num(loc.get("lonDeg", 0.0))},',
         f'    "latDeg": {_num(loc.get("latDeg", 0.0))},',
         f'    "heightM": {_num(loc.get("heightM", 0.0))}',
         "  },",
         f'  "seaLevelOffsetM": {_num(c.get("seaLevelOffsetM", 0.0))},',
         f'  "leadInvestigator": {quote(c.get("leadInvestigator", ""))},',
         f'  "agencyName": {quote(c.get("agencyName", ""))},',
         f'  "isFictionalDemo": {"true" if c.get("isFictionalDemo") else "false"},',
         f'  "summaryNotes": {quote(c.get("summaryNotes", ""))}',
         "}"]
    return "\n".join(L) + "\n"


def infer_role(rel: str) -> str:
    """与 C# PackageManifest.InferRole 一致。"""
    n = rel.replace("\\", "/")
    low = n.lower()
    if low == "case.json":
        return "CaseDefinition"
    if n.startswith("raw/") or n == "raw" or low.startswith("evidence/"):
        return "RawEvidence"
    if low.startswith("audit/"):
        return "Audit"
    if low.startswith("exports/"):
        return "Export"
    if low.startswith("thumbnails/"):
        return "Thumbnail"
    return "Derived"


def manifest_json(case_id: str, files: dict[str, bytes], created: str, package_version: str = PACKAGE_VERSION) -> str:
    """与 C# PackageManifest.ToJson 相同的格式。"""
    L = ["{",
         f'  "packageFormat": {quote(PACKAGE_FORMAT)},',
         f'  "packageVersion": {quote(package_version)},',
         f'  "caseId": {quote(case_id)},',
         f'  "createdAtUtc": {quote(created)},',
         f'  "lastModifiedAtUtc": {quote(iso(now_utc()))},',
         f'  "generatorVersion": {quote(GENERATOR)},',
         '  "files": [']
    names = sorted(files)
    for i, rel in enumerate(names):
        data = files[rel]
        L += ["    {",
              f'      "relativePath": {quote(rel)},',
              f'      "role": {quote(infer_role(rel))},',
              f'      "sizeBytes": {len(data)},',
              f'      "sha256": {quote(sha256_hex(data))}',
              "    }" + ("," if i < len(names) - 1 else "")]
    L += ["  ]", "}"]
    return "\n".join(L) + "\n"


def _j(obj: Any) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _lines(lines: list[str]) -> bytes:
    return ("".join(l + "\n" for l in lines)).encode("utf-8")


def build_files(s: Session, blob_root: Path, case_id: str) -> dict[str, bytes]:
    case = get_doc(s, CaseRow, case_id, case_id)
    files: dict[str, bytes] = {}
    for d in REQUIRED_DIRS:
        files[f"{d}/.keep"] = b""
    files["case.json"] = case_json(case).encode("utf-8")
    files["case.ext.json"] = _j({k: case[k] for k in CASE_EXT_FIELDS if k in case})
    files["vessels.json"] = _j(list_docs(s, VesselRow, case_id))
    observations = list_docs(s, EnvironmentObservationRow, case_id)
    if observations:
        files["environment/observations.json"] = _j(observations)
    pts = s.scalars(select(TrackPointRow).where(TrackPointRow.case_id == case_id).order_by(TrackPointRow.vessel_id, TrackPointRow.time_sec)).all()
    by_v: dict[str, list] = {}
    for p in pts:
        by_v.setdefault(p.vessel_id, []).append(p.doc)
    for vid, lst in by_v.items():
        files[f"derived/tracks/{vid}.track.json"] = _j({"vesselId": vid, "points": lst})
    ev = list_docs(s, EvidenceRow, case_id)
    files["evidence/index.json"] = _j(ev)
    for item in ev:
        rel = item.get("relativePath") or ""
        if rel:
            p = evidence_service.blob_path(blob_root, case_id, rel)
            if p.exists():
                files[rel] = p.read_bytes()
    files["analysis/timeline.json"] = _j({"events": list_docs(s, TimelineEventRow, case_id)})
    files["analysis/time-alignment.json"] = _j({"conflicts": list_docs(s, ConflictRow, case_id)})
    col = get_doc(s, ColregAnalysisRow, case_id, "current")
    if col:
        files["analysis/colreg.json"] = _j(col)
    for iv in list_docs(s, InterviewRow, case_id):
        files[f"testimony/{iv['recordId']}.json"] = _j(iv)
    files["recommendations.json"] = _j(list_docs(s, RecommendationRow, case_id))
    files["consultation/rounds.json"] = _j(list_docs(s, ConsultationRoundRow, case_id))
    files["agents/drafts.json"] = _j(list_docs(s, AgentDraftRow, case_id))
    files["access-policy.json"] = _j(get_doc(s, AccessPolicyRow, case_id, "policy") or default_policy())
    files["audit/custody.jsonl"] = _lines([r.line for r in evidence_service.custody_events(s, case_id)])
    rows = s.scalars(select(AuditEventRow).where(AuditEventRow.case_id == case_id).order_by(AuditEventRow.seq)).all()
    files["audit/audit.jsonl"] = _lines([r.line for r in rows])
    files["audit/agent.jsonl"] = _lines([r.line for r in rows if r.category == "Agent"])
    return files


def export_case(s: Session, blob_root: Path, case_id: str, operator: str, role: str) -> bytes:
    from ..manual_interviews.models import InterviewRequestReceiptRow
    from ..interviews.access import begin, require_content
    begin(s)
    if s.scalar(select(InterviewRequestReceiptRow.request_id).where(InterviewRequestReceiptRow.case_id == case_id).limit(1)) is not None:
        require_content(s, case_id, role)
        raise problem(409, 'INTERVIEW_RECEIPTS_BACKUP_UNSUPPORTED', '此案含人工录入回执，旧案件包不能完整备份，未导出')
    from ..reports.access import protect_package
    protect_package(s, case_id, role)
    from ..interviews.access import protect_package as protect_interviews
    protect_interviews(s, case_id, role)
    # Refuse known incomplete backups only after full-content/source authorization.
    # Existing serializers omit reports/snapshots and import rejects testimony.
    from ..reports.models import ReportRow, ReportAuditRow
    from ..reports.access import report_event
    from ..interviews.access import event_related
    unsupported = any(s.scalar(select(model.id).where(model.case_id == case_id).limit(1)) is not None
                      for model in (InterviewRow, ReportRow, ReportAuditRow))
    if not unsupported:
        unsupported = any(report_event(audit.to_doc(event)) or event_related(audit.to_doc(event))
                          for event in s.scalars(select(AuditEventRow).where(AuditEventRow.case_id == case_id)))
    if unsupported:
        raise problem(409, 'ARCHIVE_RESTORE_UNSUPPORTED', '此案含当前案件包不能完整恢复的笔录、报告或相关历史，未导出')
    from ..hfacs_drafts import archive as hfacs_archive
    from ..hfacs_drafts.router import PreviewError
    from ..package_intake.parser import parse_package
    row = s.scalars(select(CaseRow).where(CaseRow.case_id == case_id)).first()
    if row is None:
        raise problem(404, "CASE_NOT_FOUND", f"案件不存在：{case_id}")
    try: extension = hfacs_archive.build(s, case_id, role)
    except PreviewError as exc: raise problem(exc.status, exc.code, exc.message)
    def assemble():
        files = build_files(s, blob_root, case_id)
        if extension is not None: files[hfacs_archive.PATH] = extension.raw
        files["manifest.json"] = manifest_json(case_id, files, iso(parse_iso(row.created_utc)),
                                                "1.1.0" if extension else "1.0.0").encode("utf-8")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for rel in sorted(files): z.writestr(rel, files[rel])
        result = buf.getvalue()
        if extension is not None: parse_package(result, validated_hfacs=extension)
        return result
    if extension is not None: assemble()
    audit.append(s, case_id=case_id, operator=operator, role=role, action="package.export", category="Package",
                 command=f"导出案件包 {case_id}.mcase", after=GENERATOR, entity_type="case", entity_id=case_id)
    return assemble()


# ---------------- 导入 ----------------

def _zip_member_name(info: zipfile.ZipInfo) -> tuple[str, bool]:
    # ZipInfo truncates filename at NUL; inspect the original before normalization.
    original = info.orig_filename
    name = original.replace("\\", "/")
    directory = name.endswith("/")
    components = name[:-1].split("/") if directory else name.split("/")
    if ("\x00" in original or name.startswith("/")
            or any(part in ("", ".", "..") or ":" in part for part in components)):
        raise problem(422, "BAD_PACKAGE", "案件包包含非法路径")
    return name, directory


def read_zip(data: bytes) -> dict[str, bytes]:
    """Decode an unambiguous ZIP in memory; do not extract archive paths.

    Backslashes remain supported for Unity packages. Case-insensitive collisions
    are rejected because integrity verification already uses that comparison.
    This decoder is not an upload/decompression resource budget.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            members = []
            seen = set()
            for info in z.infolist():
                name, directory = _zip_member_name(info)
                key = name.rstrip("/").lower()
                if key in seen:
                    raise problem(422, "BAD_PACKAGE", "案件包包含重复或歧义路径")
                seen.add(key)
                if info.flag_bits & 1:
                    raise problem(422, "BAD_PACKAGE", "不支持加密案件包")
                members.append((info, name, directory))
            file_keys = {name.lower() for _, name, directory in members if not directory}
            for _, name, _ in members:
                parts = name.rstrip("/").lower().split("/")
                for end in range(1, len(parts)):
                    if "/".join(parts[:end]) in file_keys:
                        raise problem(422, "BAD_PACKAGE", "案件包包含文件与目录路径冲突")
            return {name: z.read(info) for info, name, directory in members if not directory}
    except (zipfile.BadZipFile, zipfile.LargeZipFile, NotImplementedError,
            RuntimeError, EOFError, ValueError, OSError, zlib.error, lzma.LZMAError) as e:
        # Corrupt CRC/compression/header errors must not escape as HTTP 500 or
        # expose parser internals. HTTPException from validation is not caught.
        raise problem(422, "BAD_PACKAGE", "不是有效或受支持的 .mcase（ZIP）文件") from e


def verify_files(files: dict[str, bytes]) -> dict[str, Any]:
    """与 C# IntegrityChecker.VerifyWorkspace 相同的判定：缺失或篡改即无效；多余文件只报告。"""
    if "manifest.json" not in files:
        return {"isValid": False, "tamperedFiles": [], "missingFiles": ["manifest.json"], "extraFiles": []}
    m = json.loads(files["manifest.json"].decode("utf-8-sig"))
    listed = {}
    for f in m.get("files", []):
        listed[f["relativePath"].replace("\\", "/")] = f
    lower = {k.lower(): k for k in files}
    tampered, missing = [], []
    for rel, f in listed.items():
        real = files.get(rel) if rel in files else files.get(lower.get(rel.lower(), ""), None)
        if real is None:
            missing.append(rel)
        elif sha256_hex(real).lower() != (f.get("sha256") or "").lower():
            tampered.append(rel)
    listed_low = {k.lower() for k in listed}
    extra = [k for k in files if k != "manifest.json" and k.lower() not in listed_low]
    return {"isValid": not tampered and not missing, "tamperedFiles": tampered, "missingFiles": missing,
            "extraFiles": extra, "caseId": m.get("caseId"), "packageFormat": m.get("packageFormat"),
            "createdAtUtc": m.get("createdAtUtc"),
            "generatorVersion": m.get("generatorVersion")}


def _load_json(files: dict[str, bytes], rel: str, default: Any) -> Any:
    return json.loads(files[rel].decode("utf-8-sig")) if rel in files else default


def import_case(s: Session, blob_root: Path, data: bytes, operator: str, role: str, *, validated_hfacs=None) -> dict[str, Any]:
    files = read_zip(data)
    from ..interviews.access import draft_related, event_related
    for name, raw in files.items():
        if name.casefold() in ('audit/audit.jsonl', 'audit/agent.jsonl'):
            try: lines = raw.decode('utf-8-sig').splitlines()
            except UnicodeError: raise problem(422, 'BAD_PACKAGE', '审计格式无效')
            if any(event_related({'line': line}) for line in lines if line.strip()):
                raise problem(422, 'INTERVIEW_IMPORT_UNSUPPORTED', '此旧入口不支持恢复笔录或未分类智能体审计')
            for line in lines:
                if not line.strip(): continue
                event=json.loads(line)
                if event.get('category') == 'Agent':
                    try: incoming=json.loads(files.get('agents/drafts.json',b'[]'))
                    except (ValueError,UnicodeError): incoming=[]
                    matches=[d for d in incoming if isinstance(d,dict) and d.get('draftId')==event.get('entity_id',event.get('entityId'))] if isinstance(incoming,list) and event.get('entity_type',event.get('entityType'))=='agentDraft' else []
                    if len(matches)!=1 or draft_related(matches[0]):
                        raise problem(422, 'INTERVIEW_IMPORT_UNSUPPORTED', '此旧入口不支持恢复未分类智能体原文审计')
    if any(name.casefold().startswith('testimony/') and name.casefold().endswith('.json') for name in files):
        raise problem(422, 'INTERVIEW_IMPORT_UNSUPPORTED', '此旧入口不支持恢复笔录及其访问策略')
    for name, raw in files.items():
        if name.casefold() == 'agents/drafts.json':
            try: drafts = json.loads(raw.decode('utf-8-sig'))
            except (ValueError, UnicodeError): raise problem(422, 'BAD_PACKAGE', '草稿格式无效')
            if not isinstance(drafts, list) or any(not isinstance(d,dict) or draft_related(d) for d in drafts):
                raise problem(422, 'INTERVIEW_IMPORT_UNSUPPORTED', '此旧入口不支持恢复笔录派生草稿')
    from ..hfacs_drafts import archive as hfacs_archive
    namespace = [name for name in files if name.casefold() == "hfacs" or name.casefold().startswith("hfacs/")]
    try:
        manifest = json.loads(files.get("manifest.json", b"{}").decode("utf-8-sig"))
        if not isinstance(manifest, dict): raise ValueError("manifest shape")
    except (ValueError, UnicodeError):
        raise problem(422, "BAD_PACKAGE", "案件包清单无效")
    if namespace or manifest.get("packageVersion") == "1.1.0":
        if (namespace != [hfacs_archive.PATH] or manifest.get("packageVersion") != "1.1.0"
                or not isinstance(validated_hfacs, hfacs_archive.ValidatedArchive)
                or validated_hfacs.raw != files[hfacs_archive.PATH]):
            raise problem(422, "HFACS_IMPORT_ENTRY", "HFACS扩展只能通过本版本受限导入预检与确认恢复，旧入口不接受")
    elif manifest.get("packageVersion", PACKAGE_VERSION) != PACKAGE_VERSION:
        raise problem(422, "BAD_PACKAGE", "不支持的案件包版本")
    report = verify_files(files)
    if not report["isValid"]:
        raise problem(422, "INTEGRITY_FAILED", "案件包完整性校验失败", report)
    if report.get("packageFormat") not in (None, PACKAGE_FORMAT):
        raise problem(422, "BAD_PACKAGE", f"未知包格式 {report.get('packageFormat')}")
    if "case.json" not in files:
        raise problem(422, "BAD_PACKAGE", "案件包缺少 case.json")
    raw_case = json.loads(files["case.json"].decode("utf-8-sig"))
    case = {k: raw_case[k] for k in CASE_FIELDS if k in raw_case}
    case.update(_load_json(files, "case.ext.json", {}))
    # 缺省值与 C# CaseDefinition 默认一致（Unity 侧最小包可能只写部分字段）
    created = report.get("createdAtUtc") or "1970-01-01T00:00:00Z"
    case.setdefault("schemaVersion", "1.0.0")
    case.setdefault("title", case.get("caseId", ""))
    case.setdefault("accidentType", "")
    case.setdefault("incidentTimeUtc", case.get("caseEpochUtc", created))
    case.setdefault("caseEpochUtc", case["incidentTimeUtc"])
    case.setdefault("displayTimeZoneOffsetMinutes", 480)
    case.setdefault("incidentLocation", {"lonDeg": 0.0, "latDeg": 0.0, "heightM": 0.0})
    case.setdefault("isFictionalDemo", False)
    for k in ("incidentTimeUtc", "caseEpochUtc"):
        case[k] = iso(parse_iso(case[k]))
    case_id = case["caseId"]
    if s.scalars(select(CaseRow).where(CaseRow.case_id == case_id)).first():
        raise problem(409, "CASE_EXISTS", f"案件已存在：{case_id}（请先换库或改名）")

    # Validate optional W9.2 extension before any SQL/blob write. Legacy absence is empty.
    env_path = next((k for k in files if k.lower() == "environment/observations.json"), None)
    observations = []
    if env_path is not None:
        if env_path in report["extraFiles"]:
            raise problem(422, "BAD_PACKAGE", "环境记录必须包含在完整性清单中")
        try:
            observations = _load_json(files, env_path, [])
        except (ValueError, UnicodeError):
            raise problem(422, "BAD_PACKAGE", "环境记录不是有效 JSON")
        validate_observations(observations, case_id)

    # 审计链与保管链先校验再落库
    audit_lines = [l for l in files.get("audit/audit.jsonl", b"").decode("utf-8").splitlines() if l.strip()]
    custody_lines = [l for l in files.get("audit/custody.jsonl", b"").decode("utf-8").splitlines() if l.strip()]
    for name, lines in (("audit.jsonl", audit_lines), ("custody.jsonl", custody_lines)):
        chk = audit.verify_chain(lines)
        if not chk["valid"]:
            raise problem(422, "CHAIN_BROKEN", f"{name} 哈希链断裂", chk)

    put_doc(s, CaseRow, case_id, case_id, case)
    for observation in observations:
        put_doc(s, EnvironmentObservationRow, case_id, observation["observationId"], observation)
    for v in _load_json(files, "vessels.json", []):
        put_doc(s, VesselRow, case_id, v["vesselId"], v)
    for rel, blob in files.items():
        if rel.startswith("derived/tracks/") and rel.endswith(".track.json"):
            t = json.loads(blob.decode("utf-8"))
            for p in t.get("points", []):
                s.add(TrackPointRow(case_id=case_id, vessel_id=t["vesselId"], time_sec=p["timeSec"], doc=p))
    ev_index = _load_json(files, "evidence/index.json", [])
    if not ev_index:
        # Unity 侧包没有 evidence/index.json：从 custody.jsonl 的 Register 行还原登记快照
        for line in custody_lines:
            rec = json.loads(line)
            if rec.get("action") == "custody.register":
                ev_index.append({"evidenceId": rec["evidence_id"], "caseId": rec.get("case_id") or case_id,
                                 "title": rec.get("title", ""), "source": rec.get("source", ""),
                                 "extractedBy": rec.get("extracted_by", ""), "extractedUtc": rec.get("extracted_utc", ""),
                                 "sha256": rec.get("sha256", ""), "relativePath": rec.get("path", ""),
                                 "confidentiality": rec.get("confidentiality", "Normal"), "category": "Other", "note": ""})
    for item in ev_index:
        put_doc(s, EvidenceRow, case_id, item["evidenceId"], item)
    for rel, blob in files.items():
        if (rel.startswith("raw/") or rel.startswith("evidence/")) and not rel.endswith("/.keep") and rel != "evidence/index.json":
            p = evidence_service.blob_path(blob_root, case_id, rel)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(blob)
    for e in _load_json(files, "analysis/timeline.json", {}).get("events", []):
        put_doc(s, TimelineEventRow, case_id, e["eventId"], e)
    for c in _load_json(files, "analysis/time-alignment.json", {}).get("conflicts", []):
        put_doc(s, ConflictRow, case_id, c["conflictId"], c)
    if "analysis/colreg.json" in files:
        put_doc(s, ColregAnalysisRow, case_id, "current", _load_json(files, "analysis/colreg.json", {}))
    for rel in files:
        if rel.startswith("testimony/") and rel.endswith(".json"):
            iv = _load_json(files, rel, {})
            put_doc(s, InterviewRow, case_id, iv["recordId"], iv)
    for r in _load_json(files, "recommendations.json", []):
        put_doc(s, RecommendationRow, case_id, r["id"], r)
    for r in _load_json(files, "consultation/rounds.json", []):
        put_doc(s, ConsultationRoundRow, case_id, str(r["roundNo"]), r)
    for d in _load_json(files, "agents/drafts.json", []):
        put_doc(s, AgentDraftRow, case_id, d["draftId"], d)
    if "access-policy.json" in files:
        put_doc(s, AccessPolicyRow, case_id, "policy", _load_json(files, "access-policy.json", {}))

    from ..common.csjson import ZERO_HASH, sha256_utf8
    prev = ZERO_HASH
    for i, line in enumerate(custody_lines):
        rec = json.loads(line)
        kind = evidence_service.KIND_BY_ACTION.get(rec.get("action"), "Access")
        s.add(CustodyEventRow(case_id=case_id, seq=int(rec.get("seq", i + 1)), evidence_id=rec.get("evidence_id", ""), kind=kind,
                              utc=rec.get("utc", ""), operator=rec.get("operator", ""), sha256=rec.get("sha256", ""),
                              previous_sha256=rec.get("before", "") if kind in ("Change", "Verify") else "",
                              detail=rec.get("detail", ""),
                              verify_matched=(rec.get("result") == "match") if kind == "Verify"
                              else (rec.get("result") == "needs_review") if kind == "Review" else None,
                              prev_line_hash=rec.get("prev", prev), line=line))
        prev = sha256_utf8(line)
    prev = ZERO_HASH
    for i, line in enumerate(audit_lines):
        audit.append_raw_line(s, case_id, json.loads(line), line, i + 1, prev)
        prev = sha256_utf8(line)
    if validated_hfacs is not None:
        if validated_hfacs.data["caseId"] != case_id: raise problem(422, "HFACS_IMPORT_CASE", "HFACS案件不一致")
        hfacs_archive.restore(s, validated_hfacs)
    s.flush()
    audit.append(s, case_id=case_id, operator=operator, role=role, action="package.import", category="Package",
                 command=f"导入案件包 {case_id}", after=f"{report.get('generatorVersion')}；文件 {len(files)} 个；额外 {len(report['extraFiles'])} 个",
                 entity_type="case", entity_id=case_id)
    return {"caseId": case_id, "integrity": report, "imported": {
        "evidence": len(ev_index), "custodyEvents": len(custody_lines), "auditEvents": len(audit_lines) + 1}}
