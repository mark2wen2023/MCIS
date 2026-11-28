"""Official sandboxed Chrome gate: ships page, cross-case read-only check.

Uses the real MCIS service and the official `#/ships` page. Does not change
product code. Pre-seeding uses the official registration APIs and is listed
separately; verification is read-only. Desktop 1440 and 390 each run the
same official lobby A→B→A chain.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).absolute().parent
ROOT = HERE.parents[1]
PIN = "9ff7a0488e30fad050d21bafc2bdc7d55d0043da"

CASE_A = "SYN-W9-SHIP-A"
CASE_B = "SYN-W9-SHIP-B"
VESSEL_A = "SYN-V-A"
VESSEL_B = "SYN-V-B"
TITLE_A = "合成船舶案-合法零吃水"
TITLE_B = "合成船舶案-未登记首吃水"
SRC_A = "合成 Direct 来源甲"
SRC_B = "合成估计来源乙"
LOA_A = 96
LOA_B = 72
BEAM_B = 12
DRAFT_FORE_A = 0

INVESTIGATOR = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "X-MCIS-Role": "Investigator",
    "X-MCIS-Operator": "LocalSyntheticInvestigator",
}


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _http(method: str, url: str, headers: dict, body: dict | None = None, expected: int | tuple[int, ...] = 200):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            status = resp.status
            payload = json.loads(raw.decode()) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        raise RuntimeError(f"{method} {url} -> {exc.code}: {raw.decode('utf-8', 'replace')}") from exc
    allowed = expected if isinstance(expected, tuple) else (expected,)
    if status not in allowed:
        raise RuntimeError(f"{method} {url} -> {status}, expected {allowed}")
    return payload


def wait_http(url: str, timeout: float = 40.0) -> None:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1).read()
            return
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(0.1)
    raise RuntimeError(f"startup failed for {url}: {last}")


def wait_ready(proc: subprocess.Popen, api: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"host exited {proc.returncode} before ready")
        try:
            urllib.request.urlopen(f"{api}/api/v1/health", timeout=0.4).read()
            return
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(0.05)
    raise RuntimeError(f"host ready timed out: {last}")


def case_body(case_id: str, title: str) -> dict:
    return {
        "schemaVersion": "1.0.0",
        "caseId": case_id,
        "title": title,
        "accidentType": "Collision",
        "caseEpochUtc": "2026-01-01T00:00:00Z",
        "incidentTimeUtc": "2026-01-01T00:00:00Z",
        "incidentLocation": {"lonDeg": 0, "latDeg": 0},
        "displayTimeZoneOffsetMinutes": 0,
        "isFictionalDemo": True,
    }


def vessel_a() -> dict:
    return {
        "caseId": CASE_A,
        "vesselId": VESSEL_A,
        "name": "合成船甲",
        "loaM": LOA_A,
        "draftForeM": DRAFT_FORE_A,
        "parameterSources": {
            "loaM": {"kind": "Direct", "sourceLabel": SRC_A},
            "draftForeM": {"kind": "Direct", "sourceLabel": SRC_A},
        },
    }


def vessel_b() -> dict:
    return {
        "caseId": CASE_B,
        "vesselId": VESSEL_B,
        "name": "合成船乙",
        "loaM": LOA_B,
        "beamM": BEAM_B,
        "parameterSources": {
            "loaM": {"kind": "Estimated", "sourceLabel": SRC_B},
            "beamM": {"kind": "Estimated", "sourceLabel": SRC_B},
        },
    }


def seed_vessels(api: str) -> dict:
    ops: list[dict] = []
    for case_id, title in ((CASE_A, TITLE_A), (CASE_B, TITLE_B)):
        created = _http("POST", f"{api}/api/v1/cases", INVESTIGATOR, case_body(case_id, title), 201)
        ops.append({"method": "POST", "path": "/api/v1/cases", "status": 201, "caseId": case_id})
        if created.get("caseId") != case_id:
            raise RuntimeError(f"create case unexpected: {created!r}")
    stored_a = _http("POST", f"{api}/api/v1/cases/{CASE_A}/vessels", INVESTIGATOR, vessel_a(), 201)
    ops.append({"method": "POST", "path": f"/api/v1/cases/{CASE_A}/vessels", "status": 201})
    stored_b = _http("POST", f"{api}/api/v1/cases/{CASE_B}/vessels", INVESTIGATOR, vessel_b(), 201)
    ops.append({"method": "POST", "path": f"/api/v1/cases/{CASE_B}/vessels", "status": 201})
    read_a = _http("GET", f"{api}/api/v1/cases/{CASE_A}/vessels", INVESTIGATOR)
    read_b = _http("GET", f"{api}/api/v1/cases/{CASE_B}/vessels", INVESTIGATOR)
    if read_a != [vessel_a()] or stored_a != vessel_a():
        raise RuntimeError(f"case A seed mismatch: {stored_a!r} {read_a!r}")
    if read_b != [vessel_b()] or stored_b != vessel_b():
        raise RuntimeError(f"case B seed mismatch: {stored_b!r} {read_b!r}")
    if "beamM" in (read_a[0] or {}) or "draftForeM" in (read_b[0] or {}):
        raise RuntimeError(f"seed leaked omitted fields: A={read_a!r} B={read_b!r}")
    return {
        "caseA": CASE_A,
        "caseB": CASE_B,
        "vesselA": vessel_a(),
        "vesselB": vessel_b(),
        "preseedOperations": ops,
        "preseedWriteCount": len(ops),
        "preseedVerifyGets": [
            {"method": "GET", "path": f"/api/v1/cases/{CASE_A}/vessels", "body": read_a},
            {"method": "GET", "path": f"/api/v1/cases/{CASE_B}/vessels", "body": read_b},
        ],
    }


def ensure_node_modules(node_modules: Path) -> None:
    target = ROOT / "web" / "node_modules"
    if target.exists():
        return
    if not node_modules.is_dir():
        raise RuntimeError(f"web/node_modules missing and {node_modules} is not a directory; will not install")
    target.symlink_to(node_modules, target_is_directory=True)


def terminate(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=5)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_vessels_get(url: str, case_id: str) -> bool:
    path = urllib.parse.urlparse(url).path.rstrip("/")
    return path == f"/api/v1/cases/{case_id}/vessels"


def dimension_row(page, label: str) -> str:
    section = page.locator('section[aria-label="登记尺寸核对"]')
    rows = section.locator("dt")
    for i in range(rows.count()):
        if (rows.nth(i).inner_text() or "").strip() == label:
            return (rows.nth(i).locator("xpath=following-sibling::dd[1]").inner_text() or "").strip()
    raise RuntimeError(f"dimension row not found: {label}")


def assert_case_a(page, body: list) -> None:
    if body != [vessel_a()]:
        raise RuntimeError(f"case A GET mismatch: {body!r}")
    main = page.locator("section.w9-page")
    text = main.inner_text() or ""
    assert CASE_A in text and TITLE_A in text and VESSEL_A in text and "合成船甲" in text, text
    loa = dimension_row(page, "总长（m）")
    beam = dimension_row(page, "型宽（m）")
    fore = dimension_row(page, "首吃水（m）")
    aft = dimension_row(page, "尾吃水（m）")
    assert f"{LOA_A} · 已登记值" in loa and SRC_A in loa and "【直接】" in loa and "尚未核验" in loa, loa
    assert "未登记 · 不填默认值" in beam and "不能据来源标签推定数值" in beam, beam
    assert SRC_A not in beam
    assert f"{DRAFT_FORE_A} · 已登记值" in fore and SRC_A in fore and "尚未核验" in fore, fore
    assert "未知" not in fore
    assert "未登记 · 不填默认值" in aft
    assert CASE_B not in text and TITLE_B not in text and VESSEL_B not in text and "合成船乙" not in text
    assert SRC_B not in text and str(LOA_B) not in text and str(BEAM_B) not in text
    assert "未提供模型比例" in text


def assert_case_b(page, body: list) -> None:
    if body != [vessel_b()]:
        raise RuntimeError(f"case B GET mismatch: {body!r}")
    main = page.locator("section.w9-page")
    text = main.inner_text() or ""
    assert CASE_B in text and TITLE_B in text and VESSEL_B in text and "合成船乙" in text, text
    loa = dimension_row(page, "总长（m）")
    beam = dimension_row(page, "型宽（m）")
    fore = dimension_row(page, "首吃水（m）")
    aft = dimension_row(page, "尾吃水（m）")
    assert f"{LOA_B} · 已登记值" in loa and SRC_B in loa and "【估计】" in loa and "尚未核验" in loa, loa
    assert f"{BEAM_B} · 已登记值" in beam and SRC_B in beam and "尚未核验" in beam, beam
    assert "未登记 · 不填默认值" in fore and "不能据来源标签推定数值" in fore, fore
    assert f"{DRAFT_FORE_A} · 已登记值" not in fore
    assert "未登记 · 不填默认值" in aft
    assert CASE_A not in text and TITLE_A not in text and VESSEL_A not in text and "合成船甲" not in text
    assert SRC_A not in text and str(LOA_A) not in text


def run_segment(context, web: str, viewport_name: str, shot_dir: Path, prefix: str) -> dict:
    page = context.new_page()
    page.set_default_timeout(20000)
    page_errors: list[str] = []
    requests: list[dict] = []
    page.on("pageerror", lambda exc: page_errors.append(str(exc)))

    def on_request(req):
        requests.append({"method": req.method, "url": req.url, "resource": req.resource_type})

    page.on("request", on_request)

    def open_ships_via_lobby(case_id: str, title: str) -> dict:
        if "/lobby" not in (page.url or ""):
            page.locator("a.nav-item", has_text="案件大厅").click()
        page.get_by_role("heading", name="案件大厅").wait_for()
        page.get_by_role("link", name="进入案件：" + title).click()
        page.get_by_text(case_id, exact=False).first.wait_for()

        def match(resp) -> bool:
            return resp.request.method == "GET" and is_vessels_get(resp.url, case_id) and resp.ok

        with page.expect_response(match, timeout=20000) as pending:
            page.locator("a.nav-item", has_text="船舶参数").click()
        resp = pending.value
        page.get_by_role("heading", name="船舶参数").wait_for()
        page.get_by_text("正在加载案件与船舶…").wait_for(state="hidden")
        page.locator('section[aria-label="登记尺寸核对"]').wait_for()
        return {"url": resp.url, "status": resp.status, "body": resp.json()}

    page.goto(f"{web}/#/lobby")
    page.locator('select[title="X-MCIS-Role"]').wait_for()
    page.locator('select[title="X-MCIS-Role"]').select_option("Investigator")

    first = open_ships_via_lobby(CASE_A, TITLE_A)
    assert_case_a(page, first["body"])
    page.locator('section[aria-label="登记尺寸核对"]').scroll_into_view_if_needed()
    page.screenshot(path=str(shot_dir / f"{prefix}-A.png"), full_page=True)

    second = open_ships_via_lobby(CASE_B, TITLE_B)
    assert_case_b(page, second["body"])
    page.locator('section[aria-label="登记尺寸核对"]').scroll_into_view_if_needed()
    page.screenshot(path=str(shot_dir / f"{prefix}-B.png"), full_page=True)

    third = open_ships_via_lobby(CASE_A, TITLE_A)
    assert_case_a(page, third["body"])
    page.locator('section[aria-label="登记尺寸核对"]').scroll_into_view_if_needed()
    page.screenshot(path=str(shot_dir / f"{prefix}-A-return.png"), full_page=True)

    writes = [r for r in requests if r["method"] not in ("GET", "HEAD", "OPTIONS") and "/api/v1/" in r["url"]]
    assert not writes, f"{viewport_name} verification issued writes: {writes}"
    assert not page_errors, page_errors
    page.close()
    return {
        "viewport": viewport_name,
        "visitA": {"url": first["url"], "status": first["status"], "body": first["body"]},
        "visitB": {"url": second["url"], "status": second["status"], "body": second["body"]},
        "visitAReturn": {"url": third["url"], "status": third["status"], "body": third["body"]},
        "browserApiRequests": [r for r in requests if "/api/v1/" in r["url"]],
        "verificationWrites": writes,
        "verificationWriteCount": len(writes),
        "pageErrors": page_errors,
        "screenshots": [f"{prefix}-A.png", f"{prefix}-B.png", f"{prefix}-A-return.png"],
    }


def run_browser(web: str, chrome: str, shot_dir: Path) -> dict:
    from playwright.sync_api import sync_playwright

    shot_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw, tempfile.TemporaryDirectory(prefix="w9-ships-read-chrome-") as tmp:
        browser = pw.chromium.launch(
            executable_path=chrome,
            headless=True,
            chromium_sandbox=True,
            env={**os.environ, "HOME": tmp, "XDG_CONFIG_HOME": f"{tmp}/config"},
        )
        desktop_ctx = browser.new_context(viewport={"width": 1440, "height": 1100})
        desktop = run_segment(desktop_ctx, web, "desktop-1440", shot_dir, "01-desktop")
        desktop_ctx.close()
        narrow_ctx = browser.new_context(viewport={"width": 390, "height": 844})
        narrow = run_segment(narrow_ctx, web, "narrow-390", shot_dir, "02-390")
        narrow_ctx.close()
        version = browser.version
        browser.close()
    return {
        "pass": True,
        "version": f"Google Chrome {version}",
        "chromiumSandbox": True,
        "noSandboxArg": False,
        "desktop": desktop,
        "narrow390": narrow,
        "verificationWrites": desktop["verificationWrites"] + narrow["verificationWrites"],
        "verificationWriteCount": desktop["verificationWriteCount"] + narrow["verificationWriteCount"],
        "pageErrors": desktop["pageErrors"] + narrow["pageErrors"],
        "screenshots": desktop["screenshots"] + narrow["screenshots"],
    }


def parse_host_log(path: Path) -> tuple[list[dict], list[dict]]:
    if not path.exists():
        return [], []
    recs = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    writes = [r for r in recs if r.get("method") not in ("GET", "HEAD", "OPTIONS")]
    return recs, writes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--host-python", required=True)
    parser.add_argument("--browser", required=True)
    parser.add_argument("--node-modules", required=True)
    args = parser.parse_args()

    evidence = Path(args.evidence).absolute()
    host_python = Path(args.host_python).absolute()
    chrome = str(Path(args.browser).absolute())
    node_modules = Path(args.node_modules).absolute()

    evidence.mkdir(parents=True, exist_ok=True)
    logs = evidence / "logs"
    shots = evidence / "screenshots"
    logs.mkdir(parents=True, exist_ok=True)
    shots.mkdir(parents=True, exist_ok=True)

    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    if head != PIN:
        base_ok = subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", PIN, "HEAD"]).returncode == 0
        if not base_ok:
            raise SystemExit(f"HEAD {head} is not {PIN} or a descendant")
        diff = subprocess.check_output(["git", "-C", str(ROOT), "diff", "--name-only", PIN, "HEAD"], text=True).splitlines()
        allowed = "tests_acceptance/w9-ships-read/"
        if any(not path.startswith(allowed) for path in diff):
            raise SystemExit(f"Unexpected changes versus pin: {diff}")

    ensure_node_modules(node_modules)
    data_dir = Path(tempfile.mkdtemp(prefix="w9-ships-read-sqlite-"))
    api_port = free_port()
    web_port = free_port()
    api = f"http://127.0.0.1:{api_port}"
    web = f"http://127.0.0.1:{web_port}"
    write_log = logs / "host-requests.jsonl"
    host_log = (logs / "01-host.log").open("w", encoding="utf-8")
    vite_log = (logs / "02-vite.log").open("w", encoding="utf-8")
    host = vite = None
    sqlite = data_dir / "mcis.db"
    exit_doc: dict = {
        "pass": False,
        "pin": PIN,
        "chromiumSandbox": True,
        "noSandboxArg": False,
        "api": api,
        "web": web,
    }
    try:
        env = {
            **os.environ,
            "MCIS_DATA_DIR": str(data_dir),
            "MCIS_SEED_DEMO": "0",
            "MCIS_PORT": str(api_port),
            "MCIS_API": api,
            "MCIS_WRITE_LOG": str(write_log),
            "PYTHONPATH": str(ROOT / "service"),
        }
        host = subprocess.Popen(
            [str(host_python), "-u", str(HERE / "host.py")],
            cwd=str(ROOT),
            env=env,
            stdout=host_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        wait_ready(host, api)
        seed = seed_vessels(api)
        after_seed_sha = sha256_file(sqlite) if sqlite.exists() else None
        seed["sqliteAfterPreseedSha256"] = after_seed_sha
        (logs / "00-seed.json").write_text(json.dumps(seed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _, writes_after_seed = parse_host_log(write_log)
        seed_write_count = len(writes_after_seed)
        (logs / "00-seed.json").write_text(
            json.dumps({**seed, "hostWriteCountAfterPreseed": seed_write_count}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        vite = subprocess.Popen(
            [
                "node",
                "node_modules/vite/bin/vite.js",
                "--host",
                "127.0.0.1",
                "--port",
                str(web_port),
                "--strictPort",
            ],
            cwd=str(ROOT / "web"),
            env=env,
            stdout=vite_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        wait_http(web + "/", timeout=40)
        result = run_browser(web, chrome, shots)
        after_browser_sha = sha256_file(sqlite) if sqlite.exists() else None
        if after_browser_sha != after_seed_sha:
            raise RuntimeError(f"sqlite changed during browser read: {after_seed_sha} -> {after_browser_sha}")
        recs, all_writes = parse_host_log(write_log)
        browser_phase_writes = all_writes[seed_write_count:]
        if browser_phase_writes:
            raise RuntimeError(f"host observed writes during browser read: {browser_phase_writes}")
        exit_doc.update(result)
        exit_doc.update(
            {
                "sqliteAfterPreseedSha256": after_seed_sha,
                "sqliteAfterBrowserSha256": after_browser_sha,
                "hostWriteCountAfterPreseed": seed_write_count,
                "hostWriteCountDuringBrowser": len(browser_phase_writes),
                "preseedOperations": seed["preseedOperations"],
            }
        )
        print(
            "PASS official sandboxed Chrome: official #/ships page read registered synthetic vessels; "
            "legal zero, missing beam, and declared sources stayed unverified; A→B→A did not leak; "
            "desktop and 390 read-only, sqlite unchanged.",
            flush=True,
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        exit_doc["error"] = str(exc)
        exit_doc["traceback"] = traceback.format_exc()
        print(f"FAIL {exc}", flush=True)
        traceback.print_exc()
        return 1
    finally:
        (logs / "03-browser-exit.json").write_text(
            json.dumps(exit_doc, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        terminate(vite)
        terminate(host)
        host_log.close()
        vite_log.close()


if __name__ == "__main__":
    sys.exit(main())
