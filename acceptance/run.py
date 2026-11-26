"""Official browser control: current-case CPA/distance snapshot vs cross-case leak."""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from synthetic_seed import A_MARKERS, B_MARKERS, CASE_A, CASE_B, TITLE_A, TITLE_B, write_seed

PIN = "03a8e7867fedbaaabbf8dd12fc9041d6a1a74cd5"
CHROME = "/opt/google/chrome/chrome"
SAFE_ENV = {k: v for k, v in os.environ.items() if k in ("HOME", "PATH", "LD_LIBRARY_PATH", "LANG", "LC_ALL", "TMPDIR", "XDG_RUNTIME_DIR")}


def log(logs, msg):
    line = msg if msg.endswith("\n") else msg + "\n"
    sys.stdout.write(line)
    sys.stdout.flush()
    logs.append(line)


def write_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha_file(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bind_listeners(pid: int):
    out = subprocess.check_output(["ss", "-ltnp"], text=True, env={**os.environ, "LC_ALL": "C"})
    rows = []
    for line in out.splitlines()[1:]:
        if f"pid={pid}" not in line and f",{pid}," not in line:
            # also include child python host later via port match
            pass
        parts = line.split()
        if len(parts) < 4:
            continue
        local = parts[3]
        if ":" not in local:
            continue
        addr, port = local.rsplit(":", 1)
        rows.append({"raw": line, "addr": addr.lstrip("[").rstrip("]"), "port": int(port) if port.isdigit() else port})
    return rows


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


def snapshot_scope_text(page) -> str:
    """Visible current-case snapshot text, excluding the case switcher list."""
    parts = [
        page.locator(".case-chip").inner_text(),
        page.locator(".demo-banner").inner_text(),
        page.locator(".p6-note").filter(has_text="当前来源快照").inner_text(),
        page.locator('[data-testid="analysis-page"]').inner_text(),
    ]
    text = chr(10).join(parts)
    switcher = page.locator('[data-testid="case-switcher"]').inner_text()
    if switcher:
        text = text.replace(switcher, "")
    return text


def assert_case_only(page, current_markers, other_markers, label):
    text = snapshot_scope_text(page)
    missing = [m for m in current_markers if m not in text]
    leaked = [m for m in other_markers if m in text]
    if missing or leaked:
        raise SystemExit(f"{label}: missing={missing!r} leaked={leaked!r}")


def canvas_count(page) -> int:
    return page.locator("canvas").count()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True, help="preinstalled service Python")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--worktree", type=Path, required=True)
    parser.add_argument("--browser", type=Path, default=Path(CHROME))
    parser.add_argument("--port", type=int, default=18770)
    parser.add_argument("--viewport", choices=("desktop", "390"), default="desktop")
    parser.add_argument("--also-390", action="store_true")
    args = parser.parse_args()

    if not args.python.is_absolute() or not os.access(args.python, os.X_OK):
        raise SystemExit("BLOCKED: preinstalled service Python not found; will not install")
    if not args.browser.is_file():
        raise SystemExit("BLOCKED: Chrome 156 executable not found; will not install")
    worktree = args.worktree.resolve()
    head = subprocess.check_output(["git", "-C", str(worktree), "rev-parse", "HEAD"], text=True).strip()
    if head != PIN:
        diff = subprocess.check_output(["git", "-C", str(worktree), "diff", "--name-only", PIN, "HEAD"], text=True).splitlines()
        allowed_prefix = "tests_acceptance/w12-snapshot-scope-browser/"
        if any(not p.startswith(allowed_prefix) for p in diff):
            raise SystemExit(f"Unexpected changes versus {PIN}: {diff}")

    assets = worktree / "web" / "dist"
    if not (assets / "index.html").is_file():
        raise SystemExit("BLOCKED: web/dist missing; build with existing node_modules first, do not install")

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
    log(logs, f"HEAD={head}; synthetic seed SHA-256={seed_sha}")
    log(logs, "Product historical analysis seed is not loaded.")
    log(logs, f"Existing SSR/build/cjs at 03a8e786 cited only, not re-run as official gates.")

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
        wait_http(origin + f"/api/v1/analysis/cases", host, 10)
        # confirm only synthetic cases
        with urllib.request.urlopen(origin + "/api/v1/analysis/cases", timeout=3) as r:
            listing = json.loads(r.read().decode())
        ids = [c["caseId"] for c in listing["cases"]]
        if ids != [CASE_A, CASE_B]:
            raise SystemExit(f"Unexpected analysis cases: {ids}")
        if listing.get("seedSha256") != seed_sha:
            raise SystemExit("List seedSha256 does not match synthetic sidecar")
        write_json(out / "analysis-cases.json", listing)
        # listeners
        ss = subprocess.check_output(["ss", "-ltnp"], text=True)
        write_json(out / "listeners.txt.json", {"ss": ss, "port": args.port})
        if f"0.0.0.0:{args.port}" in ss or f"[::]:{args.port}" in ss:
            raise SystemExit("Non-loopback bind detected")

        from playwright.sync_api import sync_playwright, expect

        def run_viewport(name: str, width: int, height: int, also_prefix: str | None = None):
            nonlocal first_breakpoint
            prefix = also_prefix or name
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
                    blocked = []

                    def route(r):
                        from urllib.parse import urlsplit
                        target = urlsplit(r.request.url)
                        if target.scheme in {"http", "ws"} and target.hostname == "127.0.0.1" and target.port == args.port:
                            r.continue_()
                        elif target.scheme == "data":
                            r.continue_()
                        else:
                            blocked.append(r.request.url)
                            r.abort()

                    context.route("**/*", route)
                    page = context.new_page()
                    page.set_default_timeout(12000)

                    def snap(filename):
                        path = shots / filename
                        page.screenshot(path=str(path), full_page=True)
                        log(logs, f"screenshot {path}")
                        return path

                    step(f"{name}: open case A snapshot and CPA/distance curve")
                    page.goto(origin + f"/#/analysis?case={CASE_A}", wait_until="domcontentloaded")
                    expect(page.locator('[data-testid="analysis-page"]')).to_be_visible()
                    expect(page.locator('[data-testid="source-banner"]')).to_contain_text(CASE_A)
                    expect(page.locator('[data-testid="source-banner"]')).to_contain_text(TITLE_A)
                    expect(page.locator('[data-testid="series-label"]')).to_contain_text("SYN-W12-A-CURVE")
                    expect(page.locator('[data-testid="key-moments"]')).to_contain_text("SYN-W12-A-MARK")
                    expect(page.get_by_text("当前来源快照")).to_be_visible()
                    expect(page.get_by_text("未确认登记轨迹实时版本")).to_be_visible()
                    # curve canvas must actually paint (ECharts), not a DOM placeholder
                    page.wait_for_function("() => document.querySelectorAll('canvas').length >= 1")
                    if canvas_count(page) < 1:
                        raise SystemExit(f"{name}: CPA/distance curve canvas missing on case A")
                    assert_case_only(page, A_MARKERS, B_MARKERS, f"{name} A")
                    snap(f"01-{prefix}-case-a.png")

                    step(f"{name}: switch to case B; A snapshot and labels must disappear")
                    page.locator('[data-testid="case-switcher"]').get_by_text(TITLE_B, exact=True).click()
                    expect(page.locator('[data-testid="analysis-page"]')).to_be_visible()
                    expect(page.locator('[data-testid="source-banner"]')).to_contain_text(CASE_B)
                    expect(page.locator('[data-testid="source-banner"]')).not_to_contain_text(CASE_A)
                    expect(page.locator('[data-testid="series-label"]')).to_contain_text("SYN-W12-B-CURVE")
                    expect(page.locator('[data-testid="key-moments"]')).to_contain_text("SYN-W12-B-MARK")
                    expect(page.locator('[data-testid="key-moments"]')).not_to_contain_text("SYN-W12-A-MARK")
                    page.wait_for_function("() => document.querySelectorAll('canvas').length >= 1")
                    assert_case_only(page, B_MARKERS, A_MARKERS, f"{name} B")
                    snap(f"02-{prefix}-case-b.png")

                    step(f"{name}: switch back to case A; only A is shown")
                    page.locator('[data-testid="case-switcher"]').get_by_text(TITLE_A, exact=True).click()
                    expect(page.locator('[data-testid="analysis-page"]')).to_be_visible()
                    expect(page.locator('[data-testid="source-banner"]')).to_contain_text(CASE_A)
                    expect(page.locator('[data-testid="source-banner"]')).not_to_contain_text(CASE_B)
                    expect(page.locator('[data-testid="series-label"]')).to_contain_text("SYN-W12-A-CURVE")
                    expect(page.locator('[data-testid="key-moments"]')).to_contain_text("SYN-W12-A-MARK")
                    expect(page.locator('[data-testid="key-moments"]')).not_to_contain_text("SYN-W12-B-MARK")
                    page.wait_for_function("() => document.querySelectorAll('canvas').length >= 1")
                    assert_case_only(page, A_MARKERS, B_MARKERS, f"{name} A-back")
                    snap(f"03-{prefix}-case-a-back.png")
                    write_json(out / f"blocked-urls-{prefix}.json", blocked)
                finally:
                    browser.close()

        if args.viewport == "desktop":
            run_viewport("desktop", 1440, 900)
            ran = ["desktop 1440x900"]
        else:
            run_viewport("390px", 390, 844)
            ran = ["390x844"]

        if args.also_390 and args.viewport == "desktop":
            try:
                run_viewport("390px", 390, 844, also_prefix="390")
                ran.append("390x844")
            except SystemExit as exc:
                untested.append(f"390px not completed: {exc}")
                log(logs, f"390px not completed: {exc}")
        elif args.viewport == "desktop":
            untested.append("390px 未验（本轮先跑桌面 1440x900；未加 --also-390 或时间不足）")
        else:
            untested.append("desktop 未验（本轮先跑 390px）")

        untested.append("同案轨迹换版 未验：页面只显示本次读取的 seedSha256，并写明未确认登记轨迹实时版本；未接登记轨迹换版信号，不伪造版本变化，不把跨案保护算成同案换版通过。")
        untested.append("W12 整包 未验；已有 SSR/构建/合成切案不作为本轮新验收；向量检索与 3D/4A 未验。")

        receipt = {
            "passed": True,
            "kind": "w12-snapshot-scope-browser",
            "pin": PIN,
            "httpNotBrowser": False,
            "browserVerified": True,
            "sandbox": "chromium_sandbox=True",
            "noSandboxFlag": False,
            "viewportsRun": ran,
            "syntheticCases": [CASE_A, CASE_B],
            "seedSha256": seed_sha,
            "trackVersionChange": "未验",
            "notWholePackage": True,
            "untested": untested,
            "sequence": sequence,
            "firstBreakpoint": first_breakpoint,
        }
        write_json(out / "receipt.json", receipt)
        write_json(out / "sequence.json", sequence)
        (out / "console.log").write_text("".join(logs), encoding="utf-8")
        log(logs, f"OFFICIAL RESULT: snapshot-scope browser PASS viewports={ran}; W12 whole-package 未验; track version-change 未验")
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
