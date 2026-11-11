"""虚构演示案件 Lily / Mary 种子数据（以原型时间线为准：2026-05-18 14:15–14:27 北京时间，星屿港，Mary 撞 Lily 左舷）。

全部人物、船名、MMSI/IMO、证件号、电话、坐标、时间均为虚构（isFictionalDemo = true），不使用 reports/ 下任何真实报告内容。
"""
from __future__ import annotations

import hashlib

import math
from datetime import timedelta
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ..audit import service as audit
from ..cases.models import CaseRow, TrackPointRow, VesselRow
from ..colreg.models import ColregAnalysisRow
from ..common.timeutil import iso, now_utc, parse_iso, sim_to_utc
from ..db import put_doc
from ..evidence import service as ev
from ..evidence.models import EvidenceRow
from ..interviews.models import InterviewRow
from ..interviews.service import utf16_index, utf16_len
from ..agents.models import AgentDraftRow
from ..recommendations.models import ConsultationRoundRow, RecommendationRow
from ..redaction.models import AccessPolicyRow
from ..redaction.policy import default_policy
from ..timeline.models import ConflictRow, TimelineEventRow

CASE_ID = "CASE-2026-DEMO-LILY-MARY"
EPOCH = "2026-05-18T06:15:00Z"          # 14:15:00 北京时间 = SimTime 0
COLLISION_T = 540.0                      # 14:24:00
DURATION = 720.0                         # 至 14:27:00
P_LAT, P_LON = 21.796667, 113.700000     # 21°47.8'N 113°42.0'E（虚构）
FICTION = "【虚构演示】"
SEED_OP = "种子数据（虚构）"


def L(local_hhmm: str, day: int = 18) -> str:
    """北京时间 'HH:MM[:SS]' → UTC ISO。"""
    parts = [int(x) for x in local_hhmm.split(":")] + [0]
    h, m, s = parts[0], parts[1], parts[2] if len(parts) > 3 else 0
    return iso(parse_iso(f"2026-05-{day:02d}T00:00:00Z") + timedelta(hours=h - 8, minutes=m, seconds=s))


def T(local_hhmmss: str) -> float:
    """北京时间 → SimTime 秒。"""
    return (parse_iso(L(local_hhmmss)) - parse_iso(EPOCH)).total_seconds()


# ---------------- 航迹（运动学积分，保证 t=540 s 两船在碰撞点相遇） ----------------

def _profile(vessel: str, t: float) -> tuple[float, float]:
    """返回 (course°, speed kn)。"""
    if vessel == "vessel_mary":
        sp = 13.5 if t < 240 else max(9.5, 13.5 - (t - 240) * 0.27)
        if t >= 500:
            sp = max(8.6, 9.5 - (t - 500) * 0.03)       # 14:23:20 停车后冲程
        crs = 8.0 if t < 435 else 8.0 - min(52.0, (t - 435) * 0.5)  # 14:22:15 左转
        return crs % 360, sp
    sp = 10.6 if t < 465 else max(6.0, 10.6 - (t - 465) * 0.06)
    crs = 188.0 if t < 465 else 188.0 + min(52.0, (t - 465) * 0.9)  # 14:22:45 右满舵
    return crs % 360, sp


def _integrate(vessel: str) -> list[tuple[float, float, float, float, float]]:
    """1 s 步长积分，返回 (t, east_nm, north_nm, course, speed)。"""
    e = n = 0.0
    out = []
    for i in range(int(COLLISION_T) + 1):
        t = float(i)
        crs, sp = _profile(vessel, t)
        out.append((t, e, n, crs, sp))
        r = math.radians(crs)
        e += sp / 3600.0 * math.sin(r)
        n += sp / 3600.0 * math.cos(r)
    return out


def track_points() -> list[dict[str, Any]]:
    pts = []
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(P_LAT))
    for vid in ("vessel_lily", "vessel_mary"):
        seq = _integrate(vid)
        e_c, n_c = seq[-1][1], seq[-1][2]
        lat_c, lon_c = P_LAT, P_LON
        if vid == "vessel_lily":       # 碰撞点：Mary 球鼻艏触 Lily 左舷，两船参考点相距约 40 m
            lat_c += 25.0 / m_per_deg_lat
            lon_c -= 30.0 / m_per_deg_lon
        samples = [s for s in seq if int(s[0]) % 10 == 0]
        last = seq[-1]
        # 碰撞后：Lily 漂移下沉，Mary 冲程减至停船
        e, n = last[1], last[2]
        for k in range(1, 19):
            t = COLLISION_T + k * 10
            if vid == "vessel_lily":
                crs, sp = 205.0, max(0.3, 1.5 - k * 0.07)
            else:
                crs, sp = 330.0, max(0.0, 6.0 - k * 0.6)
            r = math.radians(crs)
            e += sp / 360.0 * math.sin(r)
            n += sp / 360.0 * math.cos(r)
            samples.append((t, e, n, crs, sp))
        for (t, e_nm, n_nm, crs, sp) in samples:
            de, dn = (e_nm - e_c) * 1852.0, (n_nm - n_c) * 1852.0
            pts.append({
                "vesselId": vid, "timeSec": t, "utc": sim_to_utc(EPOCH, t),
                "latDeg": round(lat_c + dn / m_per_deg_lat, 7), "lonDeg": round(lon_c + de / m_per_deg_lon, 7),
                "sogKn": round(sp, 2), "cogDeg": round(crs, 1), "hdgDeg": round((crs + (1.5 if vid == "vessel_mary" else -1.0)) % 360, 1),
                "rotDegPerMin": None, "provenance": "Measured", "source": "AIS-VTS（虚构）",
            })
    return pts


# ---------------- 证据 ----------------

