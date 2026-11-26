#!/usr/bin/env python3
"""Isolated W15 AcciMap synthetic-sketch Linux Chrome gate. Does not change product source."""
import argparse, hashlib, json, os, shutil, struct, subprocess, sys, tempfile, time
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit

PIN = "2447b14076bbf39db014b8bf4a3a3b350cbf0e05"
COMPONENT = "web/src/accimapPreview/Diagram.tsx"
COMPONENT_SHA256 = "d6f67ba6d80b19b7a1c212a02ee6ac0bfc7903f6d067affd2acba4e6210c875f"
REGION = "AcciMap 草图可滚动区域"
LIST_SUMMARY = "查看全部输入节点（完整名称）"
VIEWPORTS = ((1440, 900), (390, 844))
LAYERS = [
    ("政府与法规", "SYN-GOV-LONG-IDENTIFIER-001", "政府层必须完整保留的合成长名称甲"),
    ("监管", "SYN-REG-LONG-IDENTIFIER-001", "监管层必须完整保留的合成长名称乙"),
    ("公司", "SYN-CO-LONG-IDENTIFIER-001", "这是必须完整保留且不能只显示十个汉字的合成节点说明"),
    ("船舶管理", "SYN-MGT-LONG-IDENTIFIER-001", "船舶管理层必须完整保留的合成长名称癸"),
    ("船员行为", "SYN-CREW-LONG-IDENTIFIER-001", "船员行为层必须完整保留的合成长名称子"),
    ("设备与环境", "SYN-EQ-LONG-IDENTIFIER-001", "设备与环境层必须完整保留的合成长名称丑"),
]
COMPANY_FULL = [
    "这是必须完整保留且不能只显示十个汉字的合成节点说明",
    "公司层合成节点丙必须完整显示",
    "公司层合成节点丁必须完整显示",
    "公司层合成节点戊必须完整显示",
    "公司层合成节点己必须完整显示",
    "公司层合成节点庚必须完整显示",
    "公司层合成节点辛必须完整显示",
    "公司层合成节点壬必须完整显示",
]


def require(condition, name):
    if not condition:
        raise RuntimeError(name)


def step(msg):
    print(f"W15 ACCIMAP {time.monotonic():.3f} {msg}", flush=True)


