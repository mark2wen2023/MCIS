"""Official sandboxed Chrome gate for keyboard use of the existing transcript locator.

Reuses the fixed synthetic interview already used by 8af8f3e. Does not re-run
time-matching or source-content checks, change product code, or treat HTTP/DOM
doubles as browser evidence.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
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
PIN = "8af8f3e8662c70b074cd9f0a5081d9a14ccdd4df"
PRODUCT = "d4452bb6c8aac41f2ce99c157b02a7e501f4f4ba"
CASE_ID = "SYN-W3-UTC-001"
UTC = "2026-02-01T12:01:40Z"
UTC_MS = "2026-02-01T12:01:40.125Z"
ANSWER_UNIQUE = "唯一时间的原有回答"
ANSWER_UNKNOWN = "时间未知的回答"
ANSWER_MS = "毫秒对应的原有回答"

JS_FOCUS = """() => {
  const el = document.activeElement;
  if (!el) return null;
  const cs = getComputedStyle(el);
  const rect = el.getBoundingClientRect();
  return {
    tag: el.tagName,
    type: el.getAttribute("type"),
    placeholder: el.getAttribute("placeholder"),
    role: el.getAttribute("role"),
    ariaCurrent: el.getAttribute("aria-current"),
    dataRound: el.getAttribute("data-round"),
    dataTestId: el.getAttribute("data-testid"),
    className: String(el.className || ""),
    id: el.id || "",
    text: ((el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement)
      ? el.value : (el.innerText || "")).slice(0, 200),
    matchesFocus: el.matches(":focus"),
    matchesFocusVisible: el.matches(":focus-visible"),
    outline: cs.outline,
    outlineWidth: cs.outlineWidth,
    outlineStyle: cs.outlineStyle,
    outlineColor: cs.outlineColor,
    outlineOffset: cs.outlineOffset,
    boxShadow: cs.boxShadow,
    border: cs.border,
    borderColor: cs.borderColor,
    href: el.getAttribute("href"),
    hrefHash: (typeof location !== "undefined") ? location.hash : "",
  };
}"""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--node-modules", required=True)
    p.add_argument("--host-python", required=True)
    p.add_argument("--browser", required=True)
    p.add_argument("--evidence", required=True)
    return p.parse_args()


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def allowed_head() -> None:
    head = git_head()
    if head == PIN:
        return
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", PIN, "HEAD"], cwd=ROOT, text=True
    ).splitlines()
    unexpected = [p for p in changed if not p.startswith("tests_acceptance/w3-transcript-keyboard/")]
    if unexpected:
        raise RuntimeError(f"HEAD {head} changes product or other paths vs {PIN}: {unexpected}")


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def http(method: str, url: str, headers: dict[str, str], body: dict | None = None, expected: int = 200):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            status = resp.status
            payload = json.loads(raw.decode()) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        raise RuntimeError(f"{method} {url} -> {exc.code}: {raw.decode('utf-8', 'replace')}") from exc
    if status != expected:
        raise RuntimeError(f"{method} {url} -> {status}, expected {expected}")
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


def wait_ready(proc: subprocess.Popen, api: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"host exited {proc.returncode} before ready")
        try:
            urllib.request.urlopen(f"{api}/api/v1/health", timeout=0.4).read()
            return
        except Exception:
            time.sleep(0.05)
    raise RuntimeError("host ready timed out")


def utf16_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def seed_registered_transcript(api: str, headers: dict[str, str]) -> dict:
    case = {
        "caseId": CASE_ID,
        "schemaVersion": "1.0.0",
        "title": "合成登记笔录定位（虚构）",
        "accidentType": "Collision",
        "incidentTimeUtc": "2026-02-01T12:00:00Z",
        "caseEpochUtc": "2026-02-01T11:00:00Z",
        "displayTimeZoneOffsetMinutes": 480,
        "incidentLocation": {"lonDeg": 120.0, "latDeg": 30.0},
        "isFictionalDemo": True,
        "placeName": "虚构水域",
    }
    http("POST", f"{api}/api/v1/cases", headers, case, 201)
    evidence = http(
        "POST",
        f"{api}/api/v1/cases/{CASE_ID}/evidence",
        headers,
        {
            "title": "合成登记笔录来源（虚构，仅哈希）",
            "source": "合成登记",
            "extractedBy": "首席调查官",
            "extractedUtc": "2026-02-01T11:30:00Z",
            "sha256": "a" * 64,
            "confidentiality": "Normal",
            "category": "Other",
            "note": "不提供原件字节，只登记哈希",
        },
        201,
    )
    eid = evidence["evidenceId"]
    sha = evidence.get("sha256") or evidence.get("currentSha256")
    if not isinstance(sha, str) or len(sha) != 64:
        raise RuntimeError(f"service did not return a bound sha256: {evidence!r}")
    interview = http(
        "POST",
        f"{api}/api/v1/cases/{CASE_ID}/interviews",
        headers,
        {
            "interviewee": {
                "intervieweeId": "SYN-P-01",
                "name": "虚构受询问人甲",
                "role": "虚构值班员",
                "affiliation": "虚构船",
            },
            "startUtc": "2026-02-01T12:00:00Z",
            "location": "虚构询问室",
            "recorder": "虚构记录员",
            "interviewers": ["虚构调查员"],
            "evidenceId": eid,
        },
        201,
    )
    record_id = interview["recordId"]
    if interview.get("sourceSha256") != sha:
        raise RuntimeError(f"server did not bind sourceSha256: {interview.get('sourceSha256')!r}")
    turns = [
        {"question": "合成问题甲", "answer": ANSWER_UNKNOWN, "utc": None},
        {"question": "合成问题乙", "answer": ANSWER_UNIQUE, "utc": UTC},
        {"question": "合成问题丙", "answer": ANSWER_MS, "utc": UTC_MS},
    ]
    for body in turns:
        http("POST", f"{api}/api/v1/cases/{CASE_ID}/interviews/{record_id}/turns", headers, body, 201)
    statement = http(
        "POST",
        f"{api}/api/v1/cases/{CASE_ID}/interviews/{record_id}/statements",
        headers,
        {
            "kind": "Time",
            "subject": "synthetic.event_time",
            "summary": "虚构事故时刻：另一个时间",
            "claim": {"valueType": "EventTime", "time": UTC_MS},
            "referenceUtc": UTC_MS,
            "span": {"round": 2, "field": "Answer", "start": 0, "length": utf16_len(ANSWER_UNIQUE)},
            "extractedBy": "Investigator",
        },
        201,
    )
    sid = statement["statementId"]
    http(
        "POST",
        f"{api}/api/v1/cases/{CASE_ID}/interview-compare/{record_id}/rows/{sid}:recheck",
        headers,
        {
            "outcome": "Consistent",
            "observedText": "合成观测（虚构）",
            "sourceLabel": "合成数据源（虚构）",
            "delta": None,
            "deltaUnit": "",
            "reason": "",
        },
        200,
    )
    http(
        "POST",
        f"{api}/api/v1/cases/{CASE_ID}/interview-compare/{record_id}/rows/{sid}:confirm",
        headers,
        {"note": "合成确认（虚构）"},
        200,
    )
    page = http("GET", f"{api}/api/v1/cases/{CASE_ID}/interview-compare/{record_id}", headers)
    rec = page["record"]
    if rec.get("evidenceId") != eid or rec.get("sourceSha256") != sha:
        raise RuntimeError("compare page is missing the registered source binding")
    return {
        "caseId": CASE_ID,
        "recordId": record_id,
        "evidenceId": eid,
        "sourceSha256": sha,
        "statementId": sid,
        "pageTurns": [{"round": t["round"], "utc": t.get("utc")} for t in page["turns"]],
    }


def ensure_node_modules(src: Path) -> None:
    target = ROOT / "web" / "node_modules"
    if target.exists() or target.is_symlink():
        return
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


def tab_until(page, predicate, limit: int = 40) -> tuple[dict, list[dict]]:
    trail: list[dict] = []
    for _ in range(limit):
        page.keyboard.press("Tab")
        info = page.evaluate(JS_FOCUS)
        trail.append(info)
        if info and predicate(info):
            return info, trail
    raise RuntimeError(f"keyboard entry not reached in {limit} Tabs: {trail!r}")


def has_visible_focus(info: dict) -> bool:
    width = str(info.get("outlineWidth") or "")
    style = str(info.get("outlineStyle") or "")
    shadow = str(info.get("boxShadow") or "")
    if style not in ("", "none") and width not in ("", "0px"):
        return True
    if shadow and shadow != "none":
        return True
    return False


def run_browser(seed: dict, shot_dir: Path, web: str, chrome: str) -> dict:
    from playwright.sync_api import sync_playwright

    shot_dir.mkdir(parents=True, exist_ok=True)
    requests: list[str] = []
    page_errors: list[str] = []
    with sync_playwright() as pw, tempfile.TemporaryDirectory(prefix="w3-kbd-chrome-") as tmp:
        browser = pw.chromium.launch(
            executable_path=chrome,
            headless=True,
            chromium_sandbox=True,
            args=[],
            env={**os.environ, "HOME": tmp, "XDG_CONFIG_HOME": f"{tmp}/config"},
        )
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(20000)
        page.on("pageerror", lambda exc: page_errors.append(str(exc)))
        page.on("request", lambda req: requests.append(req.url))

        page.goto(f"{web}/#/interview?case={CASE_ID}")
        page.locator('select[title="X-MCIS-Role"]').select_option("LeadInvestigator")
        page.get_by_text("定位问答", exact=True).wait_for()
        body_text = page.locator("body").inner_text()
        if ANSWER_UNIQUE not in body_text:
            raise RuntimeError("official interview page did not show the fixed synthetic answers")

        # Keyboard only from the existing locate entry. Do not click or fill().
        try:
            entry, entry_trail = tab_until(
                page, lambda info: info.get("placeholder") == "YYYY-MM-DDTHH:mm:ssZ"
            )
        except RuntimeError as exc:
            (shot_dir / "00-entry-breakpoint.png")
            page.screenshot(path=str(shot_dir / "00-entry-breakpoint.png"), full_page=True)
            version = browser.version
            browser.close()
            return {
                "pass": False,
                "breakpoint": "existing locate input was not keyboard-reachable",
                "error": str(exc),
                "entryTrail": getattr(exc, "args", [None]) and None,
                "version": f"Google Chrome {version}",
                "chromiumSandbox": True,
                "noSandboxArg": False,
                "screenshots": ["00-entry-breakpoint.png"],
                "pageErrors": page_errors,
            }

        page.keyboard.type(UTC, delay=20)
        typed = page.evaluate(
            """() => {
              const el = document.activeElement;
              return (el && 'value' in el) ? el.value : null;
            }"""
        )
        if typed != UTC:
            raise RuntimeError(f"typed UTC did not land in the locate field: {typed!r}")
        # Submit the existing official form with Enter; do not click the button.
        page.keyboard.press("Enter")
        page.get_by_text("已定位到第 2 轮", exact=False).wait_for()
        # Allow the product useEffect to move focus to the located turn.
        page.wait_for_function(
            """() => {
              const el = document.activeElement;
              return !!(el && el.getAttribute('aria-current') === 'location'
                        && el.getAttribute('data-round') === '2');
            }""",
            timeout=5000,
        )
        located = page.evaluate(JS_FOCUS)
        marker = page.locator('[aria-current="location"]')
        if marker.count() != 1:
            raise RuntimeError(f"expected one located turn, got {marker.count()}")
        marker_text = marker.inner_text()
        if marker.get_attribute("data-round") != "2" or ANSWER_UNIQUE not in marker_text:
            raise RuntimeError(f"located turn is not original round 2: {marker_text!r}")
        if ANSWER_UNKNOWN in marker_text or ANSWER_MS in marker_text:
            raise RuntimeError("located turn mixed in other rounds")
        page.locator('[aria-current="location"]').evaluate(
            "el => el.scrollIntoView({block:'center'})"
        )
        page.screenshot(path=str(shot_dir / "01-located-focus.png"), full_page=True)
        marker.screenshot(path=str(shot_dir / "01-located-focus-close.png"))

        visible = has_visible_focus(located) or bool(located.get("matchesFocusVisible"))
        hash_before = page.evaluate("() => location.hash")
        page.keyboard.press("Tab")
        after_tab = page.evaluate(JS_FOCUS)
        hash_after = page.evaluate("() => location.hash")
        page.screenshot(path=str(shot_dir / "02-after-tab.png"), full_page=True)

        same_page = hash_after == hash_before and CASE_ID in (hash_after or "")
        moved = (after_tab or {}).get("tag") and (
            after_tab.get("ariaCurrent") != "location"
            or after_tab.get("dataRound") != "2"
            or after_tab.get("tag") != located.get("tag")
            or after_tab.get("text") != located.get("text")
        )
        operable = (after_tab or {}).get("tag") in {"BUTTON", "INPUT", "SELECT", "A", "TEXTAREA"}
        still_operable = bool(same_page and moved and operable)

        original_reads = [
            u
            for u in requests
            if ("/archive-history/" in u and "/content" in u)
            or ("/evidence/" in u and u.rstrip("/").endswith("/content"))
            or "/evidence:download" in u
        ]
        version = browser.version
        browser.close()

        result = {
            "pass": False,
            "version": f"Google Chrome {version}",
            "chromiumSandbox": True,
            "noSandboxArg": False,
            "caseId": seed["caseId"],
            "recordId": seed["recordId"],
            "statementId": seed["statementId"],
            "product": PRODUCT,
            "pin": PIN,
            "entryFocus": entry,
            "entryTabCount": len(entry_trail),
            "locatedFocus": located,
            "locatedVisualFocus": visible,
            "afterTabFocus": after_tab,
            "samePageAfterTab": same_page,
            "stillOperableAfterTab": still_operable,
            "hashBefore": hash_before,
            "hashAfter": hash_after,
            "pageErrors": page_errors,
            "forbiddenOriginalReads": original_reads,
            "screenshots": ["01-located-focus.png", "01-located-focus-close.png", "02-after-tab.png"],
        }
        if not located.get("matchesFocus") or located.get("ariaCurrent") != "location" or located.get("dataRound") != "2":
            result["breakpoint"] = "after keyboard locate, activeElement was not the original located Q&A"
            return result
        if not visible:
            result["breakpoint"] = (
                "keyboard locate moved activeElement to original Q&A round 2, "
                "but no measurable visual focus (outline/box-shadow/:focus-visible)"
            )
            return result
        if not still_operable:
            result["breakpoint"] = (
                "after locate, further Tab did not land on an operable control on the same page"
            )
            return result
        if original_reads:
            result["breakpoint"] = f"unexpected original-file reads: {original_reads}"
            return result
        if page_errors:
            result["breakpoint"] = f"page errors: {page_errors}"
            return result
        result["pass"] = True
        return result


def main() -> int:
    args = parse_args()
    allowed_head()
    evidence = Path(args.evidence).resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    logs = evidence / "logs"
    shots = evidence / "screenshots"
    logs.mkdir(parents=True, exist_ok=True)
    shots.mkdir(parents=True, exist_ok=True)
    host_python = Path(args.host_python).absolute()
    node_modules = Path(args.node_modules).absolute()
    chrome = args.browser
    ensure_node_modules(node_modules)

    api_port = free_port()
    web_port = free_port()
    api = f"http://127.0.0.1:{api_port}"
    web = f"http://127.0.0.1:{web_port}"
    headers = {
        "Content-Type": "application/json",
        "X-MCIS-Role": "LeadInvestigator",
        "X-MCIS-Operator": urllib.parse.quote("首席调查官", safe=""),
    }
    data_dir = Path(tempfile.mkdtemp(prefix="w3-kbd-sqlite-"))
    host_log = (logs / "01-host.log").open("w", encoding="utf-8")
    vite_log = (logs / "02-vite.log").open("w", encoding="utf-8")
    host = vite = None
    exit_doc: dict = {
        "pass": False,
        "chromiumSandbox": True,
        "noSandboxArg": False,
        "product": PRODUCT,
        "pin": PIN,
        "api": api,
        "web": web,
    }
    try:
        env = {
            **os.environ,
            "MCIS_DATA_DIR": str(data_dir),
            "MCIS_SEED_DEMO": "0",
            "MCIS_PORT": str(api_port),
            "MCIS_API": api,
            "PYTHONPATH": str(ROOT / "service"),
        }
        host = subprocess.Popen(
            [str(host_python), "-u", str(HERE / "host.py")],
            cwd=str(ROOT),
            env=env,
            stdout=host_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        wait_ready(host, api)
        seed = seed_registered_transcript(api, headers)
        (logs / "00-seed.json").write_text(json.dumps(seed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        vite = subprocess.Popen(
            [
                "node",
                "node_modules/vite/bin/vite.js",
                "--host",
                "127.0.0.1",
                "--port",
                str(web_port),
                "--strictPort",
            ],
            cwd=str(ROOT / "web"),
            env=env,
            stdout=vite_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        wait_http(web + "/", timeout=40)
        result = run_browser(seed, shots, web, chrome)
        exit_doc.update(result)
        if result.get("pass"):
            print(
                "PASS official sandboxed Chrome: keyboard reached existing locate entry; "
                "Enter located original Q&A round 2; activeElement and visual focus matched; "
                "further Tab stayed on the page and reached an operable control.",
                flush=True,
            )
            return 0
        reason = result.get("breakpoint") or result.get("error") or "unspecified breakpoint"
        print(f"BREAKPOINT {reason}", flush=True)
        return 2
    except Exception as exc:  # noqa: BLE001
        exit_doc["error"] = str(exc)
        exit_doc["traceback"] = traceback.format_exc()
        print(f"FAIL {exc}", flush=True)
        traceback.print_exc()
        return 1
    finally:
        (logs / "03-browser-exit.json").write_text(
            json.dumps(exit_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        terminate(vite)
        terminate(host)
        host_log.close()
        vite_log.close()


if __name__ == "__main__":
    sys.exit(main())
