#!/usr/bin/env python3
"""Format, ID uniqueness, completeness, and checklist-summary checks only.

Does not score agreement, start a model, or load gold / expected answers.
Exit 0 on success. This package is not formal acceptance.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REQUIRED_IDS = [f"IR-SYN-0{i}" for i in range(1, 7)]
MIN_TURNS = 6
REQUIRED_THEMES = {
    "direct-observation",
    "hearsay",
    "memory-uncertainty",
    "approximate-time-and-units",
    "same-name-roles-disambiguated",
}
FORBIDDEN_FILE_PATTERNS = re.compile(
    r"(gold|expected.?answer|auto.?label|agreement|consistency.rate|一致率|标准答案)",
    re.I,
)
FORBIDDEN_RECORD_KEYS = {
    "statements",
    "gold",
    "expectedAnswers",
    "autoLabels",
    "score",
    "agreementRate",
    "crossCheckResults",
}
TURN_REQUIRED = (
    "turnId",
    "round",
    "askedAtLocal",
    "askedAtUtc",
    "answeredAtLocal",
    "answeredAtUtc",
    "question",
    "answer",
)
TEMPLATE_FIELDS = (
    "annotationId",
    "recordId",
    "turnId",
    "evidenceLocator",
    "statementType",
    "pendingCheck",
    "notComparable",
    "notes",
)
OFFSET = timezone(timedelta(hours=8))


class Failures(list):
    def add(self, msg: str) -> None:
        self.append(msg)


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def parse_iso(value: str, label: str, failures: Failures):
    try:
        dt = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        failures.add(f"{label}: 无法解析时标 {value!r}")
        return None
    if dt.tzinfo is None:
        failures.add(f"{label}: 时标缺少时区 {value!r}")
        return None
    return dt


def check_clock_pair(local, utc, label: str, failures: Failures) -> None:
    loc = parse_iso(local, f"{label}.local", failures)
    u = parse_iso(utc, f"{label}.utc", failures)
    if loc is None or u is None:
        return
    if loc.utcoffset() != timedelta(hours=8):
        failures.add(f"{label}: 本地时标偏移不是 +08:00 ({local})")
    if u.utcoffset() != timedelta(0):
        failures.add(f"{label}: UTC 时标偏移不是 0 ({utc})")
    if loc.astimezone(timezone.utc) != u.astimezone(timezone.utc):
        failures.add(f"{label}: 本地与 UTC 不能互推 ({local} / {utc})")


def check_record(path: Path, rec: dict, failures: Failures) -> None:
    rid = rec.get("recordId", path.stem)
    prefix = f"{path.name}"
    if rec.get("recordId") != path.stem:
        failures.add(f"{prefix}: recordId {rec.get('recordId')!r} 与文件名不一致")
    for key in (
        "synthetic",
        "syntheticDisclaimer",
        "draftStatus",
        "notFormalAcceptance",
        "recordId",
        "caseId",
        "clockDomain",
        "interviewStartedAtLocal",
        "interviewStartedAtUtc",
        "interviewEndedAtLocal",
        "interviewEndedAtUtc",
        "interviewee",
        "turns",
    ):
        if key not in rec:
            failures.add(f"{prefix}: 缺字段 {key}")
    if rec.get("synthetic") is not True:
        failures.add(f"{prefix}: synthetic 必须为 true")
    if rec.get("notFormalAcceptance") is not True:
        failures.add(f"{prefix}: notFormalAcceptance 必须为 true")
    disclaimer = rec.get("syntheticDisclaimer") or ""
    if "虚构" not in disclaimer or "合成" not in disclaimer:
        failures.add(f"{prefix}: 合成声明须同时写明虚构与合成")
    if rec.get("draftStatus") != "pending-human-review-and-freeze":
        failures.add(f"{prefix}: draftStatus 应为 pending-human-review-and-freeze")
    if rec.get("caseId") != "SYN-CASE-W35-2026-0612":
        failures.add(f"{prefix}: caseId 不符合清单")
    for key in FORBIDDEN_RECORD_KEYS:
        if key in rec:
            failures.add(f"{prefix}: 不得包含 {key}")
    clock = rec.get("clockDomain") or {}
    if clock.get("offset") != "+08:00" or clock.get("iana") != "Asia/Shanghai":
        failures.add(f"{prefix}: 钟域须为 Asia/Shanghai / +08:00")
    check_clock_pair(
        rec.get("interviewStartedAtLocal"),
        rec.get("interviewStartedAtUtc"),
        f"{rid}.interviewStart",
        failures,
    )
    check_clock_pair(
        rec.get("interviewEndedAtLocal"),
        rec.get("interviewEndedAtUtc"),
        f"{rid}.interviewEnd",
        failures,
    )
    start = parse_iso(rec.get("interviewStartedAtLocal", ""), f"{rid}.start", failures)
    end = parse_iso(rec.get("interviewEndedAtLocal", ""), f"{rid}.end", failures)
    person = rec.get("interviewee") or {}
    for key in ("intervieweeId", "name", "role", "affiliation", "nameDisambiguation"):
        if not person.get(key):
            failures.add(f"{prefix}: interviewee 缺 {key}")
    turns = rec.get("turns")
    if not isinstance(turns, list) or len(turns) < MIN_TURNS:
        failures.add(f"{prefix}: 须至少 {MIN_TURNS} 轮有上下文问答，实际 {0 if not isinstance(turns, list) else len(turns)}")
        return
    rounds = []
    for i, t in enumerate(turns, start=1):
        for key in TURN_REQUIRED:
            if key not in t:
                failures.add(f"{prefix} 第 {i} 轮缺 {key}")
        expected_id = f"{rid}-T{i:02d}"
        if t.get("turnId") != expected_id:
            failures.add(f"{prefix} 第 {i} 轮 turnId 应为 {expected_id}，实际 {t.get('turnId')!r}")
        if t.get("round") != i:
            failures.add(f"{prefix} 第 {i} 轮 round 应为 {i}")
        if not (t.get("question") or "").strip() or not (t.get("answer") or "").strip():
            failures.add(f"{prefix} 第 {i} 轮问答不能为空")
        if len((t.get("question") or "")) < 8 or len((t.get("answer") or "")) < 20:
            failures.add(f"{prefix} 第 {i} 轮问答过短，不足以构成有上下文的问答")
        check_clock_pair(t.get("askedAtLocal"), t.get("askedAtUtc"), f"{t.get('turnId')}.asked", failures)
        check_clock_pair(
            t.get("answeredAtLocal"), t.get("answeredAtUtc"), f"{t.get('turnId')}.answered", failures
        )
        asked = parse_iso(t.get("askedAtLocal", ""), f"{t.get('turnId')}.asked", failures)
        answered = parse_iso(t.get("answeredAtLocal", ""), f"{t.get('turnId')}.answered", failures)
        if asked and answered and asked > answered:
            failures.add(f"{t.get('turnId')}: 提问时标晚于作答时标")
        if start and asked and asked < start:
            failures.add(f"{t.get('turnId')}: 提问早于笔录开始")
        if end and answered and answered > end:
            failures.add(f"{t.get('turnId')}: 作答晚于笔录结束")
        rounds.append(t.get("round"))
    if rounds != list(range(1, len(turns) + 1)):
        failures.add(f"{prefix}: 轮次必须从 1 连续编号")


def check_template(failures: Failures) -> None:
    tmpl_path = HERE / "annotation_template" / "blank-annotation-template.json"
    csv_path = HERE / "annotation_template" / "blank-annotation-template.csv"
    policy = HERE / "annotation_template" / "POLICY_TO_FREEZE.md"
    if not tmpl_path.is_file():
        failures.add("缺少空白标注模板 JSON")
        return
    tmpl = load_json(tmpl_path)
    if tmpl.get("answersPrefilled") is not False:
        failures.add("标注模板 answersPrefilled 必须为 false")
    if tmpl.get("rows") != []:
        failures.add("标注模板 rows 必须为空，不得预填答案")
    keys = [f.get("key") for f in tmpl.get("fields") or []]
    if keys != list(TEMPLATE_FIELDS):
        failures.add(f"标注模板字段顺序或名称不符: {keys}")
    required = {"evidenceLocator", "statementType"}
    present = {f["key"] for f in tmpl.get("fields") or [] if f.get("key") in required}
    if present != required:
        failures.add("标注模板须包含证据定位与陈述类型字段")
    pending_ok = {"pendingCheck", "notComparable"}.issubset(set(keys))
    if not pending_ok:
        failures.add("标注模板须包含待查与不具可比性字段")
    # No pre-filled enum answers on statementType
    for field in tmpl.get("fields") or []:
        if field.get("key") == "statementType" and field.get("enum"):
            failures.add("陈述类型不得预填枚举答案")
        if field.get("exampleAnswer") or field.get("gold"):
            failures.add(f"模板字段 {field.get('key')} 含预填答案")
    if not csv_path.is_file():
        failures.add("缺少空白标注模板 CSV")
    else:
        text = csv_path.read_text(encoding="utf-8")
        lines = [ln for ln in text.splitlines() if ln.strip()]
        if len(lines) != 1:
            failures.add("CSV 模板只能有表头，不得有数据行")
        else:
            header = lines[0].split(",")
            if header != list(TEMPLATE_FIELDS):
                failures.add(f"CSV 表头不符: {header}")
    if not policy.is_file() or "分母" not in policy.read_text(encoding="utf-8"):
        failures.add("缺少评审口径冻结说明，或未列出分母等待决事项")


def check_package_files(failures: Failures) -> None:
    for path in HERE.rglob("*"):
        if path.is_file() and FORBIDDEN_FILE_PATTERNS.search(path.name):
            failures.add(f"不得提交疑似答案或计分文件: {path.relative_to(HERE)}")


def build_summary(inventory: dict, records: list[dict]) -> str:
    lines = [
        "W3/5 盲标样本草案检查摘要（不是正式验收，不含分数）",
        f"packageId: {inventory.get('packageId')}",
        f"basePin: {inventory.get('basePin')}",
        f"caseId: {inventory.get('caseId')}",
        f"draftStatus: {inventory.get('draftStatus')}",
        "scoringPaused: true",
        "modelsNotUsed: true",
        "",
        "样本清单:",
    ]
    by_id = {r["recordId"]: r for r in records}
    covered = set()
    for item in inventory["samples"]:
        rec = by_id[item["recordId"]]
        themes = ", ".join(item["themeKeys"])
        covered.update(item["themeKeys"])
        person = rec["interviewee"]
        lines.append(
            f"- {rec['recordId']}: {person['name']} / {person['role']} / {person['affiliation']} "
            f"/ intervieweeId={person['intervieweeId']} / 轮次={len(rec['turns'])} "
            f"/ 开始 {rec['interviewStartedAtLocal']} / 结束 {rec['interviewEndedAtLocal']} "
            f"/ 题材标签 {themes}"
        )
    lines.append("")
    lines.append("已覆盖题材标签: " + ", ".join(sorted(covered)))
    lines.append(
        "同名区分: 陈海 → P-SYN-LS-OOW（IR-SYN-01，岚升二副）与 "
        "P-SYN-QY-MASTER（IR-SYN-05，青屿船长）"
    )
    lines.append("空白标注模板: rows=[], CSV 仅表头；未预填答案。")
    lines.append("本摘要不计算一致率，不给出错漏清单或评分。")
    return "\n".join(lines) + "\n"


def main() -> int:
    failures = Failures()
    check_package_files(failures)
    inv_path = HERE / "inventory.json"
    if not inv_path.is_file():
        print("缺少 inventory.json", file=sys.stderr)
        return 1
    inventory = load_json(inv_path)
    if inventory.get("notFormalAcceptance") is not True or inventory.get("scoringPaused") is not True:
        failures.add("inventory 须声明非正式验收且暂停评分")
    if set(inventory.get("requiredThemeKeys") or []) != REQUIRED_THEMES:
        failures.add("inventory.requiredThemeKeys 与派遣要求的题材差异不一致")
    listed = [s.get("recordId") for s in inventory.get("samples") or []]
    if listed != REQUIRED_IDS:
        failures.add(f"清单中的 recordId 应为 {REQUIRED_IDS}，实际 {listed}")

    records = []
    record_ids, turn_ids, interviewee_ids = [], [], []
    names_by_id = {}
    for item in inventory.get("samples") or []:
        path = HERE / item["file"]
        if not path.is_file():
            failures.add(f"缺少样本文件 {item['file']}")
            continue
        rec = load_json(path)
        check_record(path, rec, failures)
        records.append(rec)
        record_ids.append(rec.get("recordId"))
        interviewee_ids.append((rec.get("interviewee") or {}).get("intervieweeId"))
        names_by_id[(rec.get("interviewee") or {}).get("intervieweeId")] = (rec.get("interviewee") or {}).get("name")
        for t in rec.get("turns") or []:
            turn_ids.append(t.get("turnId"))
        if rec.get("recordId") != item.get("recordId"):
            failures.add(f"{item['file']} 与清单 recordId 不一致")
        person = rec.get("interviewee") or {}
        for field in ("intervieweeId", "name", "role", "affiliation"):
            if item.get(field) and item.get(field) != person.get(field):
                failures.add(f"{item['recordId']} 清单字段 {field} 与样本不一致")

    if len(record_ids) != len(set(record_ids)):
        failures.add(f"recordId 不唯一: {record_ids}")
    if len(turn_ids) != len(set(turn_ids)):
        failures.add("turnId 不唯一")
    if len(interviewee_ids) != len(set(interviewee_ids)):
        failures.add(f"intervieweeId 不唯一: {interviewee_ids}")

    chen_ids = {i for i, n in names_by_id.items() if n == "陈海"}
    if chen_ids != {"P-SYN-LS-OOW", "P-SYN-QY-MASTER"}:
        failures.add(f"同名「陈海」须且仅对应 P-SYN-LS-OOW 与 P-SYN-QY-MASTER，实际 {chen_ids}")

    covered = set()
    for item in inventory.get("samples") or []:
        covered.update(item.get("themeKeys") or [])
    missing = REQUIRED_THEMES - covered
    if missing:
        failures.add(f"题材差异覆盖不全: {sorted(missing)}")

    check_template(failures)

    if failures:
        print("检查未通过（退出码 1）：", file=sys.stderr)
        for msg in failures:
            print(f"- {msg}", file=sys.stderr)
        return 1

    summary = build_summary(inventory, records)
    out = HERE / "checklist-summary.txt"
    out.write_text(summary, encoding="utf-8")
    sys.stdout.write(summary)
    print(f"检查通过。退出码 0。摘要已写入 {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