EVIDENCE = [
    # id, title, source, extractedBy, extracted(local), path, category, confidentiality, accesses, needsReview
    ("EV-001", "Mary 轮 VDR 数据包（12 h）", "Mary 轮 VDR 舱", "调查员 A", ("18:40", 18), "raw/vdr/mary_vdr_12h.zip", "VDR", "Normal", 7, False),
    ("EV-002", "Lily 轮 S-VDR 数据包", "救助现场", "调查员 B", ("10:05", 19), "raw/vdr/lily_svdr.zip", "VDR", "Normal", 4, False),
    ("EV-003", "VTS 岸基 AIS 记录", "星屿 VTS 中心 / 调取函", "调查员 A", ("20:12", 18), "raw/ais/vts_shore_ais.nmea", "AIS", "Normal", 5, False),
    ("EV-004", "Mary 轮 ECDIS 截屏 ×38", "Mary 轮驾驶台", "调查员 A", ("19:02", 18), "raw/ecdis/mary_ecdis_screens.zip", "ECDIS", "Normal", 3, False),
    ("EV-005", "车钟/舵角记录纸扫描", "Mary 轮机舱", "调查员 C", ("08:30", 19), "evidence/EV-005/engine_rudder_log_scan.pdf", "EngineLog", "Normal", 2, True),
    ("EV-006", "询问笔录 IR-01 ~ IR-06", "询问室", "调查员 A、B", ("10:00", 21), "evidence/EV-006/interviews_IR01-06.zip", "Testimony", "Restricted", 9, False),
]
ACCESS_PURPOSES = ["只读回放", "时间轴同步", "冲突核对", "报告引用", "复核"]


def _blob(eid: str, title: str) -> bytes:
    line = f"MCIS FICTIONAL DEMO EVIDENCE {eid} | {title} | 虚构演示数据，不代表任何真实事故\n"
    return (line * 64).encode("utf-8")


def seed_evidence(s: Session, blob_root: Path) -> None:
    for i, (eid, title, source, by, (hhmm, day), rel, cat, conf, accesses, review) in enumerate(
            sorted(EVIDENCE, key=lambda x: L(x[4][0], x[4][1]))):
        data = _blob(eid, title)
        sha = ev.write_blob(blob_root, CASE_ID, rel, data, overwrite=True)
        item = {"evidenceId": eid, "caseId": CASE_ID, "title": title, "source": source, "extractedBy": by,
                "extractedUtc": L(hhmm, day), "sha256": sha, "relativePath": rel, "category": cat,
                "confidentiality": conf, "note": "纸本原件字迹不清" if review else ""}
        put_doc(s, EvidenceRow, CASE_ID, eid, item)
        ev.append_custody(s, case_id=CASE_ID, evidence_id=eid, kind="Register", operator=by, role="Investigator",
                          sha256=sha, detail="登记（虚构演示）", item=item, utc=item["extractedUtc"])
    # 访问记录（时间按顺序递增，保证 prev 链与时间同序）
    t0 = parse_iso(L("11:00", 21))
    k = 0
    order = []
    for (eid, *_rest) in EVIDENCE:
        accesses = _rest[7]
        order += [eid] * (accesses - 1)
    for eid in order:
        k += 1
        cur = s.query(EvidenceRow).filter_by(case_id=CASE_ID, key=eid).first().doc["sha256"]
        ev.append_custody(s, case_id=CASE_ID, evidence_id=eid, kind="Access", operator=["调查员 A", "调查员 B", "调查员 C"][k % 3],
                          role="Investigator", sha256=cur, detail=ACCESS_PURPOSES[k % len(ACCESS_PURPOSES)],
                          utc=iso(t0 + timedelta(minutes=37 * k)))
    # 全部校验一次
    tv = parse_iso(L("09:00", 22))
    for j, (eid, *_r) in enumerate(EVIDENCE):
        cur = s.query(EvidenceRow).filter_by(case_id=CASE_ID, key=eid).first().doc["sha256"]
        ev.append_custody(s, case_id=CASE_ID, evidence_id=eid, kind="Verify", operator="调查员 B", role="Investigator",
                          sha256=cur, previous_sha256=cur, detail="重新计算 SHA-256", matched=True,
                          utc=iso(tv + timedelta(seconds=5 * j)))
    # EV-005 标注需复核（保管链 Review 事件）
    cur = s.query(EvidenceRow).filter_by(case_id=CASE_ID, key="EV-005").first().doc["sha256"]
    ev.append_custody(s, case_id=CASE_ID, evidence_id="EV-005", kind="Review", operator="调查员 C", role="Investigator",
                      sha256=cur, detail="扫描件字迹不清，需与纸本原件复核", review=True, utc=L("10:00", 22))
    # EV-001 最近访问：2026-05-22 15:31 调查员 B（只读回放）
    cur = s.query(EvidenceRow).filter_by(case_id=CASE_ID, key="EV-001").first().doc["sha256"]
    ev.append_custody(s, case_id=CASE_ID, evidence_id="EV-001", kind="Access", operator="调查员 B", role="Investigator",
                      sha256=cur, detail="只读回放", utc=L("15:31", 22))


# ---------------- 时间线与冲突 ----------------

