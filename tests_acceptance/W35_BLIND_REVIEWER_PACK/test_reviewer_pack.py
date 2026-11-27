#!/usr/bin/env python3
"""Verify reviewer handoff pack: roster, SHA, empty tables, no theme leakage.

Does not contact reviewers, score, start a model, or change transcripts.
This test file is outside the transferable handoff directory.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HANDOFF = HERE / "handoff"
REPO = HERE.parents[1]  # repo root (worktree)
PIN = "c826236f51485c3b380b191b86c5ef48bfb92224"
ORIG = "tests_acceptance/W35_BLIND_LABEL/samples"
IDS = [f"IR-SYN-0{i}" for i in range(1, 7)]
EXPECTED_SHA = {
    "IR-SYN-01": "e59a10fdebdd1e5b1c22a3dfa3f23eeb5dad9f811af95273da33434e01cbdb20",
    "IR-SYN-02": "0a15e3707428e8fd299ad7791277ae72c52c0d6736eb15e921e3a572b05a292d",
    "IR-SYN-03": "78a34df5757c5384dc98efac629fe5a224b682007373481c77ed3eb0aae16bbc",
    "IR-SYN-04": "bbd94918c93e69c099a29567cfb656434437fd8286ac4956304575813cd069c4",
    "IR-SYN-05": "398c7e4c0ccc60a3420244f89cb93807ac654edff8b13fea8ccbe519f504cba5",
    "IR-SYN-06": "f6b26f29463e2acb63383d3a325c5ddda8e536fdbec2caa3c98b1609d1b5d89b",
}

# Organizer theme hints must not appear in the transferable pack,
# except inside the six verbatim transcript files (unchanged source text).
THEME_LEAK = re.compile(
    r"("
    r"题材|themeKeys?|direct-observation|hearsay|memory-uncertainty|"
    r"approximate-time-and-units|same-name-roles-disambiguated|"
    r"直接观察|转述|记忆不确定|近似时间与单位|同名角色|题材差异|题材标签|"
    r"checklist-summary|themeKeyLabels"
    r")",
    re.I,
)
FORBIDDEN_HANDOFF_NAMES = re.compile(
    r"(inventory\.json|checklist-summary|expected.?answer|gold|auto.?label|"
    r"agreement|一致率|标准答案|model-output|组织者)",
    re.I,
)
CONTRA_FIELDS = [
    "annotationId",
    "recordId",
    "turnId",
    "evidenceLocator",
    "controlSourceId",
    "controlVersionOrDigest",
    "controlLocator",
    "conclusion",
    "notComparableReason",
    "notes",
]
EXTRACT_FIELDS = [
    "annotationId",
    "recordId",
    "turnId",
    "sourceField",
    "evidenceLocator",
    "statementType",
    "extractedText",
    "pendingCheck",
    "notes",
]
POLICY_TABLES = {
    "policy-freeze-denominator": None,
    "policy-freeze-miss-and-false-positive": None,
    "policy-freeze-dispute": None,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_show(path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(REPO), "show", f"{PIN}:{path}"])


def fail_list(failures):
    print("检查未通过（退出码 1）：", file=sys.stderr)
    for msg in failures:
        print(f"- {msg}", file=sys.stderr)
    return 1


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def csv_keys(path: Path):
    text = path.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    return lines, [c.strip() for c in lines[0].split(",")] if lines else ([], [])


def check_empty_table(stem: str, required_keys: list[str] | None, failures: list[str]) -> None:
    js = HANDOFF / "templates" / f"{stem}.json"
    cs = HANDOFF / "templates" / f"{stem}.csv"
    if not js.is_file() or not cs.is_file():
        failures.append(f"缺少空表 {stem}")
        return
    obj = load_json(js)
    if obj.get("answersPrefilled") is not False:
        failures.append(f"{stem}: answersPrefilled 必须为 false")
    if obj.get("rows") != []:
        failures.append(f"{stem}: rows 必须为空")
    keys = [f.get("key") for f in obj.get("fields") or []]
    if required_keys and keys != required_keys:
        failures.append(f"{stem}: JSON 字段不符: {keys}")
    lines, header = csv_keys(cs)
    if len(lines) != 1:
        failures.append(f"{stem}.csv 只能有表头，不得有数据行")
    if required_keys and header != required_keys:
        failures.append(f"{stem}.csv 表头不符: {header}")
    if not required_keys and not header:
        failures.append(f"{stem}.csv 缺表头")


def main() -> int:
    failures: list[str] = []
    if not HANDOFF.is_dir():
        print("缺少 handoff 目录", file=sys.stderr)
        return 1

    # Originals on pin must be unchanged; handoff copies must match.
    turn_ids = []
    for rid in IDS:
        orig_path = f"{ORIG}/{rid}.json"
        pinned = git_show(orig_path)
        pinned_sha = sha256_bytes(pinned)
        if pinned_sha != EXPECTED_SHA[rid]:
            failures.append(f"固定原件 SHA 变化: {rid} {pinned_sha}")
        working = (REPO / orig_path).read_bytes()
        if sha256_bytes(working) != EXPECTED_SHA[rid]:
            failures.append(f"工作区原件被改动: {rid}")
        copy = (HANDOFF / "transcripts" / f"{rid}.json").read_bytes()
        if copy != pinned:
            failures.append(f"交件副本与固定原件字节不一致: {rid}")
        if sha256_bytes(copy) != EXPECTED_SHA[rid]:
            failures.append(f"交件副本 SHA 不符: {rid}")
        rec = json.loads(copy.decode("utf-8"))
        if rec.get("recordId") != rid:
            failures.append(f"{rid} recordId 不符")
        turns = rec.get("turns") or []
        if len(turns) != 7:
            failures.append(f"{rid} 轮次不是 7")
        for t in turns:
            turn_ids.append(t.get("turnId"))

    if len(turn_ids) != 42 or len(set(turn_ids)) != 42:
        failures.append(f"问答 ID 应为 42 个且唯一，实际 {len(turn_ids)} / 唯一 {len(set(turn_ids))}")

    sums = HANDOFF / "SHA256SUMS.txt"
    roster = HANDOFF / "roster.csv"
    guide = HANDOFF / "操作说明.md"
    if not sums.is_file():
        failures.append("缺少不含题材的 SHA 清单 SHA256SUMS.txt")
    if not roster.is_file():
        failures.append("缺少名单 roster.csv")
    if not guide.is_file():
        failures.append("缺少无题材提示的操作说明")

    if sums.is_file():
        seen = {}
        for line in sums.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            digest, rel = line.split()
            seen[Path(rel).name.replace(".json", "")] = digest
        if seen != EXPECTED_SHA:
            failures.append(f"SHA256SUMS 与固定原件不一致: {seen}")

    if roster.is_file():
        with roster.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        ids = [r["recordId"] for r in rows]
        if ids != IDS:
            failures.append(f"roster 名单不符: {ids}")
        for r in rows:
            if r["sha256"] != EXPECTED_SHA[r["recordId"]]:
                failures.append(f"roster SHA 不符: {r['recordId']}")
            if "theme" in r or "题材" in r:
                failures.append("roster 含题材列")

    check_empty_table("statement-extraction", EXTRACT_FIELDS, failures)
    check_empty_table("contradiction-review", CONTRA_FIELDS, failures)
    contra = HANDOFF / "templates" / "contradiction-review.json"
    if contra.is_file():
        obj = load_json(contra)
        if obj.get("independentControlMaterialsAvailable") is not False:
            failures.append("矛盾表须声明尚未取得独立对照材料")
        if obj.get("formatOnly") is not True or obj.get("scoringEnabled") is not False:
            failures.append("矛盾表须声明只备格式、暂不能打分")
        if obj.get("controlGroundTruthIncluded") is not False:
            failures.append("矛盾表不得包含对照真值")
        notice = obj.get("notice") or ""
        if "尚未取得独立对照材料" not in notice or "暂不能打分" not in notice:
            failures.append("矛盾表说明未写明只备格式、暂不能打分")
    for stem in POLICY_TABLES:
        check_empty_table(stem, None, failures)

    if guide.is_file():
        text = guide.read_text(encoding="utf-8")
        if "尚未取得独立对照材料" not in text or "暂不能打分" not in text:
            failures.append("操作说明未写明对照材料未取得、矛盾表暂不能打分")
        if "请勿生成或猜测对照" not in text and "请勿生成或猜测对照数据" not in text:
            failures.append("操作说明未写明不得生成或猜测对照真值")

    # Handoff must not include organizer or answer artifacts (except verbatim transcripts).
    for path in HANDOFF.rglob("*"):
        if path.is_file() and FORBIDDEN_HANDOFF_NAMES.search(path.name):
            failures.append(f"交件目录含不应转交的文件: {path.relative_to(HANDOFF)}")

    leak_roots = [p for p in HANDOFF.rglob("*") if p.is_file() and p.parent.name != "transcripts"]
    for path in leak_roots:
        text = path.read_text(encoding="utf-8")
        m = THEME_LEAK.search(text)
        if m:
            failures.append(f"交件材料题材泄露于 {path.relative_to(HANDOFF)}: {m.group(0)}")
        if path.suffix == ".json" and path.parent.name == "templates":
            obj = json.loads(text)
            if obj.get("rows"):
                failures.append(f"{path.name} 预填了行")

    if failures:
        return fail_list(failures)

    summary = [
        "W3/5 盲标交件包检查摘要（不是正式验收，不含分数）",
        f"originalPin: {PIN}",
        "handoff: tests_acceptance/W35_BLIND_REVIEWER_PACK/handoff/",
        "six originals SHA verified against pin; copies byte-identical",
        "roster: IR-SYN-01..06, 42 unique turn IDs",
        "empty tables: statement-extraction, contradiction-review (format-only, no control truth), three policy-freeze tables",
        "no theme leakage in instructions, SHA list, roster, or templates",
        "exit 0",
    ]
    text = "\n".join(summary) + "\n"
    (HERE / "check-summary.txt").write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    print("检查通过。退出码 0。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
