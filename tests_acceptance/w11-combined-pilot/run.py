#!/usr/bin/env python3
"""W11 combined-pilot gate: reuse same-round evidence if complete; otherwise record the first product-interface breakpoint. No new routes, no fixture core, no direct table writes, no product changes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PIN_CORE = "875ccc50b049fb24b82f6b0663f3f9476db1880e"
PIN_EXCERPT = "41eb599f5a42eb2d0938ad4212936a0949a1cef5"
SDK = "8.0.428"
BLOCK_EXIT = 3

# Product and prior-pilot files as they exist on PIN_CORE (excerpt files unchanged since PIN_EXCERPT).
EXPECTED_SHA256 = {
    "service/mcis_service/ecfc_drafts/router.py": "a3e29516ba1116c4f4876ebeab325d3d3f3364d0061919f96409a14c2979f4b6",
    "tests_acceptance/w11-real-core/workflow.py": "4b01ee4e9fb70e54ad792e0d05b134b696faf797eb604968874abfef15f7a4ec",
    "tests_acceptance/ECFCNEW/http_real.py": "2fe1b3ad833b4af289e7d74b8818c705276c0cb6ea0e7019abcb19a89f0b45c4",
    "tests_acceptance/w11-edge-host-optin/host.py": "9ffcc5152f5de516ade287c8998f68322bb108015ed0d0e4eac2f83b0fbe2255",
    "tests_acceptance/w11-excerpt-binding-local/check.py": "79f0583a1a18edef8cec7f15b8f9c507be29117803f77dc937b68387f116de86",
    "tests_acceptance/w11-excerpt-binding-local/pilot.py": "6d09489264e3bbff5a36576702bf5b91b8536d6f6c991ad78731885de120fe66",
}

PRIOR_EVIDENCE = {
    "dotnetCore": {
        "pin": PIN_CORE,
        "branch": "evidence/w11-core-grokbot-875ccc5",
        "sha": "5d33addffde4565903367276e7ad4e0568860327",
        "zipSha256": "87dbabc691ab77a58a08fecbd78dd78df582a681fb98a42c10eeb21c4bb100d6",
        "scope": "real .NET preview/save/SQLite reopen; not association, excerpt, browser, or HTTP lifecycle",
    },
    "excerptPilot": {
        "pin": "b40a6cacf91ba0d8b297377d31162e404e468e8d",
        "basedOn": PIN_EXCERPT,
        "branch": "evidence/w11-grokbot-b40a6ca",
        "zipSha256": "b2038e908ced208e2787a36d87e96afec9c393d8ab2ba5d5119999abb2365b1f",
        "scope": "explicit excerpt read / revision / revoke / T+109 in isolated host; fixture core + harness-only route + direct pilot_single_source writes",
    },
}

PRODUCT_ECFC_ROUTES = ("/context", "/draft", "/save", "/audit", "/preview")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def die(msg: str, code: int = 1) -> None:
    print("W11 combined pilot stopped: " + msg, file=sys.stderr)
    raise SystemExit(code)


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_sums(root: Path, dest: Path) -> None:
    lines = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "SHA256SUMS"):
        lines.append(f"{sha256(path)}  {path.relative_to(root).as_posix()}")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def preflight(dotnet: Path, logs: Path) -> dict:
    notes = {"dotnetPath": str(dotnet), "dotnetPresent": dotnet.is_file()}
    if not dotnet.is_file():
        notes["dotnetVersion"] = "未验：dotnet 可执行文件不存在"
        return notes
    env = os.environ.copy()
    env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
    env["DOTNET_NOLOGO"] = "1"
    env["DOTNET_ROOT"] = str(dotnet.parent)
    ver = subprocess.check_output([str(dotnet), "--version"], env=env, text=True).strip()
    notes["dotnetVersion"] = ver
    if ver != SDK:
        die(f"SDK preflight failed: got {ver}, required {SDK}")
    loc = subprocess.run([str(dotnet), "nuget", "locals", "all", "--list"], env=env, text=True, capture_output=True)
    (logs / "preflight-nuget-locals.txt").write_text(loc.stdout + loc.stderr, encoding="utf-8")
    notes["nugetLocalsExit"] = loc.returncode
    notes["nugetLocals"] = loc.stdout.strip().splitlines()
    if loc.returncode != 0:
        die("SDK/NuGet preflight failed: dotnet nuget locals all --list exit " + str(loc.returncode))
    return notes


def product_route_inventory(source: Path) -> dict:
    root = source / "service" / "mcis_service"
    routes = []
    excerpt_hits = []
    binding = None
    for path in sorted(root.rglob("*.py")):
        if "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(source).as_posix()
        for m in re.finditer(r"@(?:router|app)\.(get|post|put|patch|delete)\(\s*['\"]([^'\"]+)['\"]", text):
            routes.append({"file": rel, "method": m.group(1).upper(), "path": m.group(2)})
        if re.search(r"edge-excerpt|pilot_single_source|sourceRecordedUtc|read_excerpt", text):
            excerpt_hits.append(rel)
        if "sourceBinding" in text:
            found = re.findall(r"sourceBinding['\"]\s*:\s*['\"]([^'\"]+)['\"]", text)
            if found:
                binding = found[0]
    ecfc = [r for r in routes if "ecfc" in r["file"] or r["path"].startswith("/context") or "/ecfc" in r["path"] or r["path"] in PRODUCT_ECFC_ROUTES]
    return {
        "sourceBinding": binding,
        "ecfcDraftRoutes": [
            r for r in routes if r["file"] == "service/mcis_service/ecfc_drafts/router.py"
        ],
        "productFilesMentioningExcerptBinding": excerpt_hits,
        "hasProductEdgeExcerptRoute": any(
            "edge-excerpt" in (r["path"] or "") or "excerpt" in (r["path"] or "").lower()
            for r in routes
            if "knowledge" not in r["file"] and "reports" not in r["file"]
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--dotnet", type=Path, default=Path("/home/box/.dotnet/dotnet"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    out = args.out
    if out.exists() and any(out.iterdir()):
        die(f"output directory must be empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    logs = out / "logs"
    logs.mkdir()

    source = args.source.resolve()
    head = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    for pin in (PIN_CORE, PIN_EXCERPT):
        r = subprocess.run(["git", "-C", str(source), "merge-base", "--is-ancestor", pin, "HEAD"])
        if r.returncode != 0:
            die(f"source HEAD {head} does not contain pin {pin}")
    changed = subprocess.check_output(
        ["git", "-C", str(source), "diff", "--name-only", PIN_CORE, "HEAD"], text=True
    ).splitlines()
    unexpected = [n for n in changed if not n.startswith("tests_acceptance/w11-combined-pilot/")]
    if unexpected:
        die("source differs from 875ccc50 outside the acceptance directory: " + ", ".join(unexpected))

    fingerprints = {}
    for rel, expected in EXPECTED_SHA256.items():
        path = source / rel
        if not path.is_file():
            die("missing pinned file: " + rel)
        got = sha256(path)
        fingerprints[rel] = {"sha256": got, "matchesExpected": got == expected}
        if got != expected:
            die(f"pinned file hash mismatch: {rel}")

    # Confirm excerpt helpers are unchanged from 41eb599 to this tree.
    unchanged = {}
    for rel in (
        "tests_acceptance/ECFCNEW/http_real.py",
        "tests_acceptance/w11-edge-host-optin/host.py",
        "tests_acceptance/w11-excerpt-binding-local/check.py",
        "tests_acceptance/w11-excerpt-binding-local/pilot.py",
        "service/mcis_service/ecfc_drafts/router.py",
    ):
        data = (source / rel).read_bytes()
        blob = subprocess.check_output(
            ["git", "-C", str(source), "cat-file", "-p", f"{PIN_EXCERPT}:{rel}"]
        )
        unchanged[rel] = data == blob

    sdk = preflight(args.dotnet, logs)
    inventory_routes = product_route_inventory(source)
    (logs / "product-ecfc-routes.json").write_text(
        json.dumps(inventory_routes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # Thresholds vs existing same-round evidence: none of the prior official runs
    # combined real .NET save + registered single-edge excerpt in one process/SQLite
    # through product interfaces without fixture core or direct table writes.
    thresholds = {
        "sameRoundExistingEvidenceCoversAllGates": {
            "result": False,
            "note": "875ccc5 核心复验与 b40a6ca/41eb599 单边原文是两轮分开的官方证据，不是同一轮。",
        },
        "dotnetGeneratedCurrentDraft": {
            "result": "仅在 875ccc5 核心复验中单独满足；组合轮未验",
            "note": "w11-real-core/workflow.py 经原 run_core 预览/保存/同库重开，明确不含 association。",
        },
        "registeredSyntheticExcerptOnThatVersionEdge": {
            "result": "仅在 b40a6ca 单边原文轮中以试点表满足；组合轮未验",
            "note": "登记靠对 pilot_single_source 直写 INSERT，不是产品接口。",
        },
        "excerptOnlyOnExplicitReadIntent": {
            "result": "仅在 b40a6ca 浏览器轮中于试点路由上满足；组合轮未验",
        },
        "readKeepsSpecifiedVersionEdgeExcerpt": {
            "result": "仅在 b40a6ca 轮中于试点适配器上满足；组合轮未验",
        },
        "afterReviseOrUndoOldBindingUnreadable": {
            "result": "仅在 b40a6ca 轮中于试点适配器上满足；组合轮未验",
        },
        "t109OnlyAsRecordedSourceTime": {
            "result": "仅在 b40a6ca 轮中满足（2026-02-01T12:01:49.000Z）；组合轮未验",
        },
        "sqliteAndExistingAuditChecked": {
            "result": "两轮各自核对过，但不是同一库同一轮；组合轮未验",
        },
        "noFixtureCoreOrDirectProductionTableWrites": {
            "result": False,
            "note": "单边原文工装使用 fixture_core，并对试点表直写；不可当作产品动作。",
        },
        "productInterfacesCanCombineWithoutNewRoute": {
            "result": False,
            "note": "产品 ECFC 接口仅有 context/draft/save/audit/preview，sourceBinding=registered-metadata-only。",
        },
    }

    first_break = {
        "file": "service/mcis_service/ecfc_drafts/router.py",
        "version": PIN_CORE,
        "sha256": EXPECTED_SHA256["service/mcis_service/ecfc_drafts/router.py"],
        "alsoIdenticalAt": PIN_EXCERPT,
        "detail": (
            "产品 ECFC 路由只有 GET context、GET draft、POST save、GET audit、POST preview；"
            "context 声明 sourceBinding=registered-metadata-only（约第 322 行）。"
            "不存在按「图版本/边」登记或在明确读取意图下返回通联原文片段的产品接口。"
            "既有单边原文试点在 tests_acceptance/w11-edge-host-optin/host.py 临时增加 "
            "/__local_synthetic_w11/{CASE}/edge-excerpt，并在 "
            "tests_acceptance/w11-excerpt-binding-local/check.py 用 fixture_core 与直写 "
            "pilot_single_source；tests_acceptance/w11-excerpt-binding-local/pilot.py 写明"
            "为测试专用内部适配器、不是 API。"
            "tests_acceptance/ECFCNEW/http_real.py 虽走真实回环 HTTP 预览/保存，但草稿 edges=[]，"
            "不含单边原文登记或读取。"
            "按派遣不得临时开接口或改产品，故停于该首个断点。组合实跑未验。"
        ),
    }

    combined_ran = False
    receipt = {
        "passed": False,
        "blocked": True,
        "blockExit": BLOCK_EXIT,
        "sameRoundEvidenceReused": False,
        "combinedBusinessRun": "未验",
        "httpResultsClaimedAsBrowser": False,
        "cliUsed": False,
        "webUiUsed": False,
        "realCaseUsed": False,
        "productChanged": False,
        "newInterfaceOpened": False,
        "fixtureCoreUsed": False,
        "directTableWritesUsed": False,
        "scope": "interface inventory and evidence comparison only; not W11 whole package",
        "thresholds": thresholds,
        "firstBreakpoint": first_break,
        "priorEvidence": PRIOR_EVIDENCE,
        "productInterfaceInventory": inventory_routes,
        "fingerprints": fingerprints,
        "unchangedFrom41eb599": unchanged,
        "basePin": PIN_CORE,
        "excerptPin": PIN_EXCERPT,
        "basePinReason": "875ccc50 already contains both the real .NET gate and the 41eb599/b40a6ca excerpt tooling, and is the reviewed genuine-.NET pin.",
    }

    if inventory_routes.get("sourceBinding") != "registered-metadata-only":
        die("router sourceBinding was not the expected registered-metadata-only")
    if inventory_routes.get("hasProductEdgeExcerptRoute"):
        die("unexpected product excerpt route appeared; inventory assumption failed")
    if not all(unchanged.values()):
        die("excerpt/router files were expected to match 41eb599 bytes")

    write_json(out / "receipt.json", receipt)
    inventory = {
        "time": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
        "sourceHead": head,
        "basePin": PIN_CORE,
        "excerptPin": PIN_EXCERPT,
        "dotnet": sdk,
        "python": sys.version.replace("\n", " "),
        "combinedBusinessRun": "未验",
        "replayCommand": [
            "timeout", "--signal=TERM", "--kill-after=10s", "150s",
            "python3", "tests_acceptance/w11-combined-pilot/run.py",
            "--source", str(source),
            "--dotnet", str(args.dotnet),
            "--out", "<empty-out>",
        ],
        "scope": receipt["scope"],
    }
    write_json(out / "inventory.json", inventory)
    summary = {
        "passed": False,
        "blocked": True,
        "exit": BLOCK_EXIT,
        "firstBreakpoint": first_break,
        "combinedBusinessRun": "未验",
        "sameRoundEvidenceReused": False,
        "scope": receipt["scope"],
    }
    write_json(out / "summary.json", summary)
    write_sums(out, out / "SHA256SUMS")
    print(json.dumps({
        "passed": False,
        "blocked": True,
        "exit": BLOCK_EXIT,
        "firstBreakpoint": first_break["file"] + " @ " + first_break["version"],
        "out": str(out),
    }, ensure_ascii=False))
    return BLOCK_EXIT


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:
        die(type(exc).__name__ + ": " + str(exc))
