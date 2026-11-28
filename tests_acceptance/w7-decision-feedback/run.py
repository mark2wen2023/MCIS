"""Official sandboxed Chrome gate: pending opinion, decision, feedback, reopen.

Uses the real MCIS service and the official recommendations page on product
SHA b2ecb50. Does not change product code, invent fields, send, formally
issue, or treat DOM simulation / HTTP-only as browser evidence.
"""
from __future__ import annotations

import hashlib
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
PRODUCT_SHA = "b2ecb50b32b721c9f171b74ecd576691c0048b94"
PINS = {
    "web/src/consultation/ConsultationPanel.tsx": "492b65fcace052d6ced7860fc4576f2cc5ba240c",
    "web/src/consultation/model.ts": "462537d3eb3421bef6699d904d7841d497450077",
    "service/mcis_service/recommendations/router.py": "aa39f644a3205f255c1a686295fc06f559282ebf",
}
CASE_ID = "SYN-W7-DECISION-001"
VER = "SYN-DRAFT-D1"
SHA_DRAFT = "d" * 64
PARTY_ID = "SYN-P-A"
PARTY_NAME = "虚构相关方甲"
REPLY_TEXT = "已登记合成回复（虚构），不发送。"
COMMENT_TEXT = "合成待处理意见一条（虚构）。"
FEEDBACK = "合成部分采纳反馈：仅核对待处理意见的书面理由（虚构）。"
API_PORT = int(os.environ.get("MCIS_PORT", "18794"))
WEB_PORT = int(os.environ.get("MCIS_WEB_PORT", "18795"))
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


