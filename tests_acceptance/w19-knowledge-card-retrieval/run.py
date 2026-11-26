"""Official W19 reviewed-card keyword search and source return. Not vector, not browser."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

PIN = "94d5e38c926fda232bb987b60fa9145e4bcf01a7"
TOKEN = "SYN-W19-RETR-7f3a9c"
HERE = Path(__file__).resolve().parent
WORKTREE = HERE.parents[1]
API = "/api/v1/knowledge"
LEAD = {"X-MCIS-Role": "LeadInvestigator", "X-MCIS-Operator": "LocalSyntheticLead"}
INVESTIGATOR = {"X-MCIS-Role": "Investigator", "X-MCIS-Operator": "LocalSyntheticInvestigator"}
PUBLIC = {"X-MCIS-Role": "Public", "X-MCIS-Operator": "SyntheticPublic"}

def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

def http_json(method, url, headers=None, body=None, timeout=30):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/json")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            return response.status, dict(response.headers), json.loads(raw.decode()) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        parsed = None
        if raw:
            try:
                parsed = json.loads(raw.decode())
            except json.JSONDecodeError:
                parsed = {"raw": raw.decode("utf-8", "replace")[:400]}
        return exc.code, dict(exc.headers), parsed

def wait_health(base, timeout=30):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            status, _, body = http_json("GET", base + "/api/v1/health", timeout=2)
            if status == 200 and body and body.get("status") == "ok":
                return body
            last = (status, body)
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as exc:
            last = str(exc)
        time.sleep(0.1)
    raise RuntimeError(f"Health check failed: {last}")

def bind_listeners(pid: int):
    rows = []
    path = Path("/proc/net/tcp")
    if path.is_file():
        for line in path.read_text().splitlines()[1:]:
            parts = line.split()
            local, state, inode = parts[1], parts[3], parts[9]
            if state != "0A":
                continue
            addr, port_hex = local.rsplit(":", 1)
            nums = bytes.fromhex(addr)
            host = ".".join(str(b) for b in nums[::-1])
            rows.append({"addr": host, "port": int(port_hex, 16), "inode": inode})
    owned = set()
    fds = Path(f"/proc/{pid}/fd")
    if fds.is_dir():
        for entry in fds.iterdir():
            try:
                target = os.readlink(entry)
            except OSError:
                continue
            if target.startswith("socket:["):
                owned.add(target[8:-1])
    return [row for row in rows if not owned or row["inode"] in owned]

def start_loopback(app, host, port):
    import uvicorn
    if host != "127.0.0.1":
        raise SystemExit("Service must bind 127.0.0.1 only")
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="w19-knowledge-retrieval", daemon=True)
    thread.start()
    return server, thread

def stop_loopback(server, thread, port, timeout=10):
    server.should_exit = True
    thread.join(timeout=timeout)
    deadline = time.time() + 10
    while time.time() < deadline:
        sock = socket.socket()
        sock.settimeout(0.2)
        try:
            sock.connect(("127.0.0.1", port))
        except (ConnectionRefusedError, ConnectionResetError, OSError):
            sock.close()
            return
        else:
            sock.close()
            time.sleep(0.05)
    raise RuntimeError(f"Port {port} still accepting connections")

def card(label, excerpt):
    return {
        "kind": "Method",
        "title": f"合成知识卡 {TOKEN} {label}",
        "summary": f"仅用于检索出处对照的合成样本 {TOKEN}",
        "body": f"合成正文，不是真实事故。标记 {TOKEN}。{label}",
        "tags": ["synthetic-w19", TOKEN.lower()],
        "applicability": "不能当真实结论",
        "source": {
            "type": "Synthetic",
            "title": f"合成夹具-{label}",
            "locator": "段落1",
            "excerpt": excerpt,
            "rightsNote": "测试作者构造，不含真实资料",
        },
    }

def main():
    if not __debug__:
        raise SystemExit("Assertions must be enabled")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18767)
    args = parser.parse_args()
    if not args.python.is_absolute() or not os.access(args.python, os.X_OK):
        raise SystemExit("BLOCKED: preinstalled service Python not found")
    report = args.report.resolve()
    report.mkdir(parents=True, exist_ok=True)
    out = report / "official"
    if out.exists():
        import shutil
        shutil.rmtree(out)
    out.mkdir()
    logs = []

    def log(msg):
        line = msg if msg.endswith("\n") else msg + "\n"
        sys.stdout.write(line)
        sys.stdout.flush()
        logs.append(line)

    if not (WORKTREE / ".git").exists():
        raise SystemExit("Candidate worktree missing")
    head = subprocess.check_output(["git", "-C", str(WORKTREE), "rev-parse", "HEAD"], text=True).strip()
    if head != PIN:
        base_ok = subprocess.run(["git", "-C", str(WORKTREE), "merge-base", "--is-ancestor", PIN, "HEAD"]).returncode == 0
        if not base_ok:
            raise SystemExit(f"HEAD {head} is not {PIN} or a descendant")
        diff = subprocess.check_output(["git", "-C", str(WORKTREE), "diff", "--name-only", PIN, "HEAD"], text=True).splitlines()
        allowed_prefix = "tests_acceptance/w19-knowledge-card-retrieval/"
        if any(not path.startswith(allowed_prefix) for path in diff):
            raise SystemExit(f"Unexpected changes versus pin: {diff}")
    router = WORKTREE / "service/mcis_service/knowledge/router.py"
    router_sha = sha_file(router)
    log(f"Pin HEAD={head}; knowledge/router.py SHA-256={router_sha}")
    log("Search type: literal case-folded substring (keyword), not vector/semantic")

    sys.path[:0] = [str(WORKTREE / "service")]
    from mcis_service.config import Settings
    from mcis_service.main import create_app

    data_dir = report / "tmp-official" / "data"
    if data_dir.exists():
        import shutil
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True)
    db = data_dir / "w19.sqlite"
    cfg = Settings(data_dir=data_dir, db_url=f"sqlite:///{db}", seed_demo=False)
    app = create_app(cfg)
    server, thread = start_loopback(app, "127.0.0.1", args.port)
    try:
        base = f"http://127.0.0.1:{args.port}"
        wait_health(base)
        listeners = bind_listeners(os.getpid())
        write_json(out / "listeners.json", listeners)
        if any(row["addr"] in {"0.0.0.0", "::", "00000000"} and row["port"] == args.port for row in listeners):
            raise SystemExit(f"Non-loopback bind: {listeners}")
        log(f"Listening on 127.0.0.1:{args.port}")

        published_src = {
            "type": "Synthetic", "title": "合成夹具-published", "locator": "段落1",
            "excerpt": "SYN-W19-RETR-SRC-PUB", "rightsNote": "测试作者构造，不含真实资料",
        }
        pending_src = {
            "type": "Synthetic", "title": "合成夹具-pending", "locator": "段落1",
            "excerpt": "SYN-W19-RETR-SRC-CAND", "rightsNote": "测试作者构造，不含真实资料",
        }
        withdrawn_src = {
            "type": "Synthetic", "title": "合成夹具-withdrawn", "locator": "段落1",
            "excerpt": "SYN-W19-RETR-SRC-WDN", "rightsNote": "测试作者构造，不含真实资料",
        }

        def create_one(label, source):
            body = card(label, source["excerpt"])
            body["source"] = source
            status, _, created = http_json("POST", base + API + "/cards", headers=INVESTIGATOR, body=body)
            if status != 201 or created.get("status") != "Candidate":
                raise SystemExit(f"Create {label} failed: {status} {created}")
            return created

        def review_one(doc, decision):
            payload = {
                "decision": decision,
                "expectedDigest": doc["contentDigest"],
                "note": "已人工核查，允许发布或撤回合成测试样本",
                "sourceVerified": True,
                "rightsVerified": True,
                "releaseApproved": True,
            }
            status, _, reviewed = http_json("POST", base + API + f"/cards/{doc['cardId']}/review", headers=LEAD, body=payload)
            if status != 200 or reviewed.get("status") != decision:
                raise SystemExit(f"Review {doc['cardId']} -> {decision} failed: {status} {reviewed}")
            return reviewed

        pending = create_one("pending", pending_src)
        published = review_one(create_one("published", published_src), "Published")
        withdrawn = review_one(review_one(create_one("withdrawn", withdrawn_src), "Published"), "Withdrawn")
        write_json(out / "created-cards.json", {
            "count": 3,
            "note": "Dot said two records; three is the minimum to hold Published, Candidate and Withdrawn in one usable-search snapshot. Cards on this SHA are not case-scoped.",
            "published": published["cardId"],
            "pending": pending["cardId"],
            "withdrawn": withdrawn["cardId"],
        })
        log(f"Created 3 synthetic cards: published={published['cardId']} pending={pending['cardId']} withdrawn={withdrawn['cardId']}")

        # Usable results: Public default Published keyword search.
        status, _, usable = http_json(
            "GET",
            base + API + f"/cards?q={urllib.request.quote(TOKEN)}",
            headers=PUBLIC,
        )
        write_json(out / "usable-search.json", {"status": status, "body": usable})
        if status != 200:
            raise SystemExit(f"Usable search failed: {status} {usable}")
        ids = [item["cardId"] for item in usable["items"]]
        if usable["total"] != 1 or ids != [published["cardId"]]:
            raise SystemExit(f"Usable search must return only the published card, got {usable}")
        source = usable["items"][0]["content"]["source"]
        if source != published_src:
            raise SystemExit(f"Returned source mismatch: {source}")
        if pending["cardId"] in ids or withdrawn["cardId"] in ids:
            raise SystemExit("Pending or withdrawn entered usable results")
        log("Usable Public search PASS: only the reviewed Published card, original source returned")

        # Explicit Published filter with the same keyword, Lead role, still only published.
        status, _, lead_pub = http_json("GET", base + API + f"/cards?status=Published&q={urllib.request.quote(TOKEN)}", headers=LEAD)
        lead_ids = [item["cardId"] for item in lead_pub["items"]]
        if status != 200 or lead_pub["total"] != 1 or lead_ids != [published["cardId"]]:
            raise SystemExit(f"Lead Published search mismatch: {status} {lead_pub}")
        if lead_pub["items"][0]["content"]["source"] != published_src:
            raise SystemExit("Lead Published search source mismatch")

        # Public cannot use internal status filters; pending/withdrawn are not usable this way.
        for st in ("Candidate", "Withdrawn"):
            status, _, denied = http_json("GET", base + API + f"/cards?status={st}&q={urllib.request.quote(TOKEN)}", headers=PUBLIC)
            if status != 403:
                raise SystemExit(f"Public status={st} expected 403, got {status} {denied}")
        # Internal listing can see the other states, but they are not usable published results.
        status, _, cand = http_json("GET", base + API + f"/cards?status=Candidate&q={urllib.request.quote(TOKEN)}", headers=LEAD)
        status2, _, wdn = http_json("GET", base + API + f"/cards?status=Withdrawn&q={urllib.request.quote(TOKEN)}", headers=LEAD)
        write_json(out / "internal-status-filters.json", {"candidate": cand, "withdrawn": wdn})
        if [i["cardId"] for i in cand["items"]] != [pending["cardId"]] or [i["cardId"] for i in wdn["items"]] != [withdrawn["cardId"]]:
            raise SystemExit(f"Internal status lists unexpected: {cand} {wdn}")
        log("Pending and withdrawn stay out of usable Published results; Public cannot query those statuses")

        status, _, audit = http_json("GET", base + API + "/audit:verify", headers=LEAD)
        write_json(out / "audit-verify.json", audit)
        # 3 creates + 1 publish + 1 publish + 1 withdraw = 6 events
        if status != 200 or not audit.get("valid") or audit.get("count") != 6:
            raise SystemExit(f"Audit verify unexpected: {status} {audit}")
        log("Knowledge audit chain valid, count=6")
    finally:
        stop_loopback(server, thread, args.port)
        try:
            app.state.db.engine.dispose()
        except Exception:
            pass

    receipt = {
        "passed": True,
        "kind": "w19-knowledge-card-retrieval",
        "pin": PIN,
        "pinReason": "origin/main HEAD, GitHub-verifiable; existing review+search+source path; later W19 search candidates do not change knowledge/router.py versus this SHA; avoids 8183226 template Chromium work",
        "searchType": "literal-substring-keyword",
        "vectorSearch": False,
        "httpNotBrowser": True,
        "notWholePackage": True,
        "recordCount": 3,
        "recordCountNote": "Dot said two records; three is the minimum to hold Published, Candidate and Withdrawn in one usable-search snapshot. Knowledge cards on this SHA are not case-scoped.",
        "routerSha256": router_sha,
        "bind": "127.0.0.1",
        "usableSearch": {
            "path": "GET /api/v1/knowledge/cards?q=... (default status=Published)",
            "role": "Public",
            "total": 1,
            "returnedSource": published_src,
        },
        "firstBreakpoint": None,
    }
    write_json(out / "receipt.json", receipt)
    (out / "console.log").write_text("".join(logs) + "OFFICIAL RESULT: keyword search PASS (HTTP, not browser, not vector); W19 whole-package 未验\n", encoding="utf-8")
    log("OFFICIAL RESULT: keyword search PASS (HTTP, not browser, not vector); W19 whole-package 未验")
    (out / "console.log").write_text("".join(logs), encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
