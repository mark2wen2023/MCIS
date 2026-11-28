#!/usr/bin/env python3
"""Isolated W15 AcciMap local SVG export on the existing six-layer synthetic sketch.

Does not change the product preview component, official routes, Bow-tie export,
main, CI, services, the trial build, or the 3D repo. Does not rerun the past 9/9 core.
"""
import argparse, hashlib, json, os, shutil, struct, subprocess, sys, tempfile, time
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

PIN = "2447b14076bbf39db014b8bf4a3a3b350cbf0e05"
COMPONENT = "web/src/accimapPreview/Diagram.tsx"
COMPONENT_SHA256 = "d6f67ba6d80b19b7a1c212a02ee6ac0bfc7903f6d067affd2acba4e6210c875f"
DOWNLOAD_NAME = "accimap-synthetic-draft.svg"
VIEWPORT = (1440, 900)
LAYERS = ["政府与法规", "监管", "公司", "船舶管理", "船员行为", "设备与环境"]
MARKERS = ["待核验", "证据状态未知", "均非已证实因果"]
FULL_IDS = [
    "SYN-GOV-LONG-IDENTIFIER-001",
    "SYN-REG-LONG-IDENTIFIER-001",
    "SYN-CO-LONG-IDENTIFIER-001",
    "SYN-MGT-LONG-IDENTIFIER-001",
    "SYN-CREW-LONG-IDENTIFIER-001",
    "SYN-EQ-LONG-IDENTIFIER-001",
]
FULL_LABELS = [
    "政府层必须完整保留的合成长名称甲",
    "监管层必须完整保留的合成长名称乙",
    "这是必须完整保留且不能只显示十个汉字的合成节点说明",
    "船舶管理层必须完整保留的合成长名称癸",
    "船员行为层必须完整保留的合成长名称子",
    "设备与环境层必须完整保留的合成长名称丑",
]
SVG_NS = "http://www.w3.org/2000/svg"


def require(condition, name):
    if not condition:
        raise RuntimeError(name)


