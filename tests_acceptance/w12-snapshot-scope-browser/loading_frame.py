"""Official loading-frame supplement: hold the real B analysis response, do not replace it."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlsplit

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from synthetic_seed import A_MARKERS, B_MARKERS, CASE_A, CASE_B, TITLE_A, TITLE_B, write_seed

PARENT = "9979c087e19e005b9251257048317b13eea421da"
PIN = "03a8e7867fedbaaabbf8dd12fc9041d6a1a74cd5"
LOCKED = {
    "run.py": "ca53bda6aa94623d2ea02a3f7d369537cebacef36afdfad8f6b5bc0174e7f9f8",
    "host.py": "c585232799af34a4d9842e3c265d2ee2dcb28a3d03f2482ad5b99d11cce15969",
    "synthetic_seed.py": "2b48d4dbf3f494bf34415ed160b9cbb8515afe0e801ff1b4bd2532b1f9dfb095",
    "README.md": "2215973baeb685a867e80ede1cefb625e4668a565bd7dd6008050436a3b3425d",
}
CHROME = "/opt/google/chrome/chrome"
SAFE_ENV = {k: v for k, v in os.environ.items() if k in ("HOME", "PATH", "LD_LIBRARY_PATH", "LANG", "LC_ALL", "TMPDIR", "XDG_RUNTIME_DIR")}
B_PATH = "/api/v1/cases/" + CASE_B + "/analysis"
# Case id and labeled values that must not linger from A while B is still pending.
A_ID_AND_METRICS = (
    CASE_A,
    "SYN-W12-A-MARK",
    "SYN-W12-A-CURVE",
    "12:01:00",
    "0.421",
    "0.187",
    "\u5408\u6210\u7532\u672c\u8239",
    "\u5408\u6210\u7532\u76ee\u6807",
)


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def log(logs, msg):
    line = msg if msg.endswith("\n") else msg + "\n"
    sys.stdout.write(line)
    sys.stdout.flush()
    logs.append(line)


def write_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def wait_http(url: str, proc: subprocess.Popen, timeout: float = 20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise SystemExit(f"Host exited {proc.returncode} before ready")
        try:
            with urllib.request.urlopen(url, timeout=1) as r:
                if r.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise SystemExit(f"Host never became ready: {url}")


def is_b_analysis(url: str, method: str) -> bool:
    target = urlsplit(url)
    return method == "GET" and unquote(target.path).rstrip("/") == B_PATH


def snapshot_scope_text(page) -> str:
    return page.locator("body").inner_text()


def assert_no_a(page, label: str):
    text = snapshot_scope_text(page)
    leaked = [m for m in A_ID_AND_METRICS if m in text]
    if leaked:
        raise SystemExit(f"{label}: A case id or metrics still visible: {leaked!r}")


def assert_case_only(page, current_markers, other_markers, label):
    text = snapshot_scope_text(page)
    switcher = ""
    loc = page.locator('[data-testid="case-switcher"]')
    if loc.count():
        switcher = loc.inner_text()
        if switcher:
            text = text.replace(switcher, "")
    missing = [m for m in current_markers if m not in text]
    leaked = [m for m in other_markers if m in text]
    if missing or leaked:
        raise SystemExit(f"{label}: missing={missing!r} leaked={leaked!r}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--worktree", type=Path, required=True)
    parser.add_argument("--browser", type=Path, default=Path(CHROME))
    parser.add_argument("--port", type=int, default=18772)
    parser.add_argument("--viewport", choices=("desktop", "390"), default="desktop")
    parser.add_argument("--also-390", action="store_true")
    args = parser.parse_args()

    if not args.python.is_absolute() or not os.access(args.python, os.X_OK):
        raise SystemExit("BLOCKED: preinstalled service Python not found; will not install")
    if not args.browser.is_file():
        raise SystemExit("BLOCKED: Chrome 156 executable not found; will not install")

    worktree = args.worktree.resolve()
    head = subprocess.check_output(["git", "-C", str(worktree), "rev-parse", "HEAD"], text=True).strip()
    if head != PARENT:
        diff = subprocess.check_output(["git", "-C", str(worktree), "diff", "--name-only", PARENT, "HEAD"], text=True).splitlines()
        allowed = {"tests_acceptance/w12-snapshot-scope-browser/loading_frame.py"}
        if any(p not in allowed for p in diff):
            raise SystemExit(f"Unexpected changes versus {PARENT}: {diff}")
    for name, expected in LOCKED.items():
        actual = sha_file(HERE / name)
        if actual != expected:
            raise SystemExit(f"Locked {name} must stay unchanged: expected {expected}, got {actual}")

    assets = worktree / "web" / "dist"
    if not (assets / "index.html").is_file():
        raise SystemExit("BLOCKED: web/dist missing; reuse the existing 03a8e786 build, do not install")

    report = args.report.resolve()
    report.mkdir(parents=True, exist_ok=True)
    out = report / "official"
    if out.exists():
        import shutil
        shutil.rmtree(out)
    out.mkdir()
    shots = out / "screenshots"
    shots.mkdir()
    logs: list[str] = []
    sequence: list[str] = []
    first_breakpoint = None
    untested: list[str] = []

    def step(name):
        sequence.append(name)
        log(logs, f"STEP {len(sequence)}: {name}")

    seed_dir = report / "tmp-official" / "seed"
    if seed_dir.exists():
        import shutil
        shutil.rmtree(seed_dir)
    seed, sidecar, seed_sha = write_seed(seed_dir)
    store = report / "tmp-official" / "data"
    if store.exists():
        import shutil
        shutil.rmtree(store)
    store.mkdir(parents=True)
    log(logs, f"HEAD={head}; parent={PARENT}; synthetic seed SHA-256={seed_sha}")
    log(logs, "Existing run.py/host.py/synthetic_seed.py/README locked and unchanged.")
    log(logs, "Stable-state official result 9979c08 / 73aa88b / comment 7205529901 is not rerun or replaced.")

    host = subprocess.Popen(
        [
            str(args.python), "-I", "-B", str(HERE / "host.py"),
            str(assets), str(store), str(seed), str(sidecar),
            "127.0.0.1", str(args.port), str(worktree / "service"),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env={k: v for k, v in os.environ.items()
             if k not in {"HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY"}
             and not k.startswith("MCIS_")},
    )
    host_log = out / "host.log"
    origin = f"http://127.0.0.1:{args.port}"
    try:
        step("start 127.0.0.1 service+web")
        wait_http(origin + "/", host, 20)
        with urllib.request.urlopen(origin + "/api/v1/analysis/cases", timeout=3) as r:
            listing = json.loads(r.read().decode())
        ids = [c["caseId"] for c in listing["cases"]]
        if ids != [CASE_A, CASE_B]:
            raise SystemExit(f"Unexpected analysis cases: {ids}")
        write_json(out / "analysis-cases.json", listing)
        ss = subprocess.check_output(["ss", "-ltnp"], text=True)
        write_json(out / "listeners.txt.json", {"ss": ss, "port": args.port})
        if f"0.0.0.0:{args.port}" in ss or f"[::]:{args.port}" in ss:
            raise SystemExit("Non-loopback bind detected")

        from playwright.sync_api import sync_playwright, expect

        def run_viewport(name: str, width: int, height: int, prefix: str):
            nonlocal first_breakpoint
            with sync_playwright() as pw:
                try:
                    browser = pw.chromium.launch(
                        executable_path=str(args.browser),
                        headless=True,
                        chromium_sandbox=True,
                        env=SAFE_ENV,
                        args=["--no-proxy-server"],
                    )
                except Exception as exc:
                    first_breakpoint = {
                        "reason": "Chromium failed to start with normal sandbox; will not use --no-sandbox",
                        "error": str(exc),
                    }
                    raise SystemExit(f"BLOCKED: sandbox Chromium failed: {exc}") from exc
                try:
                    context = browser.new_context(
                        viewport={"width": width, "height": height},
                        device_scale_factor=1,
                        service_workers="block",
                    )
                    blocked: list[str] = []
                    requests: list[dict] = []
                    responses: list[dict] = []
                    held: list[dict] = []

                    def on_request(req):
                        requests.append({
                            "t": time.time(), "method": req.method, "url": req.url,
                            "isBAnalysis": is_b_analysis(req.url, req.method),
                        })

                    def on_response(resp):
                        responses.append({
                            "t": time.time(), "method": resp.request.method, "url": resp.url,
                            "status": resp.status,
                            "isBAnalysis": is_b_analysis(resp.url, resp.request.method),
                        })

                    def route(r):
                        target = urlsplit(r.request.url)
                        if r.request.url.startswith("data:"):
                            r.continue_()
                            return
                        if not (target.scheme in {"http", "ws"} and target.hostname == "127.0.0.1" and target.port == args.port):
                            blocked.append(r.request.url)
                            r.abort()
                            return
                        if is_b_analysis(r.request.url, r.request.method):
                            held.append({
                                "url": r.request.url,
                                "method": r.request.method,
                                "heldAt": time.time(),
                                "continuedAt": None,
                                "route": r,
                            })
                            log(logs, f"HOLD real B analysis {r.request.method} {r.request.url}")
                            return
                        r.continue_()

                    context.route("**/*", route)
                    page = context.new_page()
                    page.on("request", on_request)
                    page.on("response", on_response)
                    page.set_default_timeout(12000)

                    def snap(filename):
                        path = shots / filename
                        page.screenshot(path=str(path), full_page=True)
                        log(logs, f"screenshot {path}")
                        return str(path)

                    step(f"{name}: A already visible")
                    page.goto(origin + f"/#/analysis?case={CASE_A}", wait_until="domcontentloaded")
                    expect(page.locator('[data-testid="analysis-page"]')).to_be_visible()
                    expect(page.locator('[data-testid="source-banner"]')).to_contain_text(CASE_A)
                    expect(page.locator('[data-testid="key-moments"]')).to_contain_text("SYN-W12-A-MARK")
                    page.wait_for_function("() => document.querySelectorAll('canvas').length >= 1")
                    assert_case_only(page, A_MARKERS, B_MARKERS, f"{name} A")
                    snap(f"01-{prefix}-case-a.png")

                    step(f"{name}: switch to B and hold the real B analysis request")
                    held.clear()
                    page.locator('[data-testid="case-switcher"]').get_by_text(TITLE_B, exact=True).click()
                    expect(page.get_by_role("status")).to_contain_text("\u65e7\u5206\u6790\u5df2\u505c\u7528")
                    deadline = time.time() + 8
                    while time.time() < deadline and not held:
                        page.wait_for_timeout(50)
                    if not held:
                        first_breakpoint = {
                            "reason": "B analysis request was not intercepted; loading frame cannot be evidenced",
                        }
                        raise SystemExit("BLOCKED: B analysis request was not held; \u7b49\u5019\u5e27\u672a\u9a8c")

                    b_responses_during_hold = [row for row in responses if row["isBAnalysis"]]
                    evidence = {
                        "viewport": name,
                        "heldRequests": [{k: v for k, v in row.items() if k != "route"} for row in held],
                        "bResponsesBeforeRelease": b_responses_during_hold,
                        "bRequestSeen": True,
                        "bResponseReturnedBeforeRelease": bool(b_responses_during_hold),
                    }
                    write_json(out / f"hold-evidence-{prefix}.json", evidence)
                    if b_responses_during_hold:
                        first_breakpoint = {
                            "reason": "B analysis response already returned while the route should still be held",
                            "responses": b_responses_during_hold,
                        }
                        raise SystemExit("B response returned before release; loading frame is not valid")

                    assert_no_a(page, f"{name} loading-frame")
                    loading_text = page.get_by_role("status").inner_text()
                    log(logs, f"loading visible: {loading_text!r}; held={len(held)}; B response not yet returned")
                    snap(f"02-{prefix}-loading-b-held.png")

                    step(f"{name}: release the real B response, then B is shown")
                    released_at = time.time()
                    for row in list(held):
                        row["route"].continue_()
                        row["continuedAt"] = time.time()
                    expect(page.locator('[data-testid="analysis-page"]')).to_be_visible()
                    expect(page.locator('[data-testid="source-banner"]')).to_contain_text(CASE_B)
                    expect(page.locator('[data-testid="source-banner"]')).not_to_contain_text(CASE_A)
                    expect(page.locator('[data-testid="key-moments"]')).to_contain_text("SYN-W12-B-MARK")
                    page.wait_for_function("() => document.querySelectorAll('canvas').length >= 1")
                    assert_case_only(page, B_MARKERS, A_MARKERS, f"{name} B-after-release")
                    snap(f"03-{prefix}-case-b.png")
                    write_json(out / f"hold-evidence-{prefix}.json", {
                        **evidence,
                        "releasedAt": released_at,
                        "heldRequests": [{k: v for k, v in row.items() if k != "route"} for row in held],
                        "bResponsesAfterRelease": [row for row in responses if row["isBAnalysis"]],
                    })

                    step(f"{name}: switch back to A; only A is shown")
                    page.locator('[data-testid="case-switcher"]').get_by_text(TITLE_A, exact=True).click()
                    expect(page.locator('[data-testid="analysis-page"]')).to_be_visible()
                    expect(page.locator('[data-testid="source-banner"]')).to_contain_text(CASE_A)
                    expect(page.locator('[data-testid="source-banner"]')).not_to_contain_text(CASE_B)
                    expect(page.locator('[data-testid="key-moments"]')).to_contain_text("SYN-W12-A-MARK")
                    page.wait_for_function("() => document.querySelectorAll('canvas').length >= 1")
                    assert_case_only(page, A_MARKERS, B_MARKERS, f"{name} A-back")
                    snap(f"04-{prefix}-case-a-back.png")
                    write_json(out / f"blocked-urls-{prefix}.json", blocked)
                    write_json(out / f"network-{prefix}.json", {"requests": requests, "responses": responses})
                finally:
                    browser.close()

        ran = []
        if args.viewport == "desktop":
            run_viewport("desktop", 1440, 900, "desktop")
            ran.append("desktop 1440x900")
        else:
            run_viewport("390px", 390, 844, "390")
            ran.append("390x844")

        if args.also_390 and args.viewport == "desktop":
            try:
                run_viewport("390px", 390, 844, "390")
                ran.append("390x844")
            except SystemExit as exc:
                untested.append(f"390px loading frame \u672a\u9a8c: {exc}")
                log(logs, f"390px not completed: {exc}")
        elif args.viewport == "desktop":
            untested.append("390px \u7b49\u5019\u5e27\u672a\u9a8c\uff08\u672c\u8f6e\u5148\u8dd0\u684c\u9762 1440x900\uff09")
        else:
            untested.append("desktop \u7b49\u5019\u5e27\u672a\u9a8c\uff08\u672c\u8f6e\u5148\u8dd0 390px\uff09")

        untested.append("\u540c\u6848\u8f68\u8ff9\u6362\u7248 \u672a\u9a8c\uff1b\u7a33\u5b9a\u6001\u8de8\u6848\u7ed3\u679c\u4ee5 7205529901 / 9979c08 \u4e3a\u51c6\uff0c\u672c\u8f6e\u4e0d\u66ff\u4ee3\u3002")
        untested.append("W12 \u6574\u5305 \u672a\u9a8c\u3002")

        receipt = {
            "passed": True,
            "kind": "w12-loading-frame",
            "pin": PIN,
            "parentCandidate": PARENT,
            "stableStateUnchanged": {
                "candidate": PARENT,
                "evidence": "73aa88bf6378893f83c4f3789ceef89f7da5971d",
                "comment": "7205529901",
                "sheetRow": 48,
            },
            "browserVerified": True,
            "httpNotBrowser": False,
            "sandbox": "chromium_sandbox=True",
            "noSandboxFlag": False,
            "routeContinueDelayed": True,
            "responseReplaced": False,
            "viewportsRun": ran,
            "syntheticCases": [CASE_A, CASE_B],
            "seedSha256": seed_sha,
            "notWholePackage": True,
            "untested": untested,
            "sequence": sequence,
            "firstBreakpoint": first_breakpoint,
        }
        write_json(out / "receipt.json", receipt)
        write_json(out / "sequence.json", sequence)
        log(logs, f"OFFICIAL RESULT: loading-frame PASS viewports={ran}; W12 whole-package \u672a\u9a8c; stable-state 7205529901 unchanged")
        (out / "console.log").write_text("".join(logs), encoding="utf-8")
        return 0
    finally:
        if host.poll() is None:
            host.terminate()
            try:
                host.wait(timeout=8)
            except subprocess.TimeoutExpired:
                host.kill()
                host.wait()
        leftover = host.stdout.read() if host.stdout else ""
        host_log.write_text(leftover or "", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