TIMELINE = [
    ("14:15:00", None, "Lily 轮卸空离泊", "Lily 轮完成散货卸载，空载离泊驶入航道", "Event", "vessel_lily", False, ["EV-002"], "VDR-L01 / 港口调度记录"),
    ("14:18:30", None, "两船进入窄航道", "Lily 轮与进港满载 Mary 轮同时接近窄航道弯头", "Event", None, False, ["EV-003"], "AIS 轨迹记录"),
    ("14:20:30", None, "形成小 DCPA 对遇", "两船 DCPA 已小于 0.1 nm、TCPA 约 3 min，构成碰撞危险（mcis-core cpa 复算）", "Event", None, False, ["EV-001", "EV-003"], "ARPA 解算与 VTS 雷达录像"),
    ("14:22:15", None, "Mary 轮违规左转", "Mary 轮值班驾驶员误判态势，违背规则向左打舵 20°", "Action", "vessel_mary", False, ["EV-001"], "Mary 轮 VDR 舵角记录"),
    ("14:22:45", None, "Lily 轮紧急右满舵", "Lily 轮发觉来船横越，下令右满舵并全速倒车", "Action", "vessel_lily", False, ["EV-002"], "Lily 轮车钟簿与 VDR 语音"),
    ("14:24:00", None, "两船发生碰撞", "Mary 轮球鼻艏以约 42° 交角撞击 Lily 轮左舷 1# 货舱", "Event", None, False, ["EV-001", "EV-002", "EV-003"], "AIS 碰撞点与船体破口勘验"),
    ("14:27:30", None, "Lily 轮进水开始下沉", "Lily 轮首部破损大量进水，左倾坐沉浅滩", "Event", "vessel_lily", False, ["EV-002"], "现场航拍与搜救记录"),
    ("14:15:00", "14:22:00", "Mary 轮航速 13.5 kn 过高", "满载集装箱船在窄航道未采用安全航速", "Condition", "vessel_mary", False, ["EV-003"], "AIS SOG 实测记录"),
    ("14:19:00", "14:22:00", "Mary 驾驶台瞭望疏忽（推定）", "推定值班驾驶员忙于核对进港泊位图而未持续 ARPA 标绘", "Condition", "vessel_mary", True, ["EV-006"], "笔录矛盾·推定项"),
    ("14:21:30", None, "VHF 沟通未达成一致（推定）", "双方 VHF 16 频道呼叫存在误解（推定）", "Communication", None, True, ["EV-001"], "VDR 环境麦克风残缺录音"),
    ("14:15:00", "14:27:00", "航道狭窄且能见度 1.5 nm", "雾，3#–4# 浮标航道有效宽度不足 320 m", "Condition", None, False, [], "港口气象站与海图水深"),
    ("14:20:00", "14:24:00", "西南向 1.8 kn 横流压偏", "落潮流（215°/1.8 kn）加剧两船向航道中心线漂移", "Condition", None, False, [], "水文潮流表"),
]


def seed_timeline(s: Session) -> None:
    for i, (t, t_end, title, desc, kind, vid, pres, evs, src) in enumerate(TIMELINE, start=1):
        sec = T(t)
        put_doc(s, TimelineEventRow, CASE_ID, f"TE-{i:02d}", {
            "eventId": f"TE-{i:02d}", "caseId": CASE_ID, "timeSec": sec, "utc": sim_to_utc(EPOCH, sec),
            "endTimeSec": T(t_end) if t_end else None, "title": title, "description": desc, "kind": kind,
            "vesselId": vid, "presumptive": pres, "evidenceIds": evs, "sourceLabel": src, "confirmed": True})
    conflicts = [
        {"conflictId": "C-01", "summary": "Mary 左舵 20°：VDR 14:22:15 ／ 笔录称“14:23 才转”", "trackKind": "RudderAngle",
         "vesselId": "vessel_mary", "timeSec": T("14:22:15"),
         "a": {"sourceLabel": "VDR 舵角", "valueText": "14:22:15 左舵 20°", "value": None, "timeSec": T("14:22:15"), "evidenceId": "EV-001"},
         "b": {"sourceLabel": "笔录 IR-03 第 3 问", "valueText": "14:23 才开始左舵", "value": None, "timeSec": T("14:23:00"), "evidenceId": "EV-006"},
         "delta": 45, "deltaUnit": "s", "status": "PendingInterview", "resolution": "待询问核实", "detectedBy": "RuleEngine"},
        {"conflictId": "C-02", "summary": "车钟记录纸停车时刻比 VDR 晚 65 s", "trackKind": "EngineTelegraph",
         "vesselId": "vessel_mary", "timeSec": T("14:23:20"),
         "a": {"sourceLabel": "VDR 车钟", "valueText": "14:23:20 停车", "value": None, "timeSec": T("14:23:20"), "evidenceId": "EV-001"},
         "b": {"sourceLabel": "车钟记录纸", "valueText": "14:24:25 停车", "value": None, "timeSec": T("14:24:25"), "evidenceId": "EV-005"},
         "delta": 65, "deltaUnit": "s", "status": "ClockCorrected", "resolution": "钟差已校正（记录纸时钟快 65 s）", "detectedBy": "RuleEngine"},
        {"conflictId": "C-03", "summary": "Lily 航速：ECDIS 9.8 kn ／ AIS 10.6 kn", "trackKind": "SpeedOverGround",
         "vesselId": "vessel_lily", "timeSec": T("14:20:00"),
         "a": {"sourceLabel": "ECDIS", "valueText": "9.8 kn", "value": 9.8, "timeSec": T("14:20:00"), "evidenceId": "EV-004"},
         "b": {"sourceLabel": "AIS", "valueText": "10.6 kn", "value": 10.6, "timeSec": T("14:20:00"), "evidenceId": "EV-003"},
         "delta": 0.8, "deltaUnit": "kn", "status": "Annotated", "resolution": "标注·采信 AIS", "detectedBy": "RuleEngine"},
        {"conflictId": "C-04", "summary": "Mary 声号：笔录称“鸣了一长声” ／ VDR 音频无声号", "trackKind": "Audio",
         "vesselId": "vessel_mary", "timeSec": T("14:23:00"),
         "a": {"sourceLabel": "VDR 音频", "valueText": "14:22–14:24 无声号", "value": None, "timeSec": T("14:23:00"), "evidenceId": "EV-001"},
         "b": {"sourceLabel": "笔录 IR-03 第 3 问", "valueText": "鸣了一长声", "value": None, "timeSec": None, "evidenceId": "EV-006"},
         "delta": None, "deltaUnit": "", "status": "Open", "resolution": "", "detectedBy": "Agent"},
    ]
    for c in conflicts:
        c["caseId"] = CASE_ID
        put_doc(s, ConflictRow, CASE_ID, c["conflictId"], c)


