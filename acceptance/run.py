"""Official sandboxed Chrome gate: existing knowledge-page keyword search.

Uses the real MCIS service and the official knowledge page. Does not change
product code, add controls, invent fields, or treat DOM simulation / HTTP
doubles as browser evidence. Verification is read-only after official
pre-seeding.
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
PIN = "94d5e38c926fda232bb987b60fa9145e4bcf01a7"
TOKEN = "SYN-W19-PAGE-7k4m2p"
ABSENT = "ZXQ-ABSENT-W19-PAGE-8n3q"
API_PORT = int(os.environ.get("MCIS_PORT", "18794"))
WEB_PORT = int(os.environ.get("MCIS_WEB_PORT", "18795"))
API = f"http://127.0.0.1:{API_PORT}"
WEB = f"http://127.0.0.1:{WEB_PORT}"
HOST_PYTHON = os.environ.get("MCIS_HOST_PYTHON", sys.executable)
CHROME = os.environ.get("MCIS_CHROMIUM", "/opt/google/chrome/google-chrome")
EVIDENCE = Path(os.environ["MCIS_BROWSER_EVIDENCE_DIR"]).resolve()
KNOWLEDGE = f"{API}/api/v1/knowledge"
INVESTIGATOR = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "X-MCIS-Role": "Investigator",
    "X-MCIS-Operator": "LocalSyntheticInvestigator",
}
LEAD = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "X-MCIS-Role": "LeadInvestigator",
    "X-MCIS-Operator": "LocalSyntheticLead",
}
PUB_SRC = {
    "type": "Synthetic",
    "title": "合成夹具-published",
    "locator": "段落1",
    "excerpt": "SYN-W19-PAGE-SRC-PUB",
    "rightsNote": "测试作者构造，不含真实资料",
}
CAND_SRC = {
    "type": "Synthetic",
    "title": "合成夹具-pending",
    "locator": "段落1",
    "excerpt": "SYN-W19-PAGE-SRC-CAND",
    "rightsNote": "测试作者构造，不含真实资料",
}
WDN_SRC = {
    "type": "Synthetic",
    "title": "合成夹具-withdrawn",
    "locator": "段落1",
    "excerpt": "SYN-W19-PAGE-SRC-WDN",
    "rightsNote": "测试作者构造，不含真实资料",
}
PUB_TITLE = f"合成知识卡 {TOKEN} published"
CAND_TITLE = f"合成知识卡 {TOKEN} pending"
WDN_TITLE = f"合成知识卡 {TOKEN} withdrawn"
EMPTY_TEXT = "没有符合条件的知识卡。库为空时不伪造样本或模型推荐。"


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


def card(title: str, label: str, source: dict) -> dict:
    return {
        "kind": "Method",
        "title": title,
        "summary": f"仅用于页面检索出处对照的合成样本 {TOKEN}",
        "body": f"合成正文，不是真实事故。标记 {TOKEN}。{label}",
        "tags": ["synthetic-w19-page", TOKEN.lower()],
        "applicability": "不能当真实结论",
        "source": source,
    }


def seed_cards() -> dict:
    fixtures = " ".join(
        [
            TOKEN,
            ABSENT,
            PUB_TITLE,
            CAND_TITLE,
            WDN_TITLE,
            json.dumps(PUB_SRC, ensure_ascii=False),
            json.dumps(CAND_SRC, ensure_ascii=False),
            json.dumps(WDN_SRC, ensure_ascii=False),
        ]
    )
    if ABSENT.lower() in fixtures.replace(ABSENT, "").lower():
        raise RuntimeError("absent query leaked into fixtures")

    def create_one(title: str, label: str, source: dict) -> dict:
        created = _http("POST", f"{KNOWLEDGE}/cards", INVESTIGATOR, card(title, label, source), 201)
        if created.get("status") != "Candidate":
            raise RuntimeError(f"create {label} unexpected: {created!r}")
        return created

    def review_one(doc: dict, decision: str) -> dict:
        reviewed = _http(
            "POST",
            f"{KNOWLEDGE}/cards/{doc['cardId']}/review",
            LEAD,
            {
                "decision": decision,
                "expectedDigest": doc["contentDigest"],
                "note": "已人工核查，允许发布或撤回合成测试样本",
                "sourceVerified": True,
                "rightsVerified": True,
                "releaseApproved": True,
            },
            200,
        )
        if reviewed.get("status") != decision or reviewed.get("cardId") != doc["cardId"]:
            raise RuntimeError(f"review {doc['cardId']} -> {decision} unexpected: {reviewed!r}")
        return reviewed

    pending = create_one(CAND_TITLE, "pending", CAND_SRC)
    published = review_one(create_one(PUB_TITLE, "published", PUB_SRC), "Published")
    withdrawn = review_one(review_one(create_one(WDN_TITLE, "withdrawn", WDN_SRC), "Published"), "Withdrawn")
    return {
        "published": published["cardId"],
        "pending": pending["cardId"],
        "withdrawn": withdrawn["cardId"],
        "publishedSource": PUB_SRC,
        "token": TOKEN,
        "absent": ABSENT,
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


def q_in_url(url: str, value: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    return value in qs.get("q", [])


def is_cards_get(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return "/api/v1/knowledge/cards" in parsed.path and not parsed.path.rstrip("/").endswith("/review")


def run_browser(seed: dict, shot_dir: Path) -> dict:
    from playwright.sync_api import sync_playwright

    shot_dir.mkdir(parents=True, exist_ok=True)
    requests: list[dict] = []
    page_errors: list[str] = []
    with sync_playwright() as pw, tempfile.TemporaryDirectory(prefix="w19-page-chrome-") as tmp:
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

        page.goto(f"{WEB}/#/knowledge")
        page.locator('select[title="X-MCIS-Role"]').select_option("Investigator")
        page.get_by_role("heading", name="案例、疑难与方法知识卡").wait_for()
        page.get_by_text("读取知识卡…").wait_for(state="hidden")
        keyword = page.locator("form.w19-search input").first
        search_btn = page.get_by_role("button", name="检索", exact=True)
        keyword.wait_for()

        def do_search(term: str) -> dict:
            keyword.fill(term)

            def match(resp) -> bool:
                return (
                    resp.request.method == "GET"
                    and is_cards_get(resp.url)
                    and q_in_url(resp.url, term)
                    and resp.ok
                )

            with page.expect_response(match, timeout=20000) as pending:
                search_btn.click()
            resp = pending.value
            page.get_by_text("读取知识卡…").wait_for(state="hidden")
            body = resp.json()
            return {"url": resp.url, "status": resp.status, "body": body}

        unique = do_search(TOKEN)
        items = unique["body"].get("items") or []
        if unique["body"].get("total") != 1 or [i.get("cardId") for i in items] != [seed["published"]]:
            raise RuntimeError(f"unique-term request did not return only the published card: {unique['body']!r}")
        source = items[0]["content"]["source"]
        if source != PUB_SRC:
            raise RuntimeError(f"unique-term request source mismatch: {source!r}")
        main = page.locator("main.w19")
        visible = main.inner_text() or ""
        assert PUB_TITLE in visible, f"published title missing on page: {visible!r}"
        assert CAND_TITLE not in visible and WDN_TITLE not in visible, "unreviewed or withdrawn card mixed into unique search"
        details = page.locator("article.w19-card details").first
        if not details.get_attribute("open"):
            details.locator("summary").click()
        text = main.inner_text() or ""
        assert seed["published"] in text, "published card id missing after opening source details"
        assert PUB_SRC["title"] in text and PUB_SRC["locator"] in text and PUB_SRC["excerpt"] in text, text
        assert CAND_SRC["excerpt"] not in text and WDN_SRC["excerpt"] not in text
        assert seed["pending"] not in text and seed["withdrawn"] not in text
        page.screenshot(path=str(shot_dir / "01-unique-term.png"), full_page=True)

        absent = do_search(ABSENT)
        if absent["body"].get("total") != 0 or (absent["body"].get("items") or []) != []:
            raise RuntimeError(f"absent-term request was not empty: {absent['body']!r}")
        page.get_by_text(EMPTY_TEXT, exact=True).wait_for()
        after = main.inner_text() or ""
        assert PUB_TITLE not in after and seed["published"] not in after, "old card remained after absent search"
        assert CAND_TITLE not in after and WDN_TITLE not in after
        assert PUB_SRC["excerpt"] not in after
        page.screenshot(path=str(shot_dir / "02-absent-term.png"), full_page=True)

        writes = [r for r in requests if r["method"] not in ("GET", "HEAD", "OPTIONS") and "/api/v1/" in r["url"]]
        knowledge_writes = [r for r in writes if "/api/v1/knowledge" in r["url"]]
        assert not knowledge_writes, f"verification issued knowledge writes: {knowledge_writes}"
        assert not page_errors, page_errors
        version = browser.version
        browser.close()
    return {
        "pass": True,
        "version": f"Google Chrome {version}",
        "chromiumSandbox": True,
        "noSandboxArg": False,
        "token": TOKEN,
        "absent": ABSENT,
        "uniqueRequest": {
            "url": unique["url"],
            "status": unique["status"],
            "total": unique["body"].get("total"),
            "cardIds": [i.get("cardId") for i in unique["body"].get("items") or []],
            "source": unique["body"]["items"][0]["content"]["source"],
        },
        "absentRequest": {
            "url": absent["url"],
            "status": absent["status"],
            "total": absent["body"].get("total"),
            "items": absent["body"].get("items"),
        },
        "browserApiRequests": [r for r in requests if "/api/v1/" in r["url"]],
        "verificationWrites": writes,
        "pageErrors": page_errors,
        "screenshots": ["01-unique-term.png", "02-absent-term.png"],
    }


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    logs = EVIDENCE / "logs"
    shots = EVIDENCE / "screenshots"
    logs.mkdir(parents=True, exist_ok=True)
    shots.mkdir(parents=True, exist_ok=True)
    head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
    if head != PIN:
        base_ok = subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", PIN, "HEAD"]).returncode == 0
        if not base_ok:
            raise SystemExit(f"HEAD {head} is not {PIN} or a descendant")
        diff = subprocess.check_output(["git", "-C", str(ROOT), "diff", "--name-only", PIN, "HEAD"], text=True).splitlines()
        allowed = "tests_acceptance/w19-page-search/"
        if any(not path.startswith(allowed) for path in diff):
            raise SystemExit(f"Unexpected changes versus pin: {diff}")
    ensure_node_modules()
    data_dir = Path(tempfile.mkdtemp(prefix="w19-page-sqlite-"))
    host_log = (logs / "01-host.log").open("w", encoding="utf-8")
    vite_log = (logs / "02-vite.log").open("w", encoding="utf-8")
    host = vite = None
    exit_doc: dict = {"pass": False, "chromiumSandbox": True, "noSandboxArg": False, "pin": PIN}
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
        seed = seed_cards()
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
            "PASS official sandboxed Chrome: unique keyword located the reviewed card and source; "
            "absent keyword showed empty with no leftover card; both page results matched the same live requests.",
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