def git_blob(path: str) -> str:
    raw = (ROOT / path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\x00" + raw).hexdigest()


def check_pins() -> None:
    for path, expected in PINS.items():
        actual = git_blob(path)
        if actual != expected:
            raise RuntimeError(f"product pin mismatch {path}: {actual} != {expected}")


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


def seed_pending_opinion() -> dict:
    case = {
        "caseId": CASE_ID,
        "schemaVersion": "1.0.0",
        "title": "合成意见采纳反馈核对（虚构）",
        "accidentType": "Collision",
        "incidentTimeUtc": "2026-02-01T12:00:00Z",
        "caseEpochUtc": "2026-02-01T11:00:00Z",
        "displayTimeZoneOffsetMinutes": 480,
        "incidentLocation": {"lonDeg": 120.0, "latDeg": 30.0},
        "isFictionalDemo": True,
        "placeName": "虚构水域",
    }
    _http("POST", f"{API}/api/v1/cases", case, 201)
    opened = _http(
        "POST",
        f"{API}/api/v1/cases/{CASE_ID}/consultation/rounds",
        {
            "draftVersion": VER,
            "parties": [{"partyId": PARTY_ID, "name": PARTY_NAME}],
            "days": 30,
            "isAgreedDeadline": False,
            "draftSha256": SHA_DRAFT,
        },
        201,
    )
    reply = _http(
        "POST",
        f"{API}/api/v1/cases/{CASE_ID}/consultation/rounds/1/replies",
        {"partyId": PARTY_ID, "text": REPLY_TEXT, "comments": [COMMENT_TEXT]},
        201,
    )
    comments = [c for c in reply.get("comments", []) if c.get("text") == COMMENT_TEXT]
    if len(comments) != 1:
        raise RuntimeError(f"expected one seeded comment, got {reply!r}")
    comment = comments[0]
    if comment.get("decision") != "Pending" or comment.get("feedback"):
        raise RuntimeError(f"seeded comment not pending: {comment!r}")
    audit_before = _http("GET", f"{API}/api/v1/cases/{CASE_ID}/audit?category=Consultation")
    return {
        "caseId": CASE_ID,
        "roundNo": int(opened.get("roundNo", 1)),
        "draftVersion": VER,
        "commentId": comment["commentId"],
        "commentText": COMMENT_TEXT,
        "replyText": REPLY_TEXT,
        "auditBeforeBrowser": audit_before,
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


def start_host(env: dict, log_file) -> subprocess.Popen:
    proc = subprocess.Popen(
        [HOST_PYTHON, "-u", str(HERE / "host.py")],
        cwd=str(ROOT),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    wait_ready(proc)
    return proc


def start_vite(env: dict, log_file) -> subprocess.Popen:
    proc = subprocess.Popen(
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
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    wait_http(WEB + "/", timeout=40)
    return proc


def consultation_writes(requests: list[dict]) -> list[dict]:
    return [
        r
        for r in requests
        if r["method"] not in ("GET", "HEAD", "OPTIONS")
        and "/api/v1/" in r["url"]
        and any(
            m in r["url"]
            for m in ("/consultation/", "/recommendations")
        )
    ]


def ready_official_page(page) -> None:
    page.goto(f"{WEB}/#/recs?case={CASE_ID}")
    role = page.locator('select[title="X-MCIS-Role"]')
    if role.input_value() != "LeadInvestigator":
        role.select_option("LeadInvestigator")
    page.locator('select[aria-label="选择轮次"]').wait_for()
    page.get_by_text("正在读取轮次与权限…").wait_for(state="hidden")


def run_browser_decide(seed: dict, shot_dir: Path) -> dict:
    from playwright.sync_api import expect, sync_playwright

    shot_dir.mkdir(parents=True, exist_ok=True)
    requests: list[dict] = []
    page_errors: list[str] = []
    comment_id = seed["commentId"]
    with sync_playwright() as pw, tempfile.TemporaryDirectory(prefix="w7-decision-chrome-") as tmp:
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
            item = {"method": req.method, "url": req.url, "resource": req.resource_type}
            if req.method in ("POST", "PATCH", "PUT", "DELETE"):
                item["postData"] = req.post_data
            requests.append(item)

        page.on("request", on_request)
        ready_official_page(page)
        panel = page.locator(".w7-consultation")
        expect(page.locator('select[aria-label="选择轮次"]')).to_have_value(str(seed["roundNo"]))
        expect(panel).to_contain_text(comment_id)
        expect(panel).to_contain_text("待处理")
        expect(panel).to_contain_text(COMMENT_TEXT)
        row = panel.locator(".w7-comment").filter(has=page.locator("strong", has_text=comment_id))
        row.get_by_label("采纳决定").select_option("PartiallyAdopted")
        row.get_by_label("反馈理由", exact=False).fill("")
        save_btn = row.get_by_role("button", name="保存决定")
        expect(save_btn).to_be_disabled()
        writes_before = list(consultation_writes(requests))
        row.scroll_into_view_if_needed()
        page.screenshot(path=str(shot_dir / "01-partial-no-reason-blocked.png"), full_page=True)
        row.get_by_label("反馈理由", exact=False).fill("   ")
        expect(save_btn).to_be_disabled()
        page.screenshot(path=str(shot_dir / "02-partial-whitespace-blocked.png"), full_page=True)
        writes_after_block = consultation_writes(requests)
        if writes_after_block != writes_before:
            raise RuntimeError(f"blocked partial adopt wrote: {writes_after_block}")

        row.get_by_label("反馈理由", exact=False).fill(FEEDBACK)
        expect(save_btn).to_be_enabled()
        with page.expect_response(
            lambda r: r.request.method == "PATCH" and f"/comments/{comment_id}" in r.url
        ) as resp_info:
            save_btn.click()
        resp = resp_info.value
        if resp.status != 200:
            raise RuntimeError(f"save decision HTTP {resp.status}")
        body = resp.json()
        decided = next(c for c in body.get("comments", []) if c["commentId"] == comment_id)
        if decided.get("decision") != "PartiallyAdopted" or decided.get("feedback") != FEEDBACK:
            raise RuntimeError(f"save response mismatch: {decided!r}")
        expect(row.get_by_role("button", name="保存决定")).to_have_count(0)
        expect(row).to_contain_text("部分采纳")
        expect(row).to_contain_text(f"反馈：{FEEDBACK}")
        row.scroll_into_view_if_needed()
        page.screenshot(path=str(shot_dir / "03-partial-saved-once.png"), full_page=True)
        decide_writes = [
            r
            for r in consultation_writes(requests)
            if r not in writes_before and "/comments/" in r["url"]
        ]
        if len(decide_writes) != 1 or decide_writes[0]["method"] != "PATCH":
            raise RuntimeError(f"expected one PATCH save, got {decide_writes}")
        payload = json.loads(decide_writes[0].get("postData") or "{}")
        if payload.get("decision") != "PartiallyAdopted" or payload.get("feedback") != FEEDBACK:
            raise RuntimeError(f"PATCH body mismatch: {payload!r}")
        if page_errors:
            raise RuntimeError(f"page errors: {page_errors}")
        version = browser.version
        browser.close()
    return {
        "pass": True,
        "phase": "decide",
        "version": f"Google Chrome {version}",
        "chromiumSandbox": True,
        "noSandboxArg": False,
        "commentId": comment_id,
        "browserApiRequests": [r for r in requests if "/api/v1/" in r["url"]],
        "consultationWrites": consultation_writes(requests),
        "pageErrors": page_errors,
        "screenshots": [
            "01-partial-no-reason-blocked.png",
            "02-partial-whitespace-blocked.png",
            "03-partial-saved-once.png",
        ],
    }


def run_browser_reopen(seed: dict, shot_dir: Path) -> dict:
    from playwright.sync_api import expect, sync_playwright

    requests: list[dict] = []
    page_errors: list[str] = []
    comment_id = seed["commentId"]
    with sync_playwright() as pw, tempfile.TemporaryDirectory(prefix="w7-reopen-chrome-") as tmp:
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
            item = {"method": req.method, "url": req.url, "resource": req.resource_type}
            if req.method in ("POST", "PATCH", "PUT", "DELETE"):
                item["postData"] = req.post_data
            requests.append(item)

        page.on("request", on_request)
        ready_official_page(page)
        panel = page.locator(".w7-consultation")
        expect(page.locator('select[aria-label="选择轮次"]')).to_have_value(str(seed["roundNo"]))
        option = page.locator('select[aria-label="选择轮次"]').locator(f'option[value="{seed["roundNo"]}"]')
        expect(option).to_contain_text(VER)
        row = panel.locator(".w7-comment").filter(has=page.locator("strong", has_text=comment_id))
        expect(row).to_contain_text(comment_id)
        expect(row).to_contain_text("部分采纳")
        expect(row).to_contain_text(COMMENT_TEXT)
        expect(row).to_contain_text(f"反馈：{FEEDBACK}")
        expect(row.get_by_role("button", name="保存决定")).to_have_count(0)
        row.scroll_into_view_if_needed()
        page.screenshot(path=str(shot_dir / "04-reopen-same-db.png"), full_page=True)
        writes = consultation_writes(requests)
        if writes:
            raise RuntimeError(f"reopen issued writes: {writes}")
        if page_errors:
            raise RuntimeError(f"page errors on reopen: {page_errors}")
        version = browser.version
        browser.close()
    return {
        "pass": True,
        "phase": "reopen",
        "version": f"Google Chrome {version}",
        "chromiumSandbox": True,
        "noSandboxArg": False,
        "browserApiRequests": [r for r in requests if "/api/v1/" in r["url"]],
        "consultationWrites": writes,
        "pageErrors": page_errors,
        "screenshots": ["04-reopen-same-db.png"],
    }


def audit_actions(events: list) -> list[str]:
    if not isinstance(events, list):
        raise RuntimeError(f"audit payload not a list: {events!r}")
    return [e.get("action") for e in events]


def main() -> int:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    logs = EVIDENCE / "logs"
    shots = EVIDENCE / "screenshots"
    logs.mkdir(parents=True, exist_ok=True)
    shots.mkdir(parents=True, exist_ok=True)
    check_pins()
    ensure_node_modules()
    data_dir = Path(tempfile.mkdtemp(prefix="w7-decision-sqlite-"))
    host_log = (logs / "01-host.log").open("w", encoding="utf-8")
    vite_log = (logs / "02-vite.log").open("w", encoding="utf-8")
    host_reopen_log = (logs / "04-host-reopen.log").open("w", encoding="utf-8")
    vite_reopen_log = (logs / "05-vite-reopen.log").open("w", encoding="utf-8")
    host = vite = host2 = vite2 = None
    exit_doc: dict = {
        "pass": False,
        "productSha": PRODUCT_SHA,
        "chromiumSandbox": True,
        "noSandboxArg": False,
        "dataDir": str(data_dir),
    }
    try:
        env = {
            **os.environ,
            "MCIS_DATA_DIR": str(data_dir),
            "MCIS_SEED_DEMO": "0",
            "MCIS_PORT": str(API_PORT),
            "MCIS_API": API,
            "PYTHONPATH": str(ROOT / "service"),
        }
        host = start_host(env, host_log)
        seed = seed_pending_opinion()
        (logs / "00-seed.json").write_text(
            json.dumps(seed, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        vite = start_vite(env, vite_log)
        decide = run_browser_decide(seed, shots)
        after = _http("GET", f"{API}/api/v1/cases/{CASE_ID}/audit?category=Consultation")
        before_actions = audit_actions(seed["auditBeforeBrowser"])
        after_actions = audit_actions(after)
        new_actions = after_actions[len(before_actions) :]
        if new_actions != ["consultation.decide"]:
            raise RuntimeError(
                f"audit after save expected only consultation.decide, got {after_actions} (new={new_actions})"
            )
        decide_events = [e for e in after if e.get("action") == "consultation.decide"]
        if len(decide_events) != 1:
            raise RuntimeError(f"expected one decide audit event, got {decide_events!r}")
        ev = decide_events[0]
        after_text = ev.get("after") or ""
        if FEEDBACK not in str(after_text) or "PartiallyAdopted" not in str(after_text) and "部分采纳" not in str(after_text):
            # after field is like "PartiallyAdopted；{feedback}" from router
            if "PartiallyAdopted" not in str(after_text):
                raise RuntimeError(f"decide audit after mismatch: {ev!r}")
        if FEEDBACK not in str(after_text):
            raise RuntimeError(f"decide audit missing verbatim feedback: {ev!r}")
        chain = _http("GET", f"{API}/api/v1/cases/{CASE_ID}/audit:verify")
        if not (chain.get("valid") or chain.get("ok")):
            raise RuntimeError(f"audit chain invalid after save: {chain!r}")
        terminate(vite)
        vite = None
        terminate(host)
        host = None
        host2 = start_host(env, host_reopen_log)
        vite2 = start_vite(env, vite_reopen_log)
        reopen = run_browser_reopen(seed, shots)
        reopened = _http("GET", f"{API}/api/v1/cases/{CASE_ID}/consultation/rounds")
        if not isinstance(reopened, list) or len(reopened) != 1:
            raise RuntimeError(f"reopen rounds mismatch: {reopened!r}")
        rnd = reopened[0]
        if int(rnd.get("roundNo")) != seed["roundNo"] or rnd.get("draftVersion") != VER:
            raise RuntimeError(f"reopen round identity mismatch: {rnd!r}")
        comments = rnd.get("comments") or []
        hit = next((c for c in comments if c.get("commentId") == seed["commentId"]), None)
        if not hit:
            raise RuntimeError(f"reopen missing comment {seed['commentId']}: {comments!r}")
        if hit.get("decision") != "PartiallyAdopted" or hit.get("feedback") != FEEDBACK:
            raise RuntimeError(f"reopen comment mismatch: {hit!r}")
        if hit.get("text") != COMMENT_TEXT:
            raise RuntimeError(f"reopen comment text changed: {hit!r}")
        audit_reopen = _http("GET", f"{API}/api/v1/cases/{CASE_ID}/audit?category=Consultation")
        if audit_actions(audit_reopen) != after_actions:
            raise RuntimeError(
                f"reopen changed audit: before={after_actions} after={audit_actions(audit_reopen)}"
            )
        chain2 = _http("GET", f"{API}/api/v1/cases/{CASE_ID}/audit:verify")
        if not (chain2.get("valid") or chain2.get("ok")):
            raise RuntimeError(f"audit chain invalid after reopen: {chain2!r}")
        exit_doc.update(
            {
                "pass": True,
                "seed": {k: seed[k] for k in ("caseId", "roundNo", "draftVersion", "commentId")},
                "decide": decide,
                "reopen": reopen,
                "auditAfterSave": after,
                "auditAfterReopen": audit_reopen,
            }
        )
        print(
            "PASS official sandboxed Chrome: one pending opinion; "
            "partial adopt without reason did not save or write; "
            "synthetic feedback saved once; same SQLite reopen kept "
            "round, comment id, decision and verbatim feedback; "
            "request and audit matched.",
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
        terminate(vite2)
        terminate(host2)
        terminate(vite)
        terminate(host)
        for fh in (host_log, vite_log, host_reopen_log, vite_reopen_log):
            fh.close()


if __name__ == "__main__":
    sys.exit(main())
