"""Measure analysis-page widths in sandboxed Chromium. Synthetic loopback only."""
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
from synthetic_seed import CASE_A, CASE_B, TITLE_B, write_seed

PIN = "03a8e7867fedbaaabbf8dd12fc9041d6a1a74cd5"
CHROME = "/opt/google/chrome/chrome"
SAFE_ENV = {k: v for k, v in os.environ.items() if k in ("HOME", "PATH", "LD_LIBRARY_PATH", "LANG", "LC_ALL", "TMPDIR", "XDG_RUNTIME_DIR")}
B_PATH = "/api/v1/cases/" + CASE_B + "/analysis"

OVERFLOW_JS = r"""
() => {
  const iw = window.innerWidth;
  const ih = window.innerHeight;
  const root = document.documentElement;
  const body = document.body;
  const widths = {
    innerWidth: iw,
    innerHeight: ih,
    documentElementScrollWidth: root.scrollWidth,
    documentElementClientWidth: root.clientWidth,
    bodyScrollWidth: body.scrollWidth,
    bodyClientWidth: body.clientWidth,
    overflowing: root.scrollWidth > iw || body.scrollWidth > iw
  };
  const pick = (el) => {
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    let sel = el.tagName.toLowerCase();
    if (el.id) sel += '#' + el.id;
    else if (el.getAttribute('data-testid')) sel += '[data-testid="' + el.getAttribute('data-testid') + '"]';
    else if (el.className && typeof el.className === 'string') {
      const cls = el.className.trim().split(/\s+/).slice(0, 4).join('.');
      if (cls) sel += '.' + cls;
    }
    let path = sel;
    let p = el.parentElement, depth = 0;
    while (p && depth < 5) {
      let ps = p.tagName.toLowerCase();
      if (p.id) ps += '#' + p.id;
      else if (p.getAttribute('data-testid')) ps += '[data-testid="' + p.getAttribute('data-testid') + '"]';
      else if (p.className && typeof p.className === 'string' && p.className.trim())
        ps += '.' + p.className.trim().split(/\s+/).slice(0, 3).join('.');
      path = ps + ' > ' + path;
      p = p.parentElement; depth++;
    }
    return {
      selector: sel,
      path,
      scrollWidth: el.scrollWidth,
      clientWidth: el.clientWidth,
      offsetWidth: el.offsetWidth,
      rectWidth: Math.round(r.width * 100) / 100,
      rectLeft: Math.round(r.left * 100) / 100,
      rectRight: Math.round(r.right * 100) / 100,
      overflowX: cs.overflowX,
      display: cs.display,
      minWidth: cs.minWidth,
      whiteSpace: cs.whiteSpace,
      gridTemplateColumns: cs.gridTemplateColumns,
      flexShrink: cs.flexShrink,
      exceedsViewport: r.right > iw + 1 || el.scrollWidth > iw + 1,
      widerThanClient: el.scrollWidth > el.clientWidth + 1
    };
  };
  const interesting = [
    '.app', '.sidebar', '.topbar', '.topbar-left', '.topbar-right', '.case-chip',
    '.watermark', '.main', '.page-head', '.page-title', '.page-actions',
    '.page-sub', '[data-testid="analysis-page"]', '[data-testid="case-switcher"]',
    '[data-testid="source-banner"]', '[data-testid="series-label"]',
    '[data-testid="key-moments"]', '.an-top', '.p6-card', '[role="status"]',
    '.panel', '.p6-table', '.demo-banner'
  ];
  const listed = [];
  for (const s of interesting) {
    document.querySelectorAll(s).forEach((el) => listed.push(pick(el)));
  }
  const extras = [];
  document.querySelectorAll('body *').forEach((el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 2 && r.height < 2) return;
    if (r.right > iw + 1 || el.scrollWidth > iw + 1) extras.push(pick(el));
  });
  extras.sort((a, b) => b.rectRight - a.rectRight);
  return { widths, listed, overflowingElements: extras.slice(0, 40) };
}
"""


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--worktree", type=Path, required=True)
    parser.add_argument("--browser", type=Path, default=Path(CHROME))
    parser.add_argument("--port", type=int, default=18773)
    parser.add_argument("--label", default="before")
    parser.add_argument("--assets", type=Path)
    parser.add_argument("--also-desktop", action="store_true")
    parser.add_argument("--keyboard", action="store_true")
    args = parser.parse_args()

    worktree = args.worktree.resolve()
    assets = (args.assets or (worktree / "web" / "dist")).resolve()
    if not (assets / "index.html").is_file():
        raise SystemExit("web dist missing")

    report = args.report.resolve()
    out = report / "official" / args.label
    out.mkdir(parents=True, exist_ok=True)
    shots = out / "screenshots"
    shots.mkdir(exist_ok=True)
    logs: list[str] = []

    seed_dir = report / "tmp-official" / f"seed-{args.label}"
    if seed_dir.exists():
        import shutil
        shutil.rmtree(seed_dir)
    seed, sidecar, seed_sha = write_seed(seed_dir)
    store = report / "tmp-official" / f"data-{args.label}"
    if store.exists():
        import shutil
        shutil.rmtree(store)
    store.mkdir(parents=True)
    log(logs, f"label={args.label}; seed={seed_sha}")

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
    origin = f"http://127.0.0.1:{args.port}"
    try:
        wait_http(origin + "/", host, 20)
        from playwright.sync_api import sync_playwright, expect

        def collect(page, name, width, height):
            page.set_viewport_size({"width": width, "height": height})
            data = page.evaluate(OVERFLOW_JS)
            data["viewport"] = {"width": width, "height": height, "name": name}
            return data

        def shot(page, filename, full_page=False):
            path = shots / filename
            page.screenshot(path=str(path), full_page=full_page)
            log(logs, f"screenshot {path} full_page={full_page}")
            return str(path)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                executable_path=str(args.browser),
                headless=True,
                chromium_sandbox=True,
                env=SAFE_ENV,
                args=["--no-proxy-server"],
            )
            try:
                context = browser.new_context(
                    viewport={"width": 390, "height": 844},
                    device_scale_factor=1,
                    service_workers="block",
                )
                held = []
                hold_b = {'on': False}

                def route(r):
                    target = urlsplit(r.request.url)
                    if r.request.url.startswith("data:"):
                        r.continue_(); return
                    if not (target.scheme in {"http", "ws"} and target.hostname == "127.0.0.1" and target.port == args.port):
                        r.abort(); return
                    if hold_b['on'] and is_b_analysis(r.request.url, r.request.method):
                        held.append(r)
                        return
                    r.continue_()

                context.route("**/*", route)
                page = context.new_page()
                page.set_default_timeout(12000)

                log(logs, "390 complete state (case A loaded)")
                page.goto(origin + f"/#/analysis?case={CASE_A}", wait_until="domcontentloaded")
                expect(page.locator('[data-testid="analysis-page"]')).to_be_visible()
                page.wait_for_function("() => document.querySelectorAll('canvas').length >= 1")
                complete = collect(page, "390-complete", 390, 844)
                write_json(out / "widths-390-complete.json", complete)
                shot(page, "390-complete-viewport.png", False)
                shot(page, "390-complete-fullpage.png", True)
                log(logs, f"390 complete innerWidth={complete['widths']['innerWidth']} scrollWidth={complete['widths']['documentElementScrollWidth']}")

                log(logs, "390 waiting state (B analysis held)")
                held.clear()
                hold_b['on'] = True
                page.locator('[data-testid="case-switcher"]').get_by_text(TITLE_B, exact=True).click()
                expect(page.get_by_role("status")).to_contain_text("\u65e7\u5206\u6790\u5df2\u505c\u7528")
                deadline = time.time() + 8
                while time.time() < deadline and not held:
                    page.wait_for_timeout(50)
                if not held:
                    raise SystemExit("B analysis request was not held")
                waiting = collect(page, "390-waiting", 390, 844)
                waiting["heldBRequest"] = True
                waiting["bResponseReturned"] = False
                write_json(out / "widths-390-waiting.json", waiting)
                shot(page, "390-waiting-viewport.png", False)
                shot(page, "390-waiting-fullpage.png", True)
                log(logs, f"390 waiting innerWidth={waiting['widths']['innerWidth']} scrollWidth={waiting['widths']['documentElementScrollWidth']}")
                for r in held:
                    r.continue_()
                hold_b['on'] = False
                expect(page.locator('[data-testid="analysis-page"]')).to_be_visible()

                keyboard = None
                if args.keyboard:
                    log(logs, "keyboard Tab order on 390 complete (case A)")
                    page.goto(origin + f"/#/analysis?case={CASE_A}", wait_until="domcontentloaded")
                    expect(page.locator('[data-testid="analysis-page"]')).to_be_visible()
                    page.wait_for_function("() => document.querySelectorAll('canvas').length >= 1")
                    page.locator("body").click(position={"x": 2, "y": 2})
                    order = []
                    for i in range(24):
                        page.keyboard.press("Tab")
                        info = page.evaluate("""() => {
                          const el = document.activeElement;
                          if (!el || el === document.body) return null;
                          const r = el.getBoundingClientRect();
                          const tag = el.tagName.toLowerCase();
                          const role = el.getAttribute('role') || '';
                          const testid = el.getAttribute('data-testid') || '';
                          const cls = (typeof el.className === 'string' ? el.className : '').trim();
                          const text = (el.innerText || el.value || '').trim().slice(0, 80);
                          const visible = r.width > 0 && r.height > 0 && r.bottom > 0 && r.right > 0
                            && r.top < window.innerHeight && r.left < window.innerWidth;
                          return {tag, role, testid, cls, text, visible,
                                  left: Math.round(r.left), top: Math.round(r.top),
                                  width: Math.round(r.width), height: Math.round(r.height)};
                        }""")
                        if info:
                            order.append({"step": i + 1, "key": "Tab", **info})
                    # activate case switcher via keyboard if focused
                    activated = False
                    for item in order:
                        if "case-switcher" in (item.get("cls") or "") or item.get("role") == "button" and CASE_B in (item.get("text") or "") or TITLE_B in (item.get("text") or ""):
                            pass
                    # Tab to TITLE_B button and press Enter
                    page.locator("body").click(position={"x": 2, "y": 2})
                    found = False
                    for i in range(24):
                        page.keyboard.press("Tab")
                        text = page.evaluate("() => (document.activeElement && (document.activeElement.innerText||'').trim()) || ''")
                        if text == TITLE_B:
                            found = True
                            page.keyboard.press("Enter")
                            break
                    if found:
                        expect(page.locator('[data-testid="source-banner"]')).to_contain_text(CASE_B)
                        activated = True
                    keyboard = {"tabOrder": order, "enterOnCaseB": activated, "foundCaseBControl": found}
                    write_json(out / "keyboard-390.json", keyboard)
                    shot(page, "390-keyboard-after-enter-b.png", False)
                    log(logs, f"keyboard enterOnCaseB={activated} tabs={len(order)}")

                desktop = None
                if args.also_desktop:
                    log(logs, "1440 desktop complete state")
                    page.goto(origin + f"/#/analysis?case={CASE_A}", wait_until="domcontentloaded")
                    page.set_viewport_size({"width": 1440, "height": 900})
                    expect(page.locator('[data-testid="analysis-page"]')).to_be_visible()
                    page.wait_for_function("() => document.querySelectorAll('canvas').length >= 1")
                    page.evaluate("() => { const n = document.querySelector('.nav'); if (n) n.scrollTop = 0; window.scrollTo(0,0); }")
                    desktop = collect(page, "1440-complete", 1440, 900)
                    write_json(out / "widths-1440-complete.json", desktop)
                    shot(page, "1440-complete-viewport.png", False)
                    log(logs, f"1440 innerWidth={desktop['widths']['innerWidth']} scrollWidth={desktop['widths']['documentElementScrollWidth']}")
            finally:
                browser.close()

        summary = {
            "label": args.label,
            "pin": PIN,
            "seedSha256": seed_sha,
            "sandbox": "chromium_sandbox=True",
            "390Complete": complete["widths"],
            "390Waiting": waiting["widths"],
            "1440Complete": (desktop or {}).get("widths") if desktop else None,
            "keyboard": keyboard,
        }
        write_json(out / "summary.json", summary)
        (out / "console.log").write_text("".join(logs), encoding="utf-8")
        return 0
    finally:
        if host.poll() is None:
            host.terminate()
            try:
                host.wait(timeout=8)
            except subprocess.TimeoutExpired:
                host.kill(); host.wait()
        leftover = host.stdout.read() if host.stdout else ""
        (out / "host.log").write_text(leftover or "", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