def step(msg):
    print(f"W15 ACCIMAP-SVG {time.monotonic():.3f} {msg}", flush=True)


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def png_size(path):
    data = path.read_bytes()
    width, height = struct.unpack(">II", data[16:24])
    return {"width": width, "height": height, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def localname(tag):
    return tag.rsplit("}", 1)[-1]


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


def validate_svg(path):
    text = path.read_text(encoding="utf-8")
    require(text.lstrip().startswith("<"), "downloaded file is not XML text")
    require("<svg" in text, "downloaded file has no svg element")
    root = ET.fromstring(text)
    require(localname(root.tag) == "svg", f"root is not svg: {root.tag}")
    require(root.tag == f"{{{SVG_NS}}}svg" or root.get("xmlns") == SVG_NS,
            "standalone SVG is missing the SVG namespace")
    for marker in MARKERS:
        require(marker in text, f"missing marker {marker!r}")
    for layer in LAYERS:
        require(layer in text, f"missing layer label {layer!r}")
    for node_id in FULL_IDS:
        require(node_id in text, f"missing full node id {node_id!r}")
    for label in FULL_LABELS:
        require(label in text, f"missing full Chinese label {label!r}")
    lines = [el for el in root.iter() if localname(el.tag) == "line"]
    solid = [el for el in lines if not el.get("stroke-dasharray")]
    dashed = [el for el in lines if el.get("stroke-dasharray")]
    require(len(solid) == 2, f"expected 2 solid relation edges, got {len(solid)} (total {len(lines)})")
    require(len(dashed) == 1, f"expected 1 dashed information-flow edge, got {len(dashed)}")
    require(all("5" in (el.get("stroke-dasharray") or "") for el in dashed),
            "information-flow edge is not dashed as in the existing sketch")
    # Relation and information-flow strokes must not share the same dash style.
    require(set(el.get("stroke-dasharray") or "" for el in solid).isdisjoint(
        set(el.get("stroke-dasharray") or "" for el in dashed if el.get("stroke-dasharray"))),
        "information-flow and relation edges are not visually distinct")
    return {
        "bytes": path.stat().st_size,
        "sha256": file_sha(path),
        "layers": LAYERS,
        "markers": MARKERS,
        "solidRelationLines": len(solid),
        "dashedInformationFlowLines": len(dashed),
        "fullIdsVerified": True,
        "fullLabelsVerified": True,
    }


def main():
    from playwright.sync_api import expect, sync_playwright
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
    worktree_component = a.source / COMPONENT
    require(worktree_component.is_file(), "product component missing from the acceptance tree")
    require(file_sha(worktree_component) == product_sha, "acceptance tree component differs from the pinned SHA")
    here = Path(__file__).resolve().parent
    for name in ("page.tsx", "index.html", "svgExport.ts"):
        require((here / name).is_file(), f"missing isolated export file {name}")
    version = subprocess.check_output([a.chrome, "--version"], text=True, timeout=10).strip()
    require("Chrome" in version or "Chromium" in version, "not an available Chrome binary")
    a.out.mkdir(exist_ok=False)
    rec = {
        "revision": PIN,
        "component": COMPONENT,
        "componentSha256": product_sha,
        "exportModule": "tests_acceptance/w15-accimap-svg-export/svgExport.ts",
        "exportModuleSha256": file_sha(here / "svgExport.ts"),
        "browser": version,
        "sandboxRequested": True,
        "passed": False,
        "scope": "isolated local SVG export of the existing six-layer synthetic AcciMap sketch; not W15 whole package; not the past 9/9 core; not Bow-tie export",
        "console": [],
        "pageErrors": [],
        "blocked": [],
    }
    console_lines = rec["console"]
    page_errors = rec["pageErrors"]
    blocked = rec["blocked"]
    try:
        with tempfile.TemporaryDirectory(prefix="w15-accimap-svg-") as tmp:
            work = Path(tmp)
            assets = work / "dist"
            assets.mkdir()
            web = work / "web"
            web.mkdir()
            (work / "node_modules").symlink_to(a.node_modules, target_is_directory=True)
            (web / "node_modules").symlink_to(a.node_modules, target_is_directory=True)
            dest = web / "src" / "accimapPreview"
            dest.mkdir(parents=True)
            shutil.copy2(worktree_component, dest / "Diagram.tsx")
            require(file_sha(dest / "Diagram.tsx") == product_sha, "copied component SHA mismatch")
            page_dir = work / "tests_acceptance" / "w15-accimap-svg-export"
            page_dir.mkdir(parents=True)
            for name in ("page.tsx", "svgExport.ts"):
                (page_dir / name).write_bytes((here / name).read_bytes())
            bundled = assets / "page.js"
            esbuild = a.node_modules / "esbuild/bin/esbuild"
            with (a.out / "build.log").open("x") as log:
                proc = subprocess.run(
                    [str(esbuild), str(page_dir / "page.tsx"), "--bundle", "--format=esm",
                     "--jsx=automatic", "--platform=browser", f"--outfile={bundled}"],
                    cwd=work, env={**os.environ, "NODE_PATH": str(a.node_modules)},
                    stdout=log, stderr=subprocess.STDOUT, timeout=60,
                )
            require(proc.returncode == 0 and bundled.is_file(), "isolated export page build failed")
            (assets / "index.html").write_bytes((here / "index.html").read_bytes())
            rec["bundleSha256"] = file_sha(bundled)
            step("bundle ready")
            with sync_playwright() as pw:
                browser = pw.chromium.launch(
                    executable_path=str(a.chrome),
                    headless=True,
                    chromium_sandbox=True,
                    timeout=15000,
                )
                try:
                    rec["browserRuntime"] = browser.version
                    step("chrome launched")
                    with serve(assets) as origin:
                        rec["originHost"] = urlsplit(origin).hostname
                        require(rec["originHost"] == "127.0.0.1", "service is not loopback")
                        width, height = VIEWPORT
                        context = browser.new_context(
                            viewport={"width": width, "height": height},
                            accept_downloads=True,
                            service_workers="block",
                        )

                        def block_external(route):
                            blocked.append(route.request.url)
                            route.abort()

                        context.route("https://**/*", block_external)
                        context.route("http://localhost/**/*", block_external)
                        context.route("http://[::1]/**/*", block_external)
                        context.route_web_socket("**/*", lambda ws: (blocked.append("ws"), ws.close()))
                        page = context.new_page()
                        page.on("console", lambda msg: console_lines.append({"type": msg.type, "text": msg.text}))
                        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
                        try:
                            step("open isolated page")
                            page.goto(origin + "/", timeout=15000)
                            expect(page.get_by_role("img", name="AcciMap 六层人工草图 · 待核验")).to_be_visible(timeout=15000)
                            page_shot = a.out / "w15-accimap-svg-page.png"
                            page.screenshot(path=str(page_shot), full_page=True)
                            rec["screenshotPage"] = png_size(page_shot)
                            button = page.get_by_role("button", name="下载 SVG", exact=True)
                            expect(button).to_be_visible(timeout=15000)
                            step("click download")
                            with page.expect_download(timeout=15000) as pending:
                                button.click()
                            download = pending.value
                            rec["suggestedFilename"] = download.suggested_filename
                            require(download.suggested_filename == DOWNLOAD_NAME,
                                    f"unexpected download name: {download.suggested_filename!r}")
                            svg_path = a.out / DOWNLOAD_NAME
                            download.save_as(str(svg_path))
                            require(svg_path.is_file() and svg_path.stat().st_size > 0, "download artifact missing")
                            rec["svg"] = validate_svg(svg_path)
                            step(f"svg validated {rec['svg']}")
                            # Re-open the downloaded file over the same loopback server.
                            shutil.copy2(svg_path, assets / DOWNLOAD_NAME)
                            file_page = context.new_page()
                            file_page.on("pageerror", lambda exc: page_errors.append("open-svg: " + str(exc)))
                            file_page.goto(origin + "/" + DOWNLOAD_NAME, timeout=15000)
                            opened = file_page.evaluate(
                                """() => ({
                                  root: document.documentElement && document.documentElement.localName,
                                  ns: document.documentElement && document.documentElement.namespaceURI,
                                  text: (document.documentElement && document.documentElement.textContent) || '',
                                  lineCount: document.querySelectorAll('line').length,
                                })"""
                            )
                            rec["openedFile"] = {
                                "root": opened.get("root"),
                                "ns": opened.get("ns"),
                                "lineCount": opened.get("lineCount"),
                            }
                            require(opened.get("root") == "svg", f"opened file root is not svg: {opened}")
                            require(opened.get("ns") == SVG_NS, f"opened file namespace mismatch: {opened}")
                            require(opened.get("lineCount") == 3, f"opened file line count mismatch: {opened}")
                            for marker in MARKERS:
                                require(marker in opened.get("text", ""), f"opened file missing marker {marker!r}")
                            for layer in LAYERS:
                                require(layer in opened.get("text", ""), f"opened file missing layer {layer!r}")
                            open_shot = a.out / "w15-accimap-svg-opened.png"
                            file_page.screenshot(path=str(open_shot))
                            rec["screenshotOpened"] = png_size(open_shot)
                            file_page.close()
                            require(not blocked, f"external request blocked: {blocked}")
                            require(not page_errors, f"page errors: {page_errors}")
                        finally:
                            context.close()
                finally:
                    browser.close()
            rec["passed"] = True
            rec["exitHint"] = 0
    except Exception as exc:
        rec.setdefault("firstFailure", str(exc))
        rec["passed"] = False
        raise
    finally:
        (a.out / "receipt.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n")
        (a.out / "browser.log").write_text(
            json.dumps({"console": rec.get("console", []), "pageErrors": rec.get("pageErrors", []),
                        "blocked": rec.get("blocked", [])}, ensure_ascii=False, indent=2) + "\n"
        )


if __name__ == "__main__":
    main()