# ---------------- 询问笔录 ----------------

IR03_TURNS = [
    ("你什么时候第一次在雷达上看到 Lily 轮？", "大概 14:17 左右，在 3 号浮标北面，距离差不多 3 海里，当时看它是出港的。", []),
    ("当时能见度怎么样？你有没有减速？", "有雾，能见度大约 1.5 海里。我把车钟拉到了半速，14:19 前后。", []),
    ("两船距离接近时你采取了什么行动？", "我觉得它会从我右边过，就在 14:23 才开始左舵，左舵 20 度，同时鸣了一长声。", []),
    ("当时船长在驾驶台吗？", "船长 14:23 半才上来，之前在房间，我没有叫他。我前一晚因为家里有事没睡好。", ["家里有事没睡好"]),
    ("你和 Lily 轮或 VTS 有没有 VHF 联系？", "VTS 在 14:20 叫过我们，我回答了“保持航向”，没有直接呼叫 Lily。", []),
    ("你上一次连续休息是什么时候，睡了多久？", "前一天下午一直在装卸，晚上 22 点才下来，0 点又接班，中间大概睡了不到两个小时。", []),
    ("碰撞前你有没有用 ARPA 录取 Lily 轮？", "录取了，但矢量设成了 3 分钟，报警响过一次我按掉了。", []),
    ("你的手机号码？", "138 0000 0000", []),
]

# (summary, kind, subject, round, quote, claim, refLocal, outcome, observed, sourceLabel, delta, unit, reviewStatus, extractedBy)
IR03_STATEMENTS = [
    ("首次发现距离 3 nm", "Observation", "Mary.target_range_first_detect", 1, "距离差不多 3 海里",
     {"valueType": "Scalar", "scalar": 3.0, "unit": "nm"}, "14:17:00", "Contradictory", "2.4 nm (AIS 14:17)", "AIS / VTS", 0.6, "nm", "Confirmed", "Agent"),
    ("14:19 车钟半速", "Operation", "Mary.engine_telegraph", 2, "我把车钟拉到了半速",
     {"valueType": "EventTime", "time": "14:19:00"}, None, "Consistent", "14:19:08 (VDR)", "VDR 车钟", -8, "s", "Confirmed", "Agent"),
    ("14:23 才开始左舵", "Operation", "Mary.rudder_angle", 3, "在 14:23 才开始左舵",
     {"valueType": "EventTime", "time": "14:23:00"}, None, "Contradictory", "14:22:15 (VDR 舵角)", "VDR 舵角", 45, "s", "Confirmed", "Agent"),
    ("左舵 20°", "Operation", "Mary.rudder_angle", 3, "左舵 20 度",
     {"valueType": "Scalar", "scalar": -20.0, "unit": "deg"}, "14:22:30", "Consistent", "左 20° (VDR)", "VDR 舵角", 0, "deg", "Confirmed", "Agent"),
    ("鸣放一长声", "Operation", "Mary.sound_signal", 3, "鸣了一长声",
     {"valueType": "Occurrence", "occurred": True}, "14:23:00", "Contradictory", "无声号 (VDR 音频)", "VDR 音频", None, "", "Confirmed", "Agent"),
    ("VTS 14:20 呼叫", "Observation", "VTS.vhf_call", 5, "VTS 在 14:20 叫过我们",
     {"valueType": "EventTime", "time": "14:20:00"}, None, "Consistent", "14:20:12 (VHF16)", "VHF16 录音", -12, "s", "Confirmed", "Agent"),
    ("船长 14:23:30 上驾驶台", "Observation", "Mary.master_on_bridge", 4, "船长 14:23 半才上来",
     {"valueType": "EventTime", "time": "14:23:30"}, None, "Consistent", "音频 14:23:34", "VDR 音频", -4, "s", "Confirmed", "Agent"),
    ("事发前连续睡眠不足 2 h", "Observation", "Mary.oow_rest_hours", 6, "睡了不到两个小时",
     {"valueType": "Scalar", "scalar": 2.0, "unit": "h"}, "14:15:00", "Unverifiable", "工休记录待调取", "工休记录", None, "", "Draft", "Agent"),
]

OTHER_RECORDS = [
    ("IR-01", "张船长（虚构）", "船长", "Mary 轮", ("14:00", 19), 52, True,
     [("你何时上驾驶台？", "听到值班驾驶员呼叫后大约 14:23 上来。")],
     [("驾驶员 14:22 前已呼叫船长", "Contradictory", "VDR 无呼叫记录")]),
    ("IR-02", "李船长（虚构）", "船长", "Lily 轮", ("16:20", 19), 47, True,
     [("碰撞前你在哪里？", "我在驾驶台，14:22 发现来船左转后下令右满舵。")], [("14:22:45 右满舵", "Consistent", "14:22:47 (S-VDR)")]),
    ("IR-04", "王舵工（虚构）", "舵工", "Mary 轮", ("10:10", 20), 35, True,
     [("你执行了什么舵令？", "二副让我左舵 20，我照做了。")], [("执行左舵 20°", "Consistent", "左 20° (VDR)")]),
    ("IR-05", "赵大副（虚构）", "大副（值班）", "Lily 轮", ("15:00", 20), 41, True,
     [("你何时在雷达上发现 Mary 轮？", "14:16 左右，距离约 4 海里。")], [("14:16 发现，距离 4 nm", "Contradictory", "14:16 距离 2.8 nm (AIS)")]),
    ("IR-06", "陈值班员（虚构）", "VTS 值班员", "星屿 VTS", ("09:00", 21), 29, True,
     [("你是否提醒过两船？", "14:20 呼叫 Mary 轮提醒对遇，它回答保持航向。")], [("14:20 呼叫 Mary", "Consistent", "14:20:12 (VHF16)")]),
]


