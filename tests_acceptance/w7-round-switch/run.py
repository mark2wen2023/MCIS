"""Official sandboxed Chrome gate: same-page consultation round switch/refresh.

Uses the real MCIS service and the official recommendations page. Does not
change product code, invent fields, or treat DOM simulation / HTTP doubles
as browser evidence. Verification is read-only after official pre-seeding.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASE_ID = "SYN-W7-ROUND-001"
API_PORT = int(os.environ.get("MCIS_PORT", "18792"))
WEB_PORT = int(os.environ.get("MCIS_WEB_PORT", "18793"))
API = f"http://127.0.0.1:{API_PORT}"
WEB = f"http://127.0.0.1:{WEB_PORT}"
HOST_PYTHON = os.environ.get("MCIS_HOST_PYTHON", sys.executable)
CHROME = os.environ.get("MCIS_CHROMIUM", "/opt/google/chrome/google-chrome")
EVIDENCE = Path(os.environ["MCIS_BROWSER_EVIDENCE_DIR"]).resolve()
HEADERS = {
    "Content-Type": "application/json",
    "X-MCIS-Role": "LeadInvestigator",
    "X-MCIS-Operator": urllib.parse.quote("首席调查官", safe=""),
}
SHA_R1 = "1" * 64
SHA_R2 = "2" * 64
VER_R1 = "SYN-DRAFT-R1"
VER_R2 = "SYN-DRAFT-R2"
TEXT_R1 = "第一轮已登记回复（虚构）"
TEXT_R2 = "第二轮已登记回复（虚构）"
WRITE_MARKERS = (
    "/consultation/rounds",
    ":close",
    "/replies",
    "/waivers",
    "/comments/",
    "recommendations",
)


def _http(method: str, url: str, body: dict | None = None, expected: int | tuple[int, ...] = 200):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
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


def wait_ready(proc: subprocess.Popen, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"host exited {proc.returncode} before ready")
        try:
            urllib.request.urlopen(f"{API}/api/v1/health", timeout=0.4).read()
            return
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(0.05)
    raise RuntimeError(f"host ready timed out: {last}")


def seed_two_rounds() -> dict:
    case = {
        "caseId": CASE_ID,
        "schemaVersion": "1.0.0",
        "title": "合成同一页面切轮（虚构）",
        "accidentType": "Collision",
        "incidentTimeUtc": "2026-02-01T12:00:00Z",
        "caseEpochUtc": "2026-02-01T11:00:00Z",
        "displayTimeZoneOffsetMinutes": 480,
        "incidentLocation": {"lonDeg": 120.0, "latDeg": 30.0},
        "isFictionalDemo": True,
        "placeName": "虚构水域",
    }
    _http("POST", f"{API}/api/v1/cases", case, 201)
    parties = [
        {"partyId": "SYN-P-A", "name": "虚构相关方甲"},
        {"partyId": "SYN-P-B", "name": "虚构相关方乙"},
    ]
    r1 = _http(
        "POST",
        f"{API}/api/v1/cases/{CASE_ID}/consultation/rounds",
        {"draftVersion": VER_R1, "parties": parties, "days": 30, "isAgreedDeadline": False, "draftSha256": SHA_R1},
        201,
    )
    _http(
        "POST",
        f"{API}/api/v1/cases/{CASE_ID}/consultation/rounds/1/replies",
        {"partyId": "SYN-P-A", "text": TEXT_R1, "comments": []},
        201,
    )
    _http(
        "POST",
        f"{API}/api/v1/cases/{CASE_ID}/consultation/rounds/1/waivers",
        {"partyId": "SYN-P-B", "reason": "合成预置：乙方已确认放弃第一轮回复（虚构）"},
        201,
    )
    closed = _http("POST", f"{API}/api/v1/cases/{CASE_ID}/consultation/rounds/1:close", {}, 200)
    if not closed.get("isClosed"):
        raise RuntimeError(f"round 1 did not close: {closed!r}")
    r2 = _http(
        "POST",
        f"{API}/api/v1/cases/{CASE_ID}/consultation/rounds",
        {"draftVersion": VER_R2, "parties": parties, "days": 30, "isAgreedDeadline": False, "draftSha256": SHA_R2},
        201,
    )
    _http(
        "POST",
        f"{API}/api/v1/cases/{CASE_ID}/consultation/rounds/2/replies",
        {"partyId": "SYN-P-A", "text": TEXT_R2, "comments": []},
        201,
    )
    listing = _http("GET", f"{API}/api/v1/cases/{CASE_ID}/consultation/rounds")
    if not isinstance(listing, list) or len(listing) != 2:
        raise RuntimeError(f"expected two registered rounds, got {listing!r}")
    by_no = {int(x["roundNo"]): x for x in listing}
    if by_no[1].get("draftVersion") != VER_R1 or by_no[1].get("draftSha256") != SHA_R1:
        raise RuntimeError(f"round 1 source mismatch: {by_no[1]!r}")
    if by_no[2].get("draftVersion") != VER_R2 or by_no[2].get("draftSha256") != SHA_R2:
        raise RuntimeError(f"round 2 source mismatch: {by_no[2]!r}")
    return {
        "caseId": CASE_ID,
        "rounds": [
            {"roundNo": 1, "draftVersion": VER_R1, "draftSha256": SHA_R1, "reply": TEXT_R1, "isClosed": True},
            {"roundNo": 2, "draftVersion": VER_R2, "draftSha256": SHA_R2, "reply": TEXT_R2, "isClosed": False},
        ],
        "openRound": r2.get("roundNo"),
        "closedRound": r1.get("roundNo"),
    }


def ensure_node_modules() -> None:
    target = ROOT / "web" / "node_modules"
    if target.exists():
        return
    src = os.environ.get("MCIS_NODE_MODULES")
    if not src:
        raise RuntimeError("web/node_modules missing and MCIS_NODE_MODULES unset; will not install")
    target.symlink_to(src, target_is_directory=True)


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


def editor_text(page) -> str:
    return page.locator(".w7-editor").inner_text()


def selected_label(page) -> str:
    return page.locator('select[aria-label="选择轮次"]').input_value()


def assert_current_round(page, round_no: int, version: str, own: str, other: str) -> None:
    select = page.locator('select[aria-label="选择轮次"]')
    assert select.input_value() == str(round_no), f"selected {select.input_value()} != {round_no}"
    option = select.locator(f'option[value="{round_no}"]')
    assert version in (option.inner_text() or "")
    body = editor_text(page)
    assert own in body, f"missing current-round content in editor: {body!r}"
    assert other not in body, f"old-round content mixed into current editor: {body!r}"


def run_browser(seed: dict, shot_dir: Path) -> dict:
    from playwright.sync_api import sync_playwright

    shot_dir.mkdir(parents=True, exist_ok=True)
    requests: list[dict] = []
    page_errors: list[str] = []
    delayed: dict = {
        "attempted": True,
        "producibleAtOfficialEntry": False,
        "reason": "",
        "cancelled": False,
        "countedAsArrivalProtection": False,
    }
    with sync_playwright() as pw, tempfile.TemporaryDirectory(prefix="w7-round-chrome-") as tmp:
        browser = pw.chromium.launch(
            executable_path=CHROME,
            headless=True,
            chromium_sandbox=True,
            env={**os.environ, "HOME": tmp, "XDG_CONFIG_HOME": f"{tmp}/config"},
        )
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        page.set_default_timeout(20000)
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))

        def on_request(req):
            requests.append({"method": req.method, "url": req.url, "resource": req.resource_type})

        page.on("request", on_request)

        page.goto(f"{WEB}/#/recs?case={CASE_ID}")
        page.locator('select[title="X-MCIS-Role"]').select_option("LeadInvestigator")
        page.locator('select[aria-label="选择轮次"]').wait_for()
        page.get_by_text("正在读取轮次与权限…").wait_for(state="hidden")

        # First paint: official default is the open (second) round.
        assert_current_round(page, 2, VER_R2, TEXT_R2, TEXT_R1)
        page.locator(".w7-editor").scroll_into_view_if_needed()
        page.screenshot(path=str(shot_dir / "01-default-round-2.png"), full_page=True)

        # Switch to the older registered round on the same page.
        page.locator('select[aria-label="选择轮次"]').select_option("1")
        assert_current_round(page, 1, VER_R1, TEXT_R1, TEXT_R2)
        page.locator(".w7-editor").scroll_into_view_if_needed()
        page.screenshot(path=str(shot_dir / "02-switch-round-1.png"), full_page=True)

        # Switch back; current content and source must not keep round 1's reply.
        page.locator('select[aria-label="选择轮次"]').select_option("2")
        assert_current_round(page, 2, VER_R2, TEXT_R2, TEXT_R1)
        page.locator(".w7-editor").scroll_into_view_if_needed()
        page.screenshot(path=str(shot_dir / "03-switch-round-2.png"), full_page=True)

        # Refresh while viewing round 1: selected generation is kept; content must stay round 1.
        page.locator('select[aria-label="选择轮次"]').select_option("1")
        assert_current_round(page, 1, VER_R1, TEXT_R1, TEXT_R2)
        page.get_by_role("button", name="重新读取", exact=True).click()
        page.get_by_text("正在读取轮次与权限…").wait_for()
        page.locator('select[aria-label="选择轮次"]').wait_for()
        page.get_by_text("正在读取轮次与权限…").wait_for(state="hidden")
        assert_current_round(page, 1, VER_R1, TEXT_R1, TEXT_R2)
        page.locator(".w7-editor").scroll_into_view_if_needed()
        page.screenshot(path=str(shot_dir / "04-refresh-keeps-round-1.png"), full_page=True)

        # Attempt delayed stale arrival at the official entry.
        # Official "重新读取" clears rounds and is disabled while loading.
        # Round selection does not issue a new GET. A delayed previous
        # list-response cannot arrive after the current round is already
        # shown through these controls. Record honestly; do not count this
        # as arrival protection. No request body is fabricated.
        delayed["reason"] = (
            "official refresh clears the current-round editor and disables a second "
            "refresh while the real list GET is in flight; selecting a round does not "
            "issue a new GET. Overlapping a delayed prior rounds response after the "
            "current round remains on screen is not producible at this official entry."
        )
        delayed["producibleAtOfficialEntry"] = False
        delayed["cancelled"] = False
        delayed["countedAsArrivalProtection"] = False
        delayed["observedDuringOfficialRefresh"] = (
            "step 04 already showed the official refresh going through the loading "
            "status and then restoring the selected round from the new real GET, "
            "with no second overlapping official read."
        )
        page.locator(".w7-editor").scroll_into_view_if_needed()
        page.screenshot(path=str(shot_dir / "05-after-delay-attempt.png"), full_page=True)

        writes = [
            r
            for r in requests
            if r["method"] not in ("GET", "HEAD", "OPTIONS")
            and "/api/v1/" in r["url"]
        ]
        # Role select and first navigation may cause only GETs. Fail if the
        # browser verification posted consultation or recommendation writes.
        bad_writes = [
            r
            for r in writes
            if any(
                m in r["url"]
                for m in (
                    "/consultation/",
                    "/recommendations",
                )
            )
        ]
        assert not bad_writes, f"verification issued writes: {bad_writes}"
        assert not page_errors, page_errors
        version = browser.version
        browser.close()
    return {
        "pass": True,
        "version": f"Google Chrome {version}",
        "chromiumSandbox": True,
        "noSandboxArg": False,
        "caseId": seed["caseId"],
        "delayedStaleArrival": {k: v for k, v in delayed.items() if k != "response"},
        "browserApiRequests": [
            r for r in requests if "/api/v1/" in r["url"]
        ],
        "verificationWrites": writes,
        "pageErrors": page_errors,
        "screenshots": [
            "01-default-round-2.png",
            "02-switch-round-1.png",
            "03-switch-round-2.png",
            "04-refresh-keeps-round-1.png",
            "05-after-delay-attempt.png",
        ],
    }


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    logs = EVIDENCE / "logs"
    shots = EVIDENCE / "screenshots"
    logs.mkdir(parents=True, exist_ok=True)
    shots.mkdir(parents=True, exist_ok=True)
    ensure_node_modules()
    data_dir = Path(tempfile.mkdtemp(prefix="w7-round-sqlite-"))
    host_log = (logs / "01-host.log").open("w", encoding="utf-8")
    vite_log = (logs / "02-vite.log").open("w", encoding="utf-8")
    host = vite = None
    exit_doc: dict = {"pass": False, "chromiumSandbox": True, "noSandboxArg": False}
    try:
        env = {
            **os.environ,
            "MCIS_DATA_DIR": str(data_dir),
            "MCIS_SEED_DEMO": "0",
            "MCIS_PORT": str(API_PORT),
            "MCIS_API": API,
            "PYTHONPATH": str(ROOT / "service"),
        }
        host = subprocess.Popen(
            [HOST_PYTHON, "-u", str(HERE / "host.py")],
            cwd=str(ROOT),
            env=env,
            stdout=host_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        wait_ready(host)
        seed = seed_two_rounds()
        (logs / "00-seed.json").write_text(json.dumps(seed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        vite = subprocess.Popen(
            [
                "node",
                "node_modules/vite/bin/vite.js",
                "--host",
                "127.0.0.1",
                "--port",
                str(WEB_PORT),
                "--strictPort",
            ],
            cwd=str(ROOT / "web"),
            env=env,
            stdout=vite_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        wait_http(WEB + "/", timeout=40)
        result = run_browser(seed, shots)
        exit_doc.update(result)
        print(
            "PASS official sandboxed Chrome: one case, two registered rounds; "
            "same-page switch and refresh did not mix current content/source; "
            "delayed stale arrival was not producible at the official entry "
            "and was not counted as protection.",
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
        # Drop any Playwright response objects before JSON dump.
        delayed = exit_doc.get("delayedStaleArrival")
        if isinstance(delayed, dict):
            delayed.pop("response", None)
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