def png_size(path):
    data = path.read_bytes()
    width, height = struct.unpack(">II", data[16:24])
    return {"width": width, "height": height, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@contextmanager
def serve(root):
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def log_message(self, format, *args):
            return

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        thread.join(8)
        httpd.server_close()


def metrics(page):
    return page.evaluate(
        """() => {
          const region = document.querySelector('[role="region"][aria-label="AcciMap 草图可滚动区域"]');
          const doc = document.documentElement;
          return {
            innerWidth: window.innerWidth,
            innerHeight: window.innerHeight,
            pageScrollWidth: doc.scrollWidth,
            pageClientWidth: doc.clientWidth,
            pageScrollLeft: Math.max(doc.scrollLeft, window.scrollX || 0),
            bodyScrollWidth: document.body ? document.body.scrollWidth : null,
            regionScrollWidth: region ? region.scrollWidth : null,
            regionClientWidth: region ? region.clientWidth : null,
            regionScrollLeft: region ? region.scrollLeft : null,
            widerThanContainer: !!(region && region.scrollWidth > region.clientWidth),
          };
        }"""
    )


def focus_info(page):
    return page.evaluate(
        """() => {
          const el = document.activeElement;
          if (!el) return null;
          const cs = getComputedStyle(el);
          const r = el.getBoundingClientRect();
          return {
            tag: el.tagName,
            role: el.getAttribute('role'),
            ariaLabel: el.getAttribute('aria-label'),
            outline: cs.outline,
            outlineWidth: cs.outlineWidth,
            outlineStyle: cs.outlineStyle,
            outlineColor: cs.outlineColor,
            outlineOffset: cs.outlineOffset,
            boxShadow: cs.boxShadow,
            rect: {x: r.x, y: r.y, width: r.width, height: r.height},
          };
        }"""
    )


def no_page_overflow(m, when):
    require(m["pageScrollWidth"] <= m["innerWidth"],
            f"document overflows viewport {when}: {m}")


def flow(browser, origin, width, height, output, rec_view):
    from playwright.sync_api import expect
    context = browser.new_context(viewport={"width": width, "height": height}, service_workers="block")
    blocked, errors = [], []

    def block_external(r):
        blocked.append(r.request.url)
        r.abort()

    context.route("https://**/*", block_external)
    context.route("http://localhost/**/*", block_external)
    context.route("http://[::1]/**/*", block_external)
    context.route_web_socket("**/*", lambda ws: (blocked.append("ws"), ws.close()))
    page = context.new_page()
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    tag = str(width)
    try:
        step(f"{tag} open")
        page.goto(origin + "/", timeout=15000)
        region = page.get_by_role("region", name=REGION, exact=True)
        expect(region).to_be_visible(timeout=15000)
        before = metrics(page)
        rec_view["before"] = before
        step(f"{tag} before {before}")
        require(page.viewport_size == {"width": width, "height": height}, "viewport size mismatch")
        require(before["widerThanContainer"], "diagram is not wider than its frame")
        no_page_overflow(before, f"{tag} before Tab")
        require(before["regionScrollLeft"] == 0, "diagram already scrolled before ArrowRight")

        page.keyboard.press("Tab")
        focused = focus_info(page)
        rec_view["focus"] = focused
        step(f"{tag} focus {focused}")
        require(focused and focused.get("ariaLabel") == REGION,
                f"Tab did not enter the named diagram region: {focused}")
        require(
            (focused.get("outlineStyle") not in (None, "", "none") and focused.get("outlineWidth") not in (None, "", "0px"))
            or (focused.get("boxShadow") not in (None, "", "none")),
            f"no visible focus evidence on the diagram region: {focused}",
        )
        focus_shot = output / f"w15-accimap-{tag}-focus.png"
        page.screenshot(path=str(focus_shot))
        rec_view["screenshotFocus"] = png_size(focus_shot)
        require(rec_view["screenshotFocus"]["width"] == width and rec_view["screenshotFocus"]["height"] == height,
                f"{tag} focus screenshot is not the requested viewport size")

        before_arrow = metrics(page)
        rec_view["beforeArrow"] = before_arrow
        no_page_overflow(before_arrow, f"{tag} before ArrowRight")
        page.keyboard.press("ArrowRight")
        after_arrow = metrics(page)
        rec_view["afterArrow"] = after_arrow
        step(f"{tag} after ArrowRight {after_arrow}")
        after_shot = output / f"w15-accimap-{tag}-after-arrow.png"
        page.screenshot(path=str(after_shot))
        rec_view["screenshotAfterArrow"] = png_size(after_shot)
        require(rec_view["screenshotAfterArrow"]["width"] == width and rec_view["screenshotAfterArrow"]["height"] == height,
                f"{tag} after-arrow screenshot is not the requested viewport size")
        require(after_arrow["regionScrollLeft"] is not None
                and after_arrow["regionScrollLeft"] > before_arrow["regionScrollLeft"],
                f"ArrowRight did not change the diagram scrollLeft: {before_arrow} -> {after_arrow}")
        require(after_arrow["pageScrollLeft"] == before_arrow["pageScrollLeft"],
                f"ArrowRight changed the page scrollLeft: {before_arrow} -> {after_arrow}")
        require(after_arrow["pageScrollWidth"] == before_arrow["pageScrollWidth"]
                and after_arrow["innerWidth"] == before_arrow["innerWidth"],
                f"page width changed after ArrowRight: {before_arrow} -> {after_arrow}")
        no_page_overflow(after_arrow, f"{tag} after ArrowRight")
        rec_view["onlyRegionScrolled"] = True
        rec_view["pageOverflow"] = False

        page.keyboard.press("Tab")
        rec_view["listFocus"] = focus_info(page)
        require(page.evaluate("""() => {
          const el = document.activeElement;
          return !!(el && el.tagName === 'SUMMARY' && (el.textContent || '').includes('查看全部输入节点（完整名称）'));
        }"""), f"Tab did not move to the text-list disclosure: {rec_view['listFocus']}")
        page.keyboard.press("Enter")
        details = page.locator("details").filter(has=page.locator("summary", has_text=LIST_SUMMARY))
        require(details.get_attribute("open") is not None, "keyboard did not expand the text list")
        rec_view["listOpen"] = True
        list_root = details
        headings = [h.strip() for h in list_root.locator("h3").all_inner_texts()]
        rec_view["layerHeadings"] = headings
        require(headings == [layer for layer, _, _ in LAYERS],
                f"text list is not grouped by layer: {headings}")
        for layer, node_id, label in LAYERS:
            section = list_root.locator("section").filter(has=page.get_by_role("heading", name=layer, exact=True))
            text = section.inner_text()
            require(node_id in text and label in text,
                    f"missing full name in layer {layer}: id={node_id!r} label={label!r}")
        company = list_root.locator("section").filter(has=page.get_by_role("heading", name="公司", exact=True))
        company_text = company.inner_text()
        for label in COMPANY_FULL:
            require(label in company_text, f"missing full company name {label!r}")
        rec_view["fullNamesVerified"] = True
        rec_view["groupedByLayer"] = True
        list_root.scroll_into_view_if_needed()
        list_shot = output / f"w15-accimap-{tag}-list.png"
        page.screenshot(path=str(list_shot))
        rec_view["screenshotList"] = png_size(list_shot)
        require(rec_view["screenshotList"]["width"] == width and rec_view["screenshotList"]["height"] == height,
                f"{tag} list screenshot is not the requested viewport size")
        require(not blocked and not errors, f"external or failed browser event: {blocked} {errors}")
        rec_view["passed"] = True
    except Exception as exc:
        rec_view["firstFailure"] = str(exc)
        rec_view["passed"] = False
        try:
            fail = output / f"w15-accimap-{tag}-first-failure.png"
            page.screenshot(path=str(fail))
            rec_view["screenshotFirstFailure"] = png_size(fail)
        except Exception:
            pass
        raise
    finally:
        context.close()


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("source", "node-modules", "chrome", "out"):
        parser.add_argument("--" + flag, type=Path, required=True)
    a = parser.parse_args()
    for key, path in vars(a).items():
        if isinstance(path, Path):
            setattr(a, key, path.absolute())
    require(sys.platform.startswith("linux"), "Linux required")
    require(a.chrome.is_file() and os.access(a.chrome, os.X_OK), "missing Chrome")
    require((a.node_modules / "esbuild/bin/esbuild").is_file(), "existing esbuild required (no install)")
    require((a.node_modules / "react/package.json").is_file(), "existing React required (no install)")
    require(subprocess.check_output(["git", "-C", a.source, "cat-file", "-t", PIN], text=True).strip() == "commit",
            "missing fixed source commit")
    product = subprocess.check_output(["git", "-C", a.source, "show", f"{PIN}:{COMPONENT}"])
    product_sha = hashlib.sha256(product).hexdigest()
    require(product_sha == COMPONENT_SHA256, "pinned component SHA mismatch")
    worktree_component = (a.source / COMPONENT)
    require(worktree_component.is_file(), "product component missing from the acceptance tree")
    require(file_sha(worktree_component) == product_sha, "acceptance tree component differs from the pinned SHA")
    version = subprocess.check_output([a.chrome, "--version"], text=True, timeout=10).strip()
    require("Chrome" in version or "Chromium" in version, "not an available Chrome binary")
    a.out.mkdir(exist_ok=False)
    rec = {
        "revision": PIN, "component": COMPONENT, "componentSha256": product_sha,
        "browser": version, "sandboxRequested": True, "passed": False,
        "scope": "synthetic AcciMap draft diagram component only; not W15 or W4 whole package",
        "viewports": {},
    }
    here = Path(__file__).resolve().parent
    try:
        with tempfile.TemporaryDirectory(prefix="w15-accimap-") as tmp:
            work = Path(tmp)
            assets = work / "dist"
            assets.mkdir()
            web = work / "web"
            web.mkdir()
            (work / "node_modules").symlink_to(a.node_modules, target_is_directory=True)
            (web / "node_modules").symlink_to(a.node_modules, target_is_directory=True)
            # Copy the pinned component into the temp tree so esbuild does not
            # follow a symlink back to the worktree (where React is not installed).
            dest = web / "src" / "accimapPreview"
            dest.mkdir(parents=True)
            shutil.copy2(worktree_component, dest / "Diagram.tsx")
            require(file_sha(dest / "Diagram.tsx") == product_sha, "copied component SHA mismatch")
            page_dir = work / "tests_acceptance" / "w15-accimap-synthetic-browser"
            page_dir.mkdir(parents=True)
            page_src = page_dir / "page.tsx"
            html_src = here / "index.html"
            require((here / "page.tsx").is_file() and html_src.is_file(), "synthetic test page missing")
            page_src.write_bytes((here / "page.tsx").read_bytes())
            bundled = assets / "page.js"
            esbuild = a.node_modules / "esbuild/bin/esbuild"
            with (a.out / "build.log").open("x") as log:
                proc = subprocess.run(
                    [str(esbuild), str(page_src), "--bundle", "--format=esm", "--jsx=automatic",
                     "--platform=browser", f"--outfile={bundled}"],
                    cwd=work, env={**os.environ, "NODE_PATH": str(a.node_modules)},
                    stdout=log, stderr=subprocess.STDOUT, timeout=60,
                )
            require(proc.returncode == 0 and bundled.is_file(), "synthetic page build failed")
            (assets / "index.html").write_bytes(html_src.read_bytes())
            rec["bundleSha256"] = file_sha(bundled)
            step("bundle ready")
            with sync_playwright() as pw:
                browser = pw.chromium.launch(executable_path=str(a.chrome), headless=True,
                                              chromium_sandbox=True, timeout=15000)
                try:
                    rec["browserRuntime"] = browser.version
                    step("chrome launched")
                    with serve(assets) as origin:
                        rec["originHost"] = urlsplit(origin).hostname
                        require(rec["originHost"] == "127.0.0.1", "service is not loopback")
                        for width, height in VIEWPORTS:
                            rec["viewports"][str(width)] = {"passed": False}
                            step(f"{width} start")
                            flow(browser, origin, width, height, a.out, rec["viewports"][str(width)])
                            step(f"{width} done")
                finally:
                    browser.close()
            rec["passed"] = True
    except Exception as exc:
        rec.setdefault("firstFailure", str(exc))
        raise
    finally:
        (a.out / "receipt.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