# 架构裁定：比对结果一律需调查员确认才生效。种子里只有 IR-03-S03（对应冲突 C-01）和 IR-01-S01 已确认，其余待确认。
CONFIRMED_CC = {"IR-03-S03": ("调查员 A", "14:20", 23, "与 VDR 舵角逐秒核对"), "IR-01-S01": ("调查员 A", "15:10", 23, "VDR 音频无呼叫")}


def _cc_state(sid: str) -> dict[str, Any]:
    if sid in CONFIRMED_CC:
        by, hhmm, day, note = CONFIRMED_CC[sid]
        return {"state": "Confirmed", "decidedBy": by, "decidedUtc": L(hhmm, day), "note": note}
    return {"state": "PendingConfirmation", "decidedBy": None, "decidedUtc": None, "note": ""}


def _ir03() -> dict[str, Any]:
    turns = [{"round": i, "question": q, "answer": a, "utc": None, "sensitiveFragments": frags}
             for i, (q, a, frags) in enumerate(IR03_TURNS, start=1)]
    statements, checks = [], []
    for j, (summ, kind, subj, rnd, quote, claim, ref, outcome, observed, src, delta, unit, rs, by) in enumerate(IR03_STATEMENTS, start=1):
        answer = IR03_TURNS[rnd - 1][1]
        start = utf16_index(answer, quote)
        c = {"valueType": claim["valueType"], "time": None, "scalar": None, "unit": claim.get("unit", ""), "position": None, "occurred": None}
        if claim["valueType"] == "EventTime":
            c["time"] = L(claim["time"])
        elif claim["valueType"] == "Scalar":
            c["scalar"] = claim["scalar"]
        elif claim["valueType"] == "Occurrence":
            c["occurred"] = claim["occurred"]
        sid = f"IR-03-S{j:02d}"
        statements.append({"statementId": sid, "recordId": "IR-03", "kind": kind, "subject": subj, "summary": summ, "claim": c,
                           "referenceUtc": L(ref) if ref else None,
                           "span": {"round": rnd, "field": "Answer", "start": start, "length": utf16_len(quote)},
                           "quote": quote, "reviewStatus": rs, "extractedBy": by})
        checks.append({"statementId": sid, "recordId": "IR-03", "outcome": outcome, "delta": delta, "deltaUnit": unit,
                       "claimedText": summ, "observedText": observed, "sourceLabel": src, "rule": "W3 StatementCrossChecker（种子结果）",
                       **_cc_state(sid)})
    return {"recordId": "IR-03", "caseId": CASE_ID,
            "interviewee": {"intervieweeId": "P-03", "name": "张某（虚构）", "role": "二副（OOW）", "affiliation": "Mary 轮",
                            "idNumber": "000000000000000000", "phone": "138 0000 0000"},
            "startUtc": L("09:30", 19), "durationMin": 68, "location": "星屿海事局询问室（虚构）", "recorder": "调查员 B",
            "interviewers": ["调查员 A"], "sourceSha256": "", "evidenceId": "EV-006", "signed": True,
            "turns": turns, "statements": statements, "crossChecks": checks}


def seed_interviews(s: Session) -> None:
    put_doc(s, InterviewRow, CASE_ID, "IR-03", _ir03())
    for rid, name, role, aff, (hhmm, day), dur, signed, turns, checks in OTHER_RECORDS:
        t = [{"round": i, "question": q, "answer": a, "utc": None, "sensitiveFragments": []} for i, (q, a) in enumerate(turns, start=1)]
        cc = [{"statementId": f"{rid}-S{k:02d}", "recordId": rid, "outcome": o, "delta": None, "deltaUnit": "", "claimedText": c,
               "observedText": obs, "sourceLabel": "VDR/AIS", "rule": "W3 StatementCrossChecker（种子结果）",
               **_cc_state(f"{rid}-S{k:02d}")}
              for k, (c, o, obs) in enumerate(checks, start=1)]
        put_doc(s, InterviewRow, CASE_ID, rid, {
            "recordId": rid, "caseId": CASE_ID,
            "interviewee": {"intervieweeId": "P-" + rid[-2:], "name": name, "role": role, "affiliation": aff},
            "startUtc": L(hhmm, day), "durationMin": dur, "location": "星屿海事局询问室（虚构）", "recorder": "调查员 B",
            "interviewers": ["调查员 A"], "sourceSha256": "", "evidenceId": "EV-006", "signed": signed,
            "turns": t, "statements": [], "crossChecks": cc})


# ---------------- COLREG（W1 规则引擎交付前的种子结果，标注 source=Seed） ----------------

CHECK_ROWS = [
    ("R5", "正规瞭望（视觉+雷达+听觉）", "Partial", "NotComplied", ["EV-001", "EV-006"]),
    ("R6", "安全航速（能见度 1.5 nm）", "Complies", "Partial", ["EV-003"]),
    ("R7", "判断碰撞危险（ARPA 系统观测）", "Complies", "NotComplied", ["EV-001"]),
    ("R8", "及早、大幅度的避让行动", "Partial", "NotComplied", ["EV-001", "EV-002"]),
    ("R9", "狭水道靠右航行", "Complies", "NotComplied", ["EV-003"]),
    ("R14", "对遇局面：各自向右转向", "Complies", "NotComplied", ["EV-001"]),
    ("R17-2b", "紧迫危险时的最有助避碰行动", "Complies", "Partial", ["EV-002"]),
    ("R19", "能见度不良中的行动", "Partial", "NotComplied", ["EV-001"]),
    ("R34-35", "操纵声号 / 雾号", "Partial", "NotComplied", ["EV-001"]),
]
MARY_ACTIONS = [
    ("14:18:30", "R9", "靠航道右侧", "偏航道中线左 40 m", "Deviation"),
    ("14:19:00", "R6", "降至安全航速（R6/R19）", "半速 12.0 → 9.5 kn", "Insufficient"),
    ("14:20:40", "R14", "大幅右转（R14/R8）", "保持航向 008°", "NoAction"),
    ("14:21:30", "R34-35", "右转并鸣一短声", "无声号", "NoAction"),
    ("14:22:15", "R14", "不得向左转（R14(a)）", "左舵 20°", "Violation"),
    ("14:23:00", "R8", "停车 / 全速倒车（R8(e)）", "14:23:20 停车", "Late"),
]


