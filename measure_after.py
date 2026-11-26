"""One-off W15 layout measurement in real sandboxed Chrome. Not a pass/fail gate."""
import json
import sys
import time
from pathlib import Path

import importlib.util

HERE = Path("/workspace/mcis-w15-layout-cand")
sys.path.insert(0, str(HERE / "tests_acceptance/w15-source-chromium"))
spec = importlib.util.spec_from_file_location(
    "w15run", HERE / "tests_acceptance/w15-source-chromium/run.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

from playwright.sync_api import expect, sync_playwright

OUT = Path("/workspace/mcis-w15-layout-report/after")
OUT.mkdir(parents=True, exist_ok=True)

MEASURE_JS = r"""() => {
  const pick = (el, name) => {
    if (!el) return {name, present:false};
    const cs = getComputedStyle(el);
    return {
      name, present:true,
      clientWidth: el.clientWidth, scrollWidth: el.scrollWidth,
      overflowX: cs.overflowX, minWidth: cs.minWidth, whiteSpace: cs.whiteSpace,
      gridTemplateColumns: cs.gridTemplateColumns,
      width: cs.width
    };
  };
  const doc = document.documentElement;
  const app = document.querySelector('.app');
  const topbar = document.querySelector('.topbar');
  const main = document.querySelector('.main');
  const diagram = document.querySelector('.w153-diagram');
  const sidebar = document.querySelector('.sidebar');
  const order = [
    pick(doc, 'document'),
    pick(app, 'app'),
    pick(topbar, 'topbar'),
    pick(main, 'main'),
    pick(diagram, 'diagram'),
  ];
  const firstOverflow = order.find(x => x.present && x.scrollWidth > x.clientWidth + 1);
  return {
    viewportInnerWidth: window.innerWidth,
    viewportInnerHeight: window.innerHeight,
    sidebar: pick(sidebar, 'sidebar'),
    parts: order,
    firstOverflow: firstOverflow ? firstOverflow.name : null,
    firstOverflowDelta: firstOverflow ? firstOverflow.scrollWidth - firstOverflow.clientWidth : 0
  };
}"""

def measure(page, tag, viewport):
    data = page.evaluate(MEASURE_JS)
    data["tag"] = tag
    data["requestedViewport"] = viewport
    (OUT / f"{tag}-metrics.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    # true-size viewport shot (not full page)
    vp = OUT / f"{tag}-viewport.png"
    page.screenshot(path=str(vp), full_page=False)
    fp = OUT / f"{tag}-fullpage.png"
    page.screenshot(path=str(fp), full_page=True)
    return data, vp, fp

def go(page, origin, case):
    page.goto(origin + f"/#/systemic?case={case}")
    expect(page.get_by_role("heading", name="系统性分析 · Bow-tie 假设草拟")).to_be_visible()
    expect(page.locator("#w153-draft-sources")).to_contain_text(mod.TITLES[case])

def main():
    source = HERE
    modules = Path("/workspace/mcis-w17-871db66/web/node_modules")
    host_python = Path("/workspace/mcis-w17-871db66/service/.venv/bin/python")
    browser_path = Path("/opt/google/chrome/google-chrome")
    evidence = OUT / "host-work"
    evidence.mkdir()
    import tempfile
    with tempfile.TemporaryDirectory(prefix="mcis-w15-layout-after-") as tmp:
        work = Path(tmp)
        fixed, assets = mod.prepare(source, work, modules)
        data = work / "store"
        data.mkdir()
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=str(browser_path), headless=True,
                chromium_sandbox=True, env=mod.environment(work),
                args=["--no-proxy-server"])
            try:
                with mod.host(host_python, work, fixed, assets, data, evidence, "measure") as origin:
                    mod.setup(origin)
                    results = []
                    for width, height, tag in ((390, 844, "after-390"), (1440, 900, "after-1440")):
                        context = browser.new_context(
                            viewport={"width": width, "height": height},
                            service_workers="block")
                        def route(req):
                            from urllib.parse import urlsplit
                            if urlsplit(req.request.url).netloc == urlsplit(origin).netloc and req.request.url.startswith("http://"):
                                req.continue_()
                            else:
                                req.abort()
                        context.route("**/*", route)
                        context.add_init_script("""localStorage.setItem('mcis.role','LeadInvestigator');
      localStorage.setItem('mcis.operator','Synthetic W15');""")
                        page = context.new_page()
                        go(page, origin, mod.CASE_A)
                        measured, vp, fp = measure(page, tag, {"width": width, "height": height})
                        results.append({"metrics": measured, "viewportShot": str(vp), "fullpageShot": str(fp)})
                        context.close()
                    print(json.dumps(results, indent=2, ensure_ascii=False))
            finally:
                browser.close()

if __name__ == "__main__":
    main()
