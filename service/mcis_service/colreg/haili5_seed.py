"""海力5 / WAN HAI A17 真实案例播种（W6 避碰规则对照页）。

数据来自公开调查报告 reports/haili5/（Mark 2026-11-11 确认可直接使用真实数据）。
航迹只收录报告给出经纬度的点，不补造位置；同一时刻多源冲突并存（如 A17 在 19:51:15 的航向航速）。
COLREG 分析按 reports/REAL_CASES.md §1.1 与报告条文整理，标注【直接】/【推算】及页码。
本案件 isFictionalDemo=false。仅作技术分析，不作责任认定。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ..audit import service as audit
from ..cases.models import CaseRow, TrackPointRow, VesselRow
from ..colreg.models import ColregAnalysisRow
from ..common.timeutil import iso, sim_to_utc
from ..db import put_doc
from ..evidence import service as ev
from ..evidence.models import EvidenceRow
from ..redaction.models import AccessPolicyRow
from ..redaction.policy import default_policy

CASE_ID = "CASE-2025-HAILI5-WANA17"
# SimTime 0 = 2025-10-25 19:42:00 北京时间（两船相距约 3.5 海里、约定会红灯）【直接 p31】
EPOCH = "2025-10-25T11:42:00Z"
COLLISION_T = 752.0  # 19:54:32
DURATION = 1140.0    # 至 20:01:00（约沉没时刻）
LAT, LON = 22.2785, 113.806833  # 22°16.71′N 113°48.41′E【直接 p26】
SEED_OP = "种子数据（公开报告）"
DISCLAIMER = "仅作安全调查技术分析，不作责任认定。"
SOURCE_ROOT = "reports/haili5/"
TZ = timezone(timedelta(hours=8))

HAILI5 = "vessel_haili5"
A17 = "vessel_wanhai_a17"


def _bj(hhmmss: str) -> datetime:
    h, m, s = (int(x) for x in hhmmss.split(":"))
    return datetime(2025, 10, 25, h, m, s, tzinfo=TZ)


def T(hhmmss: str) -> float:
    return (_bj(hhmmss).astimezone(timezone.utc) - datetime.fromisoformat(EPOCH.replace("Z", "+00:00"))).total_seconds()


def _utc(hhmmss: str) -> str:
    return iso(_bj(hhmmss).astimezone(timezone.utc))


def case_doc() -> dict[str, Any]:
    return {
        "caseId": CASE_ID,
        "schemaVersion": "1.0.0",
        "title": "广州港“10·25”海力5 / WAN HAI A17 碰撞事故",
        "accidentCode": "HAILI5-2025-1025",
        "accidentType": "Collision",
        "accidentGrade": "LessSerious",
        "incidentTimeUtc": _utc("19:54:32"),
        "caseEpochUtc": EPOCH,
        "displayTimeZoneOffsetMinutes": 480,
        "incidentLocation": {"lonDeg": LON, "latDeg": LAT, "heightM": 0.0},
        "seaLevelOffsetM": 0.0,
        "agencyName": "海事调查机关（公开报告）",
        "isFictionalDemo": False,
        "summaryNotes": (
            "真实案例，数据取自公开调查报告 reports/haili5/ 与 reports/REAL_CASES.md。"
            "2025-10-25 19:54:32 北京时间，广州港主航道马友石灯船东北侧，海力5 失电失控后与 WAN HAI A17 碰撞。"
            "航迹仅为报告给出经纬度的样本，不是 AIS 原始记录。仅作技术分析，不作责任认定。"
        ),
        "durationSec": DURATION,
        "placeName": "广州港主航道马友石灯船东北侧",
    }


# 仅收录报告给出经纬度的点。source 标明页码/图号与【直接】。
# A17 在 19:51:15 的两组航向航速（正文 vs 图24）都没有经纬度，不写入航迹表，以免违反 track-point 必填坐标。
TRACKS: list[dict[str, Any]] = [
    # haili5
    {"vesselId": HAILI5, "clock": "19:42:00", "lat": 22.300833, "lon": 113.801167, "cog": 169, "sog": 7.2,
     "source": "【直接】报告正文 p31：19:42 航向 169°、7.2 节，船位 22°18.05′N 113°48.07′E"},
    {"vesselId": HAILI5, "clock": "19:51:15", "lat": 22.283667, "lon": 113.804167, "cog": 169, "sog": 6.5,
     "source": "【直接】报告正文 p31：19:51:15 失电时航向 169°、6.5 节"},
    {"vesselId": HAILI5, "clock": "19:52:52", "lat": 22.281, "lon": 113.804833, "cog": 163, "sog": 5.6,
     "source": "【直接】报告正文 p32：19:52:52 航向 163°、5.6 节"},
    {"vesselId": HAILI5, "clock": "19:53:08", "lat": 22.2807333, "lon": 113.8049333, "cog": 161.0, "sog": 5.6,
     "source": "【直接】报告图18 VTS AIS 框 p23：19:53:08，22°16′50.640″N 113°48′17.760″E，5.6 节 / 161.0°"},
    {"vesselId": HAILI5, "clock": "19:54:32", "lat": 22.279, "lon": 113.806167, "cog": 133, "sog": 4.3,
     "source": "【直接】报告正文 p26：碰撞时刻 AIS 22°16.74′N 113°48.37′E，航向 133°、4.3 节"},
    # WAN HAI A17（仅两点有经纬度）
    {"vesselId": A17, "clock": "19:53:08", "lat": 22.2736183, "lon": 113.8079883, "cog": 347.6, "sog": 9.7,
     "source": "【直接】报告图18 VTS AIS 框 p23：19:53:08，22°16′25.026″N 113°48′28.758″E，9.7 节 / 347.6°"},
    {"vesselId": A17, "clock": "19:54:32", "lat": 22.277667, "lon": 113.807, "cog": 348, "sog": 9.7,
     "source": "【直接】报告正文 p26：碰撞时刻 AIS 22°16.66′N 113°48.42′E，航向 348°、9.7 节"},
]


def track_points() -> list[dict[str, Any]]:
    out = []
    for t in TRACKS:
        sec = T(t["clock"])
        out.append({
            "vesselId": t["vesselId"], "timeSec": sec, "utc": sim_to_utc(EPOCH, sec),
            "latDeg": t["lat"], "lonDeg": t["lon"], "sogKn": t["sog"], "cogDeg": t["cog"],
            "hdgDeg": t["cog"], "rotDegPerMin": None, "provenance": "Measured", "source": t["source"],
        })
    return out


# 证据条目：只登记来源指针和短注，不写入报告正文。
EVIDENCE = [
    ("EV-101", "公开事故调查报告（海力5 / WAN HAI A17）", "交通运输部海事调查公开报告", "调查员 A",
     "raw/report/haili5_public_report.txt", "Document",
     "【直接】来源：reports/haili5/（公开资料，报告全文）。页码以正文页脚为准。"),
    ("EV-102", "图18 广州 VTS 雷达/AIS 框（19:53:08）", "报告图18 / 正文 p23", "调查员 A",
     "evidence/EV-102/fig18_vts_ais.txt", "AIS",
     "【直接】p23 图18：两船瞬时 AIS 船位、航向、航速。不是原始 AIS 记录。"),
    ("EV-103", "图24 事故经过图", "报告图24 / 正文 p36", "调查员 A",
     "evidence/EV-103/fig24_track.txt", "Document",
     "【直接】p36 图24。正文与图24 对 A17 在 19:51:15 的航向航速不一致（348°/9.9 节 vs 346°/9.5 节），两处并存。"),
    ("EV-104", "碰撞时刻与位置认定", "报告正文 p26", "调查员 A",
     "evidence/EV-104/collision_time.txt", "Document",
     "【直接】p26：2025-10-25 19:54:32 北京时间，22°16.71′N 113°48.41′E；碰撞角约 30–40°。"),
    ("EV-105", "海力5 失电经过", "报告正文 p32 / p41", "调查员 A",
     "evidence/EV-105/blackout.txt", "Document",
     "【直接】p32：19:51:15 全船失电、主机停车、舵机失灵；p41：失电后无法显示失控号灯，未第一时间 VHF 播报失控。"),
    ("EV-106", "A17 瞭望与行动认定", "报告正文 p42–43、处理建议 p55", "调查员 A",
     "evidence/EV-106/a17_lookout.txt", "Document",
     "【直接】p42–43、p55：A17 违反 COLREG 第5条及第8条第1款、第5款。"),
]


# 时间带让路/直航结论的证据（W6.1 裁定 6；band 不在 schema 内带 evidenceIds，放版本注解）
BAND_EVIDENCE: dict[str, list[str]] = {
    "HL-B1": ["EV-101", "EV-103"],
    "HL-B2": ["EV-105", "EV-102", "EV-106"],
    "HL-B3": ["EV-106", "EV-104", "EV-103"],
    "HL-B4": ["EV-104", "EV-105"],
}


def _blob(eid: str, title: str, note: str) -> bytes:
    text = (
        f"MCIS PUBLIC-REPORT POINTER {eid}\n"
        f"title: {title}\n"
        f"{note}\n"
        f"path: {SOURCE_ROOT}\n"
        f"This file is a source pointer only; it does not reproduce the report body.\n"
        f"{DISCLAIMER}\n"
    )
    return text.encode("utf-8")


def seed_evidence(s: Session, blob_root: Path) -> None:
    extracted = "2026-11-11T12:00:00Z"
    for eid, title, source, by, rel, cat, note in EVIDENCE:
        data = _blob(eid, title, note)
        sha = ev.write_blob(blob_root, CASE_ID, rel, data, overwrite=True)
        item = {"evidenceId": eid, "caseId": CASE_ID, "title": title, "source": source, "extractedBy": by,
                "extractedUtc": extracted, "sha256": sha, "relativePath": rel, "category": cat,
                "confidentiality": "Normal", "note": note}
        put_doc(s, EvidenceRow, CASE_ID, eid, item)
        ev.append_custody(s, case_id=CASE_ID, evidence_id=eid, kind="Register", operator=by, role="Investigator",
                          sha256=sha, detail="登记公开报告来源指针（非虚构）", item=item, utc=extracted)


def seed_colreg(s: Session) -> None:
    # 时段按 REAL_CASES.md §1.1；时刻为相对 EPOCH（19:42:00）的秒。
    t_blackout, t_detect, t_c, t_end = T("19:51:15"), T("19:52:50"), COLLISION_T, DURATION
    pd, nuc = "PowerDriven", "NotUnderCommand"
    bands = [
        {
            "bandId": "HL-B1", "startTimeSec": 0, "endTimeSec": t_blackout,
            "situation": "NarrowChannel", "inSight": True,
            "giveWayVesselId": None, "standOnVesselId": None,
            "applicableRules": ["R9"],
            "basis": "【直接 p31、p33】19:42 两船相距约 3.5 海里，约定左舷对左舷（会红灯），各靠右；能见度良好、夜间、互见。DCPA 足够时亦可视为无碰撞危险。",
            "dangerStage": "None", "doubt": False, "doubtReason": None,
            "vesselStatus": {HAILI5: pd, A17: pd},
        },
        {
            "bandId": "HL-B2", "startTimeSec": t_blackout, "endTimeSec": t_detect,
            "situation": "Undetermined", "inSight": True,
            "giveWayVesselId": A17, "standOnVesselId": HAILI5,
            "applicableRules": ["R5", "R18"],
            "basis": "【直接 p32】19:51:15 海力5 全船失电、舵机失灵，成为失控船（R3(f)）。【推算 p42】A17 约 90 秒后才目视发现。几何上 19:53:08 航向差约 186.6° 易被判成对遇，但失控船不承担让路义务，故局面标为 Undetermined，让路应为 A17（R18(a)(ii)）。",
            "dangerStage": "CloseQuarters", "doubt": True,
            "doubtReason": "仅看航向差会被判成对遇（R14）；结合 19:51:15 起海力5=NUC，应按 R18 由 A17 让路。",
            "vesselStatus": {HAILI5: nuc, A17: pd},
        },
        {
            "bandId": "HL-B3", "startTimeSec": t_detect, "endTimeSec": t_c,
            "situation": "ImmediateDanger", "inSight": True,
            "giveWayVesselId": A17, "standOnVesselId": HAILI5,
            "applicableRules": ["R8", "R17"],
            "basis": "【直接 p41、p43】已形成紧迫危险；A17 应停车或倒车、采取最有助于避碰的行动（R8(a)(e)）。",
            "dangerStage": "ImmediateDanger", "doubt": False, "doubtReason": None,
            "vesselStatus": {HAILI5: nuc, A17: pd},
        },
        {
            "bandId": "HL-B4", "startTimeSec": t_c, "endTimeSec": t_end,
            "situation": "PostCollision", "inSight": True,
            "giveWayVesselId": None, "standOnVesselId": None,
            "applicableRules": [],
            "basis": "【直接 p26】19:54:32 碰撞。19:54:38 海力5 恢复供电（晚于碰撞约 6 秒）。",
            "dangerStage": "None", "doubt": False, "doubtReason": None,
            "vesselStatus": {HAILI5: nuc, A17: pd},
        },
    ]
    checks = [
        {"checkId": "HL-CK-01", "rule": "R5", "title": "正规瞭望", "vesselId": A17, "verdict": "NotComplied",
         "atTimeSec": t_detect, "requiredAction": "持续有效瞭望，及时发现他船动态",
         "actualAction": "【直接 p42–43】失电后约 90 秒才目视发现；交接班期间驾驶台 6 人，前方瞭望未有效履行",
         "deviation": "Late", "evidenceIds": ["EV-106", "EV-101"], "source": "Seed", "reviewStatus": "Draft"},
        {"checkId": "HL-CK-02", "rule": "R8", "title": "及早、大幅度的避让行动（含减速、停车、倒车）", "vesselId": A17,
         "verdict": "NotComplied", "atTimeSec": T("19:54:00"),
         "requiredAction": "发现失控后立即停车、倒车并采取最有助于避碰的行动（R8(a)(e)）",
         "actualAction": "【直接 p43】舵令多次左右切换；碰撞时航速、航向没有明显变化；19:54 才停车",
         "deviation": "Insufficient", "evidenceIds": ["EV-106", "EV-103"], "source": "Seed", "reviewStatus": "Draft"},
        {"checkId": "HL-CK-03", "rule": "R34", "title": "操纵声号 / 警告声号", "vesselId": A17,
         "verdict": "NotAssessable", "atTimeSec": T("19:51:18"),
         "requiredAction": "针对海力5 的操纵或警告声号（如适用）",
         "actualAction": "【直接 p34】A17 在 19:51:18 和 19:52:36 两次鸣一长声，是为提醒“正海3”轮，不是针对海力5。报告未认定是否违反 R34。",
         "deviation": "", "evidenceIds": ["EV-101"], "source": "Seed", "reviewStatus": "Draft"},
        {"checkId": "HL-CK-04", "rule": "R18", "title": "失控船：他船应给海力5 让路", "vesselId": A17,
         "verdict": "NeedsReview", "atTimeSec": t_blackout,
         "requiredAction": "【推算】19:51:15 起海力5 为失控船，A17 应按 R18(a)(ii) 让路",
         "actualAction": "报告引用 R5/R8 认定 A17 行动不足，未单独列出 R18。需调查员研判是否单列本条。",
         "deviation": "", "evidenceIds": ["EV-105", "EV-106"], "source": "Seed", "reviewStatus": "Draft"},
        {"checkId": "HL-CK-05", "rule": "R18", "title": "失控船不承担让路义务", "vesselId": HAILI5,
         "verdict": "NeedsReview", "atTimeSec": t_blackout,
         "requiredAction": "失电后显示失控号灯并尽快通报动态（R27 等，引擎枚举未覆盖）",
         "actualAction": "【直接 p41】无法显示失控号灯；船长没有第一时间在 VHF 播报失控。报告未认定海力5 违反哪条 COLREG。",
         "deviation": "", "evidenceIds": ["EV-105", "EV-101"], "source": "Seed", "reviewStatus": "Draft"},
        {"checkId": "HL-CK-06", "rule": "R9", "title": "狭水道靠右航行", "vesselId": HAILI5,
         "verdict": "NotAssessable", "atTimeSec": 0,
         "requiredAction": "沿航道右侧行驶",
         "actualAction": "【直接 p31】失电前约定会红灯并向右调整航向；失电后船首先控左偏进入进口航路。左偏是否作为 R9 违反，报告未引用该条。",
         "deviation": "", "evidenceIds": ["EV-101", "EV-105"], "source": "Seed", "reviewStatus": "Draft"},
        {"checkId": "HL-CK-07", "rule": "R9", "title": "狭水道靠右航行", "vesselId": A17,
         "verdict": "Complies", "atTimeSec": 0,
         "requiredAction": "沿进口航道右侧行驶",
         "actualAction": "【直接 p31、p33】A17 在进口航道，约定左舷对左舷通过。报告未认定其违反 R9。",
         "deviation": "None", "evidenceIds": ["EV-101"], "source": "Seed", "reviewStatus": "Draft"},
        {"checkId": "HL-CK-08", "rule": "R8", "title": "海力5 失电后的避让能力", "vesselId": HAILI5,
         "verdict": "NotAssessable", "atTimeSec": t_blackout,
         "requiredAction": "在尚有控制时采取避让行动",
         "actualAction": "【直接 p32】19:51:15 舵机失灵，已无法主动转向。报告未以 R8 认定海力5。",
         "deviation": "", "evidenceIds": ["EV-105"], "source": "Seed", "reviewStatus": "Draft"},
    ]
    put_doc(s, ColregAnalysisRow, CASE_ID, "current", {
        "caseId": CASE_ID,
        "engineVersion": "seed（按公开报告与 REAL_CASES.md §1.1 整理，待调查员确认）",
        "disclaimer": DISCLAIMER,
        "bands": bands,
        "checks": checks,
    })
    # evaluate 附加输入（不在 colreg schema 内，单独键保存，不由 GET /colreg 返回）
    put_doc(s, ColregAnalysisRow, CASE_ID, "inputs", {
        "ownVesselId": HAILI5,
        "targetVesselId": A17,
        "vesselsInSight": True,
        "inNarrowChannel": True,
        # 合同形态（openapi evaluate.vesselStatus）：{vesselId: [{fromUtc, status}]}
        "vesselStatus": {
            HAILI5: [{"fromUtc": EPOCH, "status": "PowerDriven"},
                     {"fromUtc": _utc("19:51:15"), "status": "NotUnderCommand"}],
            A17: [{"fromUtc": EPOCH, "status": "PowerDriven"}],
        },
        "evidenceIds": ["EV-101", "EV-105"],
        "notes": "能见度良好（报告未给海里数，不编造 visibilityNm）。19:51:15 起海力5=NUC【直接 p32】。",
    })


def seed(s: Session, blob_root: Path) -> bool:
    if s.query(CaseRow).filter_by(case_id=CASE_ID).first():
        return False
    case = case_doc()
    put_doc(s, CaseRow, CASE_ID, CASE_ID, case)
    audit.append(s, case_id=CASE_ID, operator=SEED_OP, role="LeadInvestigator", action="case.create",
                 category="Case", command=f"创建案件 {CASE_ID}（公开报告·海力5）", after=case["title"],
                 entity_type="case", entity_id=CASE_ID, utc="2026-11-11T12:00:00Z")
    put_doc(s, VesselRow, CASE_ID, HAILI5, {
        "vesselId": HAILI5, "caseId": CASE_ID, "name": "HAILI 5", "nameCn": "海力5",
        "mmsi": "412356350", "callSign": "BHYU", "flagState": "中国", "vesselTypeCode": "BulkCarrier",
        "loaM": 133.20, "beamM": 22.00, "draftForeM": 6.7, "draftAftM": 7.1,
        "loadingCondition": "Loaded", "colorHex": "#3be3ff"})
    put_doc(s, VesselRow, CASE_ID, A17, {
        "vesselId": A17, "caseId": CASE_ID, "name": "WAN HAI A17", "nameCn": "万海 A17",
        "mmsi": "563234300", "imoNumber": "9968528", "callSign": "9V8938", "flagState": "新加坡",
        "vesselTypeCode": "ContainerShip", "loaM": 334.96, "beamM": 51.00,
        "draftForeM": 11.9, "draftAftM": 12.4, "loadingCondition": "Loaded", "colorHex": "#f97316"})
    for p in track_points():
        s.add(TrackPointRow(case_id=CASE_ID, vessel_id=p["vesselId"], time_sec=p["timeSec"], doc=p))
    seed_evidence(s, blob_root)
    seed_colreg(s)
    put_doc(s, AccessPolicyRow, CASE_ID, "policy", default_policy())
    audit.append(s, case_id=CASE_ID, operator=SEED_OP, role="LeadInvestigator", action="seed.load",
                 category="Case", command="载入海力5 公开报告演示数据（W6）",
                 after=f"航迹 {len(TRACKS)} 点（仅含经纬度）/ 证据 {len(EVIDENCE)} / COLREG 4 带 8 项",
                 entity_type="case", entity_id=CASE_ID, utc="2026-11-11T12:00:00Z")
    return True