def seed_colreg(s: Session) -> None:
    vs = {"vessel_lily": "PowerDriven", "vessel_mary": "PowerDriven"}
    bands = [
        {"bandId": "B1", "startTimeSec": 0, "endTimeSec": T("14:18:30"), "situation": "RestrictedVisibility", "inSight": False,
         "giveWayVesselId": None, "standOnVesselId": None, "applicableRules": ["R6", "R7", "R19"], "basis": "能见度约 1.5 nm，仅雷达探测，未互见",
         "dangerStage": "None", "doubt": False, "doubtReason": None, "vesselStatus": vs},
        {"bandId": "B2", "startTimeSec": T("14:18:30"), "endTimeSec": T("14:21:30"), "situation": "NarrowChannel", "inSight": False,
         "giveWayVesselId": None, "standOnVesselId": None, "applicableRules": ["R9", "R19(d)"], "basis": "进入窄航道；未互见，按 R19(d) 不得向左转",
         "dangerStage": "CloseQuarters", "doubt": False, "doubtReason": None, "vesselStatus": vs},
        {"bandId": "B3", "startTimeSec": T("14:21:30"), "endTimeSec": T("14:22:15"), "situation": "HeadOn", "inSight": True,
         "giveWayVesselId": None, "standOnVesselId": None, "applicableRules": ["R14", "R34"], "basis": "互见后对遇：航向差 180°±6°，双方均应向右转",
         "dangerStage": "CloseQuarters", "doubt": False, "doubtReason": None, "vesselStatus": vs},
        {"bandId": "B4", "startTimeSec": T("14:22:15"), "endTimeSec": COLLISION_T, "situation": "ImmediateDanger", "inSight": True,
         "giveWayVesselId": None, "standOnVesselId": None, "applicableRules": ["R8", "R17(b)"], "basis": "Mary 左转后形成紧迫危险",
         "dangerStage": "ImmediateDanger", "doubt": False, "doubtReason": None, "vesselStatus": vs},
        {"bandId": "B5", "startTimeSec": COLLISION_T, "endTimeSec": DURATION, "situation": "PostCollision", "inSight": True,
         "giveWayVesselId": None, "standOnVesselId": None, "applicableRules": [], "basis": "14:24:00 碰撞",
         "dangerStage": "None", "doubt": False, "doubtReason": None, "vesselStatus": vs},
    ]
    checks = []
    n = 0
    for rule, title, lily, mary, evs in CHECK_ROWS:
        for vid, verdict in (("vessel_lily", lily), ("vessel_mary", mary)):
            n += 1
            checks.append({"checkId": f"CK-{n:02d}", "rule": rule, "title": title, "vesselId": vid, "verdict": verdict,
                           "atTimeSec": None, "requiredAction": "", "actualAction": "", "deviation": "",
                           "evidenceIds": evs, "source": "Seed", "reviewStatus": "Draft"})
    for hhmmss, rule, req, act, dev in MARY_ACTIONS:
        n += 1
        checks.append({"checkId": f"CK-{n:02d}", "rule": rule, "title": "应采取 vs 实际行动", "vesselId": "vessel_mary",
                       "verdict": "NotComplied" if dev in ("Violation", "NoAction") else "Partial", "atTimeSec": T(hhmmss),
                       "requiredAction": req, "actualAction": act, "deviation": dev, "evidenceIds": ["EV-001"],
                       "source": "Seed", "reviewStatus": "Draft"})
    put_doc(s, ColregAnalysisRow, CASE_ID, "current", {
        "caseId": CASE_ID, "engineVersion": "seed（W1 规则引擎交付后由 mcis-core colreg 重算）",
        "disclaimer": "仅作安全调查技术分析，不作责任认定。", "bands": bands, "checks": checks})


# ---------------- 安全建议与征求意见 ----------------

RECS = [
    # id, title, causeNodeIds, addressee, status, due(UTC 日期), progress, interim, responseText
    ("SR-2026-01", "Mary 轮公司 SMS 增加狭水道与雾航专项程序", ["HFACS-1", "COLREG-R9", "COLREG-R19"], "Mary 船公司（虚构）", "Issued", "2026-08-30", 0, False, None),
    ("SR-2026-02", "船长常规命令中明确雾航叫船条件", ["HFACS-2"], "Mary 船公司（虚构）", "Issued", "2026-08-30", 0, False, None),
    ("SR-2026-03", "全船队驾驶员 BRM 复训并考核闭环沟通", ["HFACS-3", "ECFC-E4"], "Mary 船公司（虚构）", "Responded", "2026-12-31", 60, False, "接受，已排期分批复训（虚构）"),
    ("SR-2026-04", "工休时间电子记录与超时自动报警", ["HFACS-2", "FATIGUE"], "Mary 船公司（虚构）", "Responded", "2027-03-31", 35, False, "接受，系统选型中（虚构）"),
    ("SR-2026-05", "临时措施：雾航限速 8 kn（MSC.255 §25.5 临时安全措施）", ["COLREG-R6"], "星屿 VTS（虚构）", "Implemented", "2026-06-02", 100, True, "已发布航行通告并执行（虚构）"),
    ("SR-2026-06", "星屿 VTS 对雾航双向通航实施单向交通管制", ["ECFC-C4", "BOWTIE-B1"], "星屿 VTS（虚构）", "Draft", "2026-12-31", 0, False, None),
    ("SR-2026-07", "航道 3#–4# 浮标增设 AIS 虚拟航标", ["HFACS-EXT"], "航标处（虚构）", "Draft", "2026-12-31", 0, False, None),
]
STATUS_PATH = {"Draft": [], "Issued": ["Issued"], "Responded": ["Issued", "Responded"], "Implemented": ["Issued", "Responded", "Implemented"]}


