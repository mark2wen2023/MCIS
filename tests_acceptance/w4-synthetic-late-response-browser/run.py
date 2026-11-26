#!/usr/bin/env python3
"""Synthetic-only W4.1 late-response Linux Chrome gate. Does not rerun the preview baseline."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
from contextlib import contextmanager
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler

PIN = "94d5e38c926fda232bb987b60fa9145e4bcf01a7"
CASE_A = "SYN-W41-X-A"
CASE_B = "SYN-W41-X-B"
CASES = {CASE_A: (45, 50), CASE_B: (70, 81)}
EPOCH = "2026-01-01T00:00:00Z"
OPENER = build_opener(ProxyHandler({}))
HOLD_PATH = f"/api/v1/cases/{CASE_A}/timeline/align-preview"
B_PATH = f"/api/v1/cases/{CASE_B}/timeline/align-preview"


def require(condition, name):
    if not condition:
        raise RuntimeError(name)


def step(msg):
    print(f"W41 LATE {time.monotonic():.3f} {msg}", flush=True)


def png_size(path):
    import struct
    data = path.read_bytes()
    width, height = struct.unpack(">II", data[16:24])
    return {"width": width, "height": height, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def viewport_metrics(page):
    return page.evaluate("""() => ({
      innerWidth: window.innerWidth,
      innerHeight: window.innerHeight,
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      scrollHeight: document.documentElement.scrollHeight
    })""")


def require_no_page_overflow(page, when):
    metrics = viewport_metrics(page)
    require(metrics["scrollWidth"] <= metrics["innerWidth"],
            f"document overflows viewport {when}: {metrics}")
    return metrics


def require_result_panel_readable(page, result, when):
    from playwright.sync_api import expect
    result.scroll_into_view_if_needed()
    expect(result).to_be_visible()
    box = result.bounding_box()
    require(box is not None and box["width"] > 0 and box["height"] > 0,
            f"receipt panel has no visible box {when}")
    vp = page.viewport_size
    visible_h = min(box["y"] + box["height"], vp["height"]) - max(box["y"], 0)
    visible_w = min(box["x"] + box["width"], vp["width"]) - max(box["x"], 0)
    require(visible_h > 0 and visible_w > 0, f"receipt panel not in viewport {when}: {box}")
    text = result.inner_text()
    require(bool(text.strip()), f"receipt panel has no readable text {when}")
    return {"box": box, "visibleWidth": visible_w, "visibleHeight": visible_h, "textChars": len(text)}


def gate_json(payload, status=200):
    body = json.dumps(payload, ensure_ascii=False).encode()
    return status, [(b"content-type", b"application/json; charset=utf-8"),
                    (b"content-length", str(len(body)).encode()),
                    (b"cache-control", b"no-store")], body


class PreviewSendGate:
    """Hold only the already-computed A preview response; never rewrite it or block B."""

    def __init__(self, inner):
        self.inner = inner
        self.release = asyncio.Event()
        self.state = {
            "held": False, "sent": False, "sendError": None,
            "status": None, "sha256": None, "bytes": None,
            "computedAt": None, "releasedAt": None, "sentAt": None,
        }

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.inner(scope, receive, send)
            return
        path = scope.get("path") or ""
        method = scope.get("method") or ""
        if path == "/__w41-gate/status" and method == "GET":
            await self._respond(send, *gate_json(self.state))
            return
        if path == "/__w41-gate/release" and method == "POST":
            while True:
                message = await receive()
                if message["type"] == "http.request" and not message.get("more_body"):
                    break
            self.state["releasedAt"] = time.time()
            self.release.set()
            await self._respond(send, *gate_json({"released": True, "sha256": self.state["sha256"],
                                                  "held": self.state["held"], "sent": self.state["sent"]}))
            return
        if method == "POST" and path == HOLD_PATH and not self.state["held"] and not self.state["sent"]:
            await self._hold_a(scope, receive, send)
            return
        await self.inner(scope, receive, send)

    async def _respond(self, send, status, headers, body):
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": body})

    async def _hold_a(self, scope, receive, send):
        start = None
        chunks = []

        async def capture(message):
            nonlocal start
            if message["type"] == "http.response.start":
                start = message
            elif message["type"] == "http.response.body":
                chunks.append(bytes(message.get("body") or b""))

        await self.inner(scope, receive, capture)
        require(start is not None, "A preview produced no HTTP start")
        body = b"".join(chunks)
        self.state.update(held=True, status=start.get("status"),
                          sha256=hashlib.sha256(body).hexdigest(), bytes=len(body),
                          computedAt=time.time())
        try:
            await self.release.wait()
            await send(start)
            await send({"type": "http.response.body", "body": body})
            self.state["sent"] = True
            self.state["sentAt"] = time.time()
            self.state["held"] = False
        except Exception as exc:
            self.state["sendError"] = type(exc).__name__
            raise


def host_entry(assets, data):
    from unittest.mock import patch
    import uvicorn
    from fastapi.staticfiles import StaticFiles
    from mcis_service.config import Settings
    from mcis_service.main import create_app

    cfg = Settings(data_dir=data, db_url=f"sqlite:///{data / 'mcis.db'}", seed_demo=False)
    require(os.environ["MCIS_SEED_DEMO"] == "0", "demo seed not disabled")
    app = create_app(cfg)
    app.mount("/", StaticFiles(directory=assets, html=True))
    gated = PreviewSendGate(app)

    def deny(*args, **kwargs):
        raise RuntimeError("outbound networking prohibited")

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(128)
        print(f"W41_PORT={sock.getsockname()[1]}", flush=True); print("W41 HOST starting uvicorn", flush=True)
        with patch.object(socket.socket, "connect", deny), patch.object(socket.socket, "connect_ex", deny):
            uvicorn.Server(uvicorn.Config(gated, host="127.0.0.1", access_log=False, log_level="warning")).run(sockets=[sock])


def api(origin, path, status, doc=None, method=None):
    req = Request(origin + path, data=None if doc is None else json.dumps(doc).encode(),
                  headers={"X-MCIS-Role": "LeadInvestigator", "X-MCIS-Operator": "SyntheticW41",
                           "Content-Type": "application/json"}, method=method)
    with OPENER.open(req, timeout=8) as res:
        require(res.status == status, "unexpected local service status")
        return json.load(res)


def seed(origin):
    for case in CASES:
        api(origin, "/api/v1/cases", 201,
            {"caseId": case, "title": case, "schemaVersion": "1.0.0", "accidentType": "Collision",
             "incidentTimeUtc": EPOCH, "caseEpochUtc": EPOCH, "incidentLocation": {"latDeg": 0, "lonDeg": 0},
             "displayTimeZoneOffsetMinutes": 0, "isFictionalDemo": True})


def dump(data):
    path = data / "mcis.db"
    require(path.is_file(), "missing SQLite baseline")
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
        return hashlib.sha256("\n".join(db.iterdump()).encode()).hexdigest()


@contextmanager
def service(python, script, work, assets, data, env, output):
    with output.open("x") as err:
        p = subprocess.Popen([str(python), str(script), "--host-entry", str(assets), str(data)],
                             cwd=work, env=env, stdout=subprocess.PIPE, stderr=err, text=True,
                             start_new_session=True)

        def stop_host():
            if p.poll() is not None:
                return
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except ProcessLookupError:
                return
            try:
                p.wait(8)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                p.wait(5)

        try:
            line = p.stdout.readline().strip() if select.select([p.stdout], [], [], 20)[0] else ""
            require(re.fullmatch(r"W41_PORT=[1-9][0-9]{3,4}", line), "loopback service start failed")
            origin = "http://127.0.0.1:" + line.split("=")[1]
            for _ in range(30):
                try:
                    require(api(origin, "/api/v1/health", 200)["status"] == "ok", "unhealthy service")
                    break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError("loopback service not ready")
            yield origin
        finally:
            stop_host()
            if p.stdout:
                p.stdout.close()


def open_case(page, origin, case, *, same_document=False):
    from playwright.sync_api import expect
    target = f"#/evidence?case={case}"
    if same_document:
        # Same-document hash change only. page.goto() with a full URL can start a
        # document navigation and abort the still-held A fetch.
        page.evaluate("hash => { window.location.hash = hash }", target)
    else:
        page.goto(f"{origin}/{target}", timeout=15000)
    disclosure = page.locator(".w4-preview-disclosure")
    expect(disclosure).to_be_visible()
    if disclosure.get_attribute("open") is None:
        disclosure.locator("summary").first.click()
    panel = page.locator(".w4-preview")
    expect(panel.locator("textarea.w4-csv")).to_have_count(1)
    expect(panel.locator("textarea.w4-csv").first).to_have_value("")
    expect(panel.get_by_role("region", name="临时预览结果")).to_have_count(0)
    return panel


def fill_sources(panel, case):
    from playwright.sync_api import expect
    low, high = CASES[case]
    panel.get_by_role("button", name="添加CSV源").click()
    csv_fields = panel.locator("textarea.w4-csv")
    expect(csv_fields).to_have_count(2)
    for i, val in enumerate((low, high)):
        csv_fields.nth(i).fill(f"time_utc,cog_deg\n{EPOCH},{val}\n2026-01-01T00:01:00Z,{val}\n")
        panel.get_by_label("UTC时间列名", exact=True).nth(i).fill("time_utc")
        panel.get_by_label("值列名", exact=True).nth(i).fill("cog_deg")
        mapping = panel.locator("fieldset").nth(i).get_by_role("combobox")
        expect(mapping).to_have_count(1)
        mapping.select_option(value="CourseOverGround")
        expect(mapping).to_have_value("CourseOverGround")
    panel.get_by_role("checkbox").check()
    return high - low


def wait_gate_held(origin, timeout=20):
    deadline = time.monotonic() + timeout
    last = {}
    while time.monotonic() < deadline:
        try:
            last = api(origin, "/__w41-gate/status", 200)
        except OSError:
            last = {}
        if last.get("held") and last.get("sha256") and last.get("status") == 200:
            return last
        step(f"gate poll {last}")
        time.sleep(.25)
    raise RuntimeError(f"A preview was not computed and held in time: {last}")


def late_flow(browser, origin, output, outcome, viewport):
    from playwright.sync_api import expect
    context = browser.new_context(viewport=viewport, service_workers="block")
    blocked, errors = [], []
    events = []

    def block_external(r):
        blocked.append(r.request.url)
        r.abort()

    def note(kind, request):
        url = urlsplit(request.url)
        if request.method == "POST" and url.path in {HOLD_PATH, B_PATH}:
            failure = request.failure
            events.append({
                "at": time.time(),
                "mono": time.monotonic(),
                "kind": kind,
                "path": url.path,
                "failure": None if failure is None else str(failure),
            })

    # Do not intercept loopback HTTP: a Playwright route can swallow or stall the
    # still-held A request. Only block off-loopback traffic.
    context.route("https://**/*", block_external)
    context.route("http://localhost/**/*", block_external)
    context.route("http://[::1]/**/*", block_external)
    context.route_web_socket("**/*", lambda ws: (blocked.append("ws"), ws.close()))
    context.add_init_script("""localStorage.setItem('mcis.role','LeadInvestigator');
                               localStorage.setItem('mcis.operator','SyntheticW41');""")
    page = context.new_page()
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("requestfinished", lambda r: note("finished", r))
    page.on("requestfailed", lambda r: note("failed", r))
    a_request = None
    try:
        step("open A"); panel = open_case(page, origin, CASE_A); step("opened A")
        step("fill A"); fill_sources(panel, CASE_A); step("filled A")
        with page.expect_request(lambda r: r.method == "POST" and urlsplit(r.url).path == HOLD_PATH,
                                 timeout=15000) as pending_a:
            panel.get_by_role("button", name="计算临时预览", exact=True).click()
        a_request = pending_a.value; step("A request started")
        step("waiting for A hold"); held = wait_gate_held(origin); step(f"A held sha={held.get('sha256')}")
        # Do not call request.response() while the send gate still holds A:
        # Playwright waits for the HTTP response and would block until release.
        require(not any(e["kind"] == "finished" and e["path"] == HOLD_PATH for e in events),
                "A finished before release")
        require(not any(e["kind"] == "failed" and e["path"] == HOLD_PATH for e in events),
                "A request failed before release")
        expect(page.get_by_role("region", name="临时预览结果")).to_have_count(0)

        step("open B"); panel = open_case(page, origin, CASE_B, same_document=True); step("opened B")
        step("fill B"); delta_b = fill_sources(panel, CASE_B); step("filled B")
        with page.expect_response(lambda r: r.request.method == "POST" and urlsplit(r.url).path == B_PATH,
                                  timeout=15000) as pending_b:
            panel.get_by_role("button", name="计算临时预览", exact=True).click()
        b_response = pending_b.value; step(f"B HTTP {b_response.status}")
        require(b_response.status == 200, "B preview HTTP status not 200")
        result = page.get_by_role("region", name="临时预览结果")
        expect(result).to_contain_text(CASE_B, timeout=15000)
        expect(result).to_contain_text("未入库")
        expect(result).to_contain_text("未全部校准")
        expect(result).to_contain_text(f"{delta_b} deg")
        expect(result).not_to_contain_text(CASE_A)
        expect(result).not_to_contain_text("5 deg")
        require(any(e["kind"] == "finished" and e["path"] == B_PATH for e in events),
                "B preview did not finish in the browser")
        require(not any(e["kind"] == "finished" and e["path"] == HOLD_PATH for e in events),
                "A finished before B was visible")
        before_release = {
            "caseVisible": result.inner_text(),
            "gate": api(origin, "/__w41-gate/status", 200),
        }
        before_shot = output / f"w41-late-{viewport['width']}-B-11deg-before-release.png"
        page.screenshot(path=str(before_shot))
        outcome["screenshotBeforeRelease"] = png_size(before_shot)
        require(outcome["screenshotBeforeRelease"]["width"] == viewport["width"]
                and outcome["screenshotBeforeRelease"]["height"] == viewport["height"],
                "before-release screenshot is not the requested viewport size")
        outcome["overflowBeforeRelease"] = require_no_page_overflow(page, "before release")
        outcome["receiptPanelBeforeRelease"] = require_result_panel_readable(page, result, "before release")

        step("releasing A"); released = api(origin, "/__w41-gate/release", 200, {}, method="POST"); step("released A")
        outcome["released"] = released
        require(released.get("sha256") == held["sha256"], "release handle did not refer to the held A body")
        deadline = time.monotonic() + 15
        a_finish = None
        a_fail = None
        # Pump the Playwright sync event loop. time.sleep + urllib alone will not
        # deliver page requestfinished callbacks, so a completed A request can be
        # reported only later at context.close().
        while time.monotonic() < deadline:
            a_fail = next((e for e in events if e["kind"] == "failed" and e["path"] == HOLD_PATH), None)
            a_finish = next((e for e in events if e["kind"] == "finished" and e["path"] == HOLD_PATH), None)
            if a_fail or a_finish:
                break
            page.wait_for_timeout(50)
        try:
            outcome["gateAfterWait"] = api(origin, "/__w41-gate/status", 200)
        except OSError as e:
            outcome["gateAfterWaitError"] = type(e).__name__
        outcome["events"] = events
        step(f"after wait finish={a_finish is not None} fail={a_fail} gate={outcome.get('gateAfterWait') or outcome.get('gateAfterWaitError')}")
        require(a_fail is None, "A browser request was cancelled or failed after release")
        require(a_finish is not None, "A browser request never arrived after release")
        b_finish = next(e for e in events if e["kind"] == "finished" and e["path"] == B_PATH)
        require(a_finish["mono"] > b_finish["mono"], "A did not finish after B")
        a_http = a_request.response()
        require(a_http is not None, "A request finished without a browser response")
        require(a_http.status == 200, "A preview HTTP status not 200")
        a_body = a_http.body()
        require(hashlib.sha256(a_body).hexdigest() == held["sha256"],
                "browser A body differs from the held real core response")

        expect(result).to_contain_text(CASE_B)
        expect(result).to_contain_text("未入库")
        expect(result).to_contain_text("未全部校准")
        expect(result).to_contain_text("11 deg")
        expect(result).not_to_contain_text(CASE_A)
        expect(result).not_to_contain_text("5 deg")
        sources = page.locator("textarea.w4-csv")
        expect(sources).to_have_count(2)
        expect(sources.nth(0)).to_contain_text(",70")
        expect(sources.nth(1)).to_contain_text(",81")
        expect(sources.nth(0)).not_to_contain_text(",45")
        expect(sources.nth(1)).not_to_contain_text(",50")
        after_shot = output / f"w41-late-{viewport['width']}-B-after-A-arrived.png"
        page.screenshot(path=str(after_shot))
        outcome["screenshotAfterA"] = png_size(after_shot)
        require(outcome["screenshotAfterA"]["width"] == viewport["width"]
                and outcome["screenshotAfterA"]["height"] == viewport["height"],
                "after-A screenshot is not the requested viewport size")
        outcome["overflowAfterA"] = require_no_page_overflow(page, "after A arrived")
        outcome["receiptPanelAfterA"] = require_result_panel_readable(page, result, "after A arrived")
        require(not blocked and not errors, "external or failed browser event")
        outcome.update({
            "held": held,
            "viewport": viewport,
            "pageOverflow": False,
            "receiptPanelReadable": True,
            "beforeReleaseTextContainsB": CASE_B in before_release["caseVisible"] and "11 deg" in before_release["caseVisible"],
            "events": events,
            "aFinishedAfterB": True,
            "aCancelled": False,
            "aNeverArrived": False,
            "browserBodySha256": hashlib.sha256(a_body).hexdigest(),
            "bStatus": b_response.status,
            "aStatus": a_http.status,
        })
    except Exception as exc:
        outcome["firstFailure"] = str(exc)
        outcome["events"] = events
        outcome["blocked"] = blocked
        outcome["pageErrors"] = errors
        try:
            fail_shot = output / f"w41-late-{viewport['width']}-first-failure.png"
            page.screenshot(path=str(fail_shot))
            outcome["screenshotFirstFailure"] = png_size(fail_shot)
        except Exception:
            pass
        try:
            outcome.setdefault("gateAtFailure", api(origin, "/__w41-gate/status", 200))
        except Exception as gate_exc:
            outcome["gateAtFailureError"] = type(gate_exc).__name__
        raise
    finally:
        context.close()


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("source", "node-modules", "chrome", "host-python", "dotnet", "core-dll", "out"):
        parser.add_argument("--" + flag, type=Path, required=True)
    parser.add_argument("--core-sha256", required=True)
    parser.add_argument("--viewport-width", type=int, default=1440)
    parser.add_argument("--viewport-height", type=int, default=900)
    a = parser.parse_args()
    for key, path in vars(a).items():
        if isinstance(path, Path):
            setattr(a, key, path.absolute())
    require(sys.platform.startswith("linux"), "Linux required")
    for path in (a.chrome, a.host_python, a.dotnet):
        require(path.is_file() and os.access(path, os.X_OK), f"missing executable {path}")
    require(a.core_dll.is_file(), "prebuilt real core DLL missing")
    require(hashlib.sha256(a.core_dll.read_bytes()).hexdigest() == a.core_sha256, "core DLL SHA mismatch")
    version = subprocess.check_output([a.chrome, "--version"], text=True, timeout=10).strip()
    require("Chrome" in version or "Chromium" in version, "not an available Chrome binary")
    require(subprocess.check_output(["git", "-C", a.source, "cat-file", "-t", PIN], text=True).strip() == "commit",
            "missing fixed source commit")
    require((a.node_modules / "vite/bin/vite.js").is_file(), "installed Vite required (no install)")
    a.out.mkdir(exist_ok=False)
    require(a.viewport_width > 0 and a.viewport_height > 0, "viewport must be positive")
    rec = {"revision": PIN, "browser": version, "sandboxRequested": True, "cases": [CASE_A, CASE_B],
           "coreDllSha256": a.core_sha256, "passed": False,
           "viewport": {"width": a.viewport_width, "height": a.viewport_height},
           "scope": "synthetic late preview response at the requested viewport only; not W4 whole package and not a desktop or baseline rerun"}
    script = Path(__file__).resolve()
    try:
        with tempfile.TemporaryDirectory(prefix="w41-late-") as tmp:
            work = Path(tmp)
            tree = work / "source"
            tree.mkdir(); step("work tree ready")
            with subprocess.Popen(["git", "-C", a.source, "archive", PIN, "web", "service", "contracts",
                                   "tests_acceptance/W6/mcis-core-norebuild.sh"],
                                  stdout=subprocess.PIPE) as proc:
                with tarfile.open(fileobj=proc.stdout, mode="r|") as archive:
                    archive.extractall(tree, filter="data")
                require(proc.wait() == 0, "fixed archive failed"); step("archived pinned product")
            web = tree / "web"
            (web / "node_modules").symlink_to(a.node_modules, target_is_directory=True)
            assets = work / "dist"
            data = work / "store"
            data.mkdir()
            env = {"PATH": os.environ["PATH"], "HOME": str(work), "LANG": "C.UTF-8",
                   "PYTHONPATH": str(tree / "service"), "PYTHONDONTWRITEBYTECODE": "1",
                   "MCIS_SEED_DEMO": "0", "MCIS_DATA_DIR": str(data),
                   "MCIS_CORE": str(tree / "tests_acceptance/W6/mcis-core-norebuild.sh"),
                   "MCIS_DOTNET": str(a.dotnet), "MCIS_CORE_DLL": str(a.core_dll),
                   "DOTNET_ROOT": str(a.dotnet.resolve().parent), "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
                   "DOTNET_NOLOGO": "1"}
            node = shutil.which("node")
            require(node, "existing node executable required (no install)")
            with (a.out / "build.log").open("x") as log:
                subprocess.run([node, str(web / "node_modules/vite/bin/vite.js"), "build", "--outDir", str(assets)],
                               check=True, cwd=web, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=120)
            step("vite build done")
            with sync_playwright() as pw:
                browser = pw.chromium.launch(executable_path=str(a.chrome), headless=True,
                                              chromium_sandbox=True, timeout=15000)
                try:
                    rec["browserRuntime"] = browser.version; step("chrome launched")
                    with service(a.host_python, script, work, assets, data, env, a.out / "service-first.log") as origin:
                        step("service first ready")
                        seed(origin)
                        step("cases seeded")
                        rec["sqliteBefore"] = dump(data); step("sqlite before hashed")
                        step("late flow start"); rec["late"] = rec.get("late") or {}; late_flow(browser, origin, a.out, rec["late"], {"width": a.viewport_width, "height": a.viewport_height}); step("late flow done")
                        rec["sqliteAfterLate"] = dump(data)
                        require(rec["sqliteAfterLate"] == rec["sqliteBefore"], "SQLite changed after the late-response sequence")
                    with service(a.host_python, script, work, assets, data, env, a.out / "service-reopened.log") as origin:
                        require(api(origin, "/api/v1/health", 200)["status"] == "ok", "reopened service unhealthy")
                        rec["sqliteAfterReopen"] = dump(data)
                        require(rec["sqliteAfterReopen"] == rec["sqliteBefore"], "SQLite changed after service restart")
                finally:
                    browser.close()
            rec["passed"] = True
    except Exception as exc:
        rec.setdefault("firstFailure", str(exc))
        raise
    finally:
        (a.out / "receipt.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--host-entry":
        host_entry(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        main()