def seed_recommendations(s: Session) -> None:
    t = parse_iso(L("10:00", 25))
    for i, (rid, title, causes, addr, status, due, prog, interim, resp) in enumerate(RECS):
        t += timedelta(hours=1)
        created = t
        audit.append(s, case_id=CASE_ID, operator="调查员 A", role="Investigator", action="safetyrec.create", category="SafetyRec",
                     command=f"新建安全建议 {rid}",
                     after=f"对象={addr}；原因节点={','.join(causes)}；期限={due}T15:59:59Z" + ("；临时措施" if interim else ""),
                     entity_type="recommendation", entity_id=rid, utc=created)
        history, responses, prev = [], [], "Draft"
        for st in STATUS_PATH[status]:
            t += timedelta(hours=5)
            if st == "Responded":
                # = RecordResponse：一条 safetyrec.response 审计，同时 Issued→Responded
                responses.append({"party": addr, "text": resp, "utc": iso(t)})
                audit.append(s, case_id=CASE_ID, operator="调查员 A", role="Investigator", action="safetyrec.response",
                             category="SafetyRec", command=f"登记回复 {rid}", before=prev, after=f"Responded；回复方={addr}",
                             entity_type="recommendation", entity_id=rid, utc=t)
                history.append({"from": prev, "to": st, "operator": "调查员 A", "utc": iso(t), "note": f"回复方={addr}"})
                prev = st
                continue
            note = "核实落实（2026-06-02 现场检查，虚构）" if st == "Implemented" else ""
            history.append({"from": prev, "to": st, "operator": "首席调查官", "utc": iso(t), "note": note})
            audit.append(s, case_id=CASE_ID, operator="首席调查官", role="LeadInvestigator", action="safetyrec.transition",
                         category="SafetyRec", command=f"建议状态变更 {rid}", before=prev, after=st + (f"；{note}" if note else ""),
                         entity_type="recommendation", entity_id=rid, utc=t)
            prev = st
        rec = {"id": rid, "caseId": CASE_ID, "title": title, "body": f"{title}。【虚构演示】", "addressee": addr,
               "causeNodeIds": causes, "dueUtc": f"{due}T15:59:59Z", "isInterim": interim, "createdUtc": iso(created),
               "updatedUtc": history[-1]["utc"] if history else iso(created), "status": status, "progressPct": prog,
               "verificationNote": "核实落实（2026-06-02 现场检查，虚构）" if status == "Implemented" else "",
               "history": history, "responses": responses}
        put_doc(s, RecommendationRow, CASE_ID, rid, rec)

    now = now_utc()
    parties = [{"partyId": "FLAG-A", "name": "船旗国 A（Lily）"}, {"partyId": "FLAG-B", "name": "船旗国 B（Mary）"},
               {"partyId": "CO-LILY", "name": "Lily 船公司"}, {"partyId": "CO-MARY", "name": "Mary 船公司"}]

    def mk_round(n, ver, opened, deadline, closed, replies, waivers=()):
        comments, reps = [], []
        for pid, days_ago, text, decisions in replies:
            ids = []
            for k, dec in enumerate(decisions, start=1):
                cid = f"R{n}-C{len(comments) + 1:02d}"
                comments.append({"commentId": cid, "round": n, "partyId": pid, "text": f"{pid} 意见 {k}（虚构）", "decision": dec,
                                 "feedback": "" if dec in ("Adopted", "Pending") else "已在草案中说明理由（虚构）",
                                 "decidedBy": None if dec == "Pending" else "首席调查官",
                                 "decidedUtc": None if dec == "Pending" else iso(now - timedelta(days=max(days_ago - 2, 0)))})
                ids.append(cid)
            reps.append({"partyId": pid, "utc": iso(now - timedelta(days=days_ago)), "text": text, "commentIds": ids})
        return {"roundNo": n, "caseId": CASE_ID, "draftVersion": ver, "openedUtc": iso(opened), "deadlineUtc": iso(deadline),
                "isAgreedDeadline": False, "draftSha256": hashlib.sha256(ver.encode("utf-8")).hexdigest(),
                "isClosed": closed, "closedUtc": iso(deadline) if closed else None,
                "parties": parties, "replies": reps,
                "waivers": [{"partyId": pid, "reason": why, "utc": iso(now - timedelta(days=d))} for pid, d, why in waivers],
                "comments": comments}

    r1 = mk_round(1, "草案 v0.9（虚构）", now - timedelta(days=75), now - timedelta(days=45), True, [
        ("FLAG-A", 50, "第 1 轮书面意见（虚构）", ["Adopted", "Adopted", "NotAdopted"]),
        ("FLAG-B", 47, "第 1 轮书面意见（虚构）", ["Adopted", "PartiallyAdopted", "NotAdopted"]),
        ("CO-LILY", 52, "第 1 轮书面意见（虚构）", ["Adopted"]),
    ], waivers=[("CO-MARY", 46, "书面声明对第 1 轮草案无意见（虚构）")])
    r2 = mk_round(2, "草案 v1.2（虚构）", now - timedelta(days=18), now + timedelta(days=12, hours=6), False, [
        ("FLAG-A", 4, "第 2 轮书面意见（虚构）", ["Adopted", "Adopted", "PartiallyAdopted", "Pending"]),
        ("CO-LILY", 6, "第 2 轮书面意见（虚构）", ["Adopted"]),
    ])
    put_doc(s, ConsultationRoundRow, CASE_ID, "1", r1)
    put_doc(s, ConsultationRoundRow, CASE_ID, "2", r2)


def seed_agent_drafts(s: Session) -> None:
    drafts = [
        {"draftId": "AD-001", "caseId": CASE_ID, "agent": "people_ops", "kind": "statement_extraction",
         "targetEntityType": "statement", "targetEntityId": "IR-03-S08",
         "payload": {"recordId": "IR-03", "statementId": "IR-03-S08", "summary": "事发前连续睡眠不足 2 h（疲劳风险）"},
         "citations": [{"evidenceId": "EV-006", "recordId": "IR-03", "round": 6, "quote": "睡了不到两个小时"}],
         "model": "none（骨架，未接模型）", "promptDigest": "", "status": "PendingReview", "createdUtc": L("11:00", 23),
         "reviewedBy": None, "reviewedUtc": None, "reviewNote": ""},
        {"draftId": "AD-002", "caseId": CASE_ID, "agent": "timeline", "kind": "timeline_anchor",
         "targetEntityType": "timelineEvent", "targetEntityId": None,
         "payload": {"timeSec": T("14:21:40"), "title": "Mary 轮 ARPA 报警被人工消音（推定）", "kind": "Action",
                     "vesselId": "vessel_mary", "presumptive": True, "evidenceIds": ["EV-001", "EV-006"],
                     "description": "笔录称报警响过一次被按掉；VDR 音频 14:21:40 前后有报警音", "sourceLabel": "笔录 IR-03 + VDR 音频"},
         "citations": [{"evidenceId": "EV-006", "recordId": "IR-03", "round": 7, "quote": "报警响过一次我按掉了"}],
         "model": "none（骨架，未接模型）", "promptDigest": "", "status": "PendingReview", "createdUtc": L("11:05", 23),
         "reviewedBy": None, "reviewedUtc": None, "reviewNote": ""},
    ]
    for d in drafts:
        put_doc(s, AgentDraftRow, CASE_ID, d["draftId"], d)


def case_doc() -> dict[str, Any]:
    return {
        "caseId": CASE_ID, "schemaVersion": "1.0.0", "title": FICTION + "星屿港 Lily 轮与 Mary 轮碰撞事故",
        "accidentCode": "DEMO-2026-0518", "accidentType": "Collision", "accidentGrade": "VerySerious",
        "incidentTimeUtc": sim_to_utc(EPOCH, COLLISION_T), "caseEpochUtc": EPOCH, "displayTimeZoneOffsetMinutes": 480,
        "incidentLocation": {"lonDeg": P_LON, "latDeg": P_LAT, "heightM": 0.0}, "seaLevelOffsetM": 0.0,
        "leadInvestigator": "首席调查官（虚构）", "agencyName": "星屿海事局（虚构）", "isFictionalDemo": True,
        "summaryNotes": "虚构演示数据：雾中窄航道对遇，Mary 轮违规左转，14:24:00 球鼻艏撞击 Lily 轮左舷 1# 货舱，Lily 轮进水坐沉。不代表任何真实事故。",
        "durationSec": DURATION, "placeName": "星屿港 3#–4# 浮标窄航道（虚构）",
    }


def seed(s: Session, blob_root: Path) -> bool:
    if s.query(CaseRow).filter_by(case_id=CASE_ID).first():
        return False
    case = case_doc()
    put_doc(s, CaseRow, CASE_ID, CASE_ID, case)
    audit.append(s, case_id=CASE_ID, operator=SEED_OP, role="LeadInvestigator", action="case.create", category="Case",
                 command=f"创建案件 {CASE_ID}（虚构演示）", after=case["title"], entity_type="case", entity_id=CASE_ID,
                 utc=L("16:30", 18))
    put_doc(s, VesselRow, CASE_ID, "vessel_lily", {
        "vesselId": "vessel_lily", "caseId": CASE_ID, "name": "Lily", "nameCn": "莉莉轮", "mmsi": "413990101",
        "imoNumber": "IMO 9900101", "callSign": "BXXX1", "flagState": "船旗国 A（虚构）", "vesselTypeCode": "BulkCarrier",
        "loaM": 189.9, "beamM": 32.26, "draftForeM": 5.2, "draftAftM": 6.8, "displacementTons": 24500,
        "loadingCondition": "Ballast", "colorHex": "#3be3ff"})
    put_doc(s, VesselRow, CASE_ID, "vessel_mary", {
        "vesselId": "vessel_mary", "caseId": CASE_ID, "name": "Mary", "nameCn": "玛丽轮", "mmsi": "351990202",
        "imoNumber": "IMO 9900202", "callSign": "3FXX2", "flagState": "船旗国 B（虚构）", "vesselTypeCode": "ContainerShip",
        "loaM": 225.0, "beamM": 32.2, "draftForeM": 12.4, "draftAftM": 12.8, "displacementTons": 58200,
        "loadingCondition": "FullLoad", "colorHex": "#f97316"})
    for p in track_points():
        s.add(TrackPointRow(case_id=CASE_ID, vessel_id=p["vesselId"], time_sec=p["timeSec"], doc=p))
    seed_evidence(s, blob_root)
    seed_timeline(s)
    seed_interviews(s)
    seed_colreg(s)
    seed_recommendations(s)
    seed_agent_drafts(s)
    put_doc(s, AccessPolicyRow, CASE_ID, "policy", default_policy())
    audit.append(s, case_id=CASE_ID, operator=SEED_OP, role="LeadInvestigator", action="seed.load", category="Case",
                 command="载入虚构演示数据（Lily/Mary）", after="证据 6 / 时间线 12 / 冲突 4 / 笔录 6 / 建议 7 / 草稿 2",
                 entity_type="case", entity_id=CASE_ID, utc=L("10:00", 28))
    return True
