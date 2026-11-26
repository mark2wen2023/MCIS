"""Independent W19 keyword-control. Does not rerun lifecycle gates or edit run.py."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run as base

PIN_PARENT = "eeb7a2a152f95274346f07884fbe6f3b77c299b1"
ABSENT_Q = "ZXQ-ABSENT-W19-9K2M"
PRIOR_SOURCE = {
    "excerpt": "SYN-W19-RETR-SRC-PUB",
    "locator": "段落1",
    "rightsNote": "测试作者构造，不含真实资料",
    "title": "合成夹具-published",
    "type": "Synthetic",
}

def log(logs, msg):
    line = msg if msg.endswith("\n") else msg + "\n"
    sys.stdout.write(line)
    sys.stdout.flush()
    logs.append(line)

def collect_text(value, acc):
    if isinstance(value, str):
        acc.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            collect_text(item, acc)
    elif isinstance(value, list):
        for item in value:
            collect_text(item, acc)

def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()

def main():
    if not __debug__:
        raise SystemExit("Assertions must be enabled")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18768)
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
    logs, sequence = [], []

    def step(name):
        sequence.append(name)
        log(logs, f"STEP {len(sequence)}: {name}")

    worktree = base.WORKTREE
    if not (worktree / ".git").exists():
        raise SystemExit("Candidate worktree missing")
    head = subprocess.check_output(["git", "-C", str(worktree), "rev-parse", "HEAD"], text=True).strip()
    if head != PIN_PARENT:
        ok = subprocess.run(["git", "-C", str(worktree), "merge-base", "--is-ancestor", PIN_PARENT, "HEAD"]).returncode == 0
        if not ok:
            raise SystemExit(f"HEAD {head} is not {PIN_PARENT} or a descendant")
        diff = subprocess.check_output(["git", "-C", str(worktree), "diff", "--name-only", PIN_PARENT, "HEAD"], text=True).splitlines()
        allowed = {"tests_acceptance/w19-knowledge-card-retrieval/keyword_control.py"}
        if any(path not in allowed for path in diff):
            raise SystemExit(f"Unexpected changes versus eeb7a2a: {diff}")
    run_sha = base.sha_file(HERE / "run.py")
    if run_sha != "e7959f56cffc316f2bf0bb921f1b8b4a143213e94704513f6e6fe5196efbce09":
        raise SystemExit(f"run.py must stay unchanged at eeb7a2a, got {run_sha}")
    log(logs, f"HEAD={head}; run.py unchanged SHA-256={run_sha}")
    log(logs, "Prior W191 real-HTTP tests and eeb7a2a official run are not equivalent originals: different or same-case-only queries; no byte-level source compare for a case-changed q; no recorded absent-word precondition.")

    sys.path[:0] = [str(worktree / "service")]
    from mcis_service.config import Settings
    from mcis_service.main import create_app

    data_dir = report / "tmp-official" / "data"
    if data_dir.exists():
        import shutil
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True)
    cfg = Settings(data_dir=data_dir, db_url=f"sqlite:///{data_dir / 'w19.sqlite'}", seed_demo=False)
    app = create_app(cfg)
    server, thread = base.start_loopback(app, "127.0.0.1", args.port)
    try:
        step("start 127.0.0.1 service on a fresh empty SQLite")
        http_base = f"http://127.0.0.1:{args.port}"
        base.wait_health(http_base)
        listeners = base.bind_listeners(os.getpid())
        base.write_json(out / "listeners.json", listeners)
        if any(row["addr"] in {"0.0.0.0", "::", "00000000"} and row["port"] == args.port for row in listeners):
            raise SystemExit(f"Non-loopback bind: {listeners}")

        step("load the same 3-card synthetic fixture (setup only, not a lifecycle re-acceptance)")
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
            body = base.card(label, source["excerpt"])
            body["source"] = source
            status, _, created = base.http_json("POST", http_base + base.API + "/cards", headers=base.INVESTIGATOR, body=body)
            if status != 201:
                raise SystemExit(f"Create {label} failed: {status} {created}")
            return created, body

        def review_one(doc, decision):
            payload = {
                "decision": decision, "expectedDigest": doc["contentDigest"],
                "note": "已人工核查，允许发布或撤回合成测试样本",
                "sourceVerified": True, "rightsVerified": True, "releaseApproved": True,
            }
            status, _, reviewed = base.http_json("POST", http_base + base.API + f"/cards/{doc['cardId']}/review", headers=base.LEAD, body=payload)
            if status != 200:
                raise SystemExit(f"Review failed: {status} {reviewed}")
            return reviewed

        pending_doc, pending_body = create_one("pending", pending_src)
        published_created, published_body = create_one("published", published_src)
        published = review_one(published_created, "Published")
        withdrawn_created, withdrawn_body = create_one("withdrawn", withdrawn_src)
        withdrawn = review_one(review_one(withdrawn_created, "Published"), "Withdrawn")
        fixtures = {
            "pending": pending_body, "published": published_body, "withdrawn": withdrawn_body,
            "pendingId": pending_doc["cardId"], "publishedId": published["cardId"], "withdrawnId": withdrawn["cardId"],
        }
        base.write_json(out / "fixture-cards.json", {
            "count": 3, "published": published["cardId"],
            "pending": pending_doc["cardId"], "withdrawn": withdrawn["cardId"],
        })

        texts = []
        for body in (pending_body, published_body, withdrawn_body):
            collect_text(body, texts)
        corpus = "\n".join(texts)
        if ABSENT_Q in corpus or ABSENT_Q.casefold() in corpus.casefold():
            raise SystemExit(f"Absent probe {ABSENT_Q!r} leaked into the fixture")
        base.write_json(out / "absent-word-precondition.json", {
            "word": ABSENT_Q, "presentInFixture": False, "fixtureStringCount": len(texts),
        })
        log(logs, f"Fixture loaded; absent word {ABSENT_Q!r} not present in any sample string")

        def search(q):
            path = base.API + "/cards?q=" + urllib.parse.quote(q, safe="")
            status, headers, body = base.http_json("GET", http_base + path, headers=base.PUBLIC)
            return {"query": q, "path": path, "status": status, "headers": {k: v for k, v in headers.items()}, "body": body}

        step("baseline same-token usable search (same-process original control, not a lifecycle re-run)")
        baseline = search(base.TOKEN)
        base.write_json(out / "http-baseline-same-token.json", baseline)
        if baseline["status"] != 200 or baseline["body"]["total"] != 1:
            raise SystemExit(f"Baseline search failed: {baseline}")
        baseline_item = baseline["body"]["items"][0]
        if baseline_item["cardId"] != published["cardId"]:
            raise SystemExit("Baseline did not return the published card")
        if canonical(baseline_item["content"]["source"]) != canonical(published_src) or canonical(published_src) != canonical(PRIOR_SOURCE):
            raise SystemExit("Baseline source is not byte-identical to the fixture / prior official source")
        log(logs, f"Baseline q={base.TOKEN!r} -> {baseline_item['cardId']}")

        step("query A: case-swapped matching token, expect same card id and byte-identical source")
        case_q = base.TOKEN.swapcase()
        if case_q == base.TOKEN:
            raise SystemExit("Case-swapped query must differ from the original token")
        query_a = search(case_q)
        base.write_json(out / "http-query-a-case-swap.json", query_a)
        if query_a["status"] != 200:
            raise SystemExit(f"Query A HTTP {query_a['status']}: {query_a['body']}")
        if query_a["body"]["total"] != 1 or len(query_a["body"]["items"]) != 1:
            raise SystemExit(f"Query A must return exactly one item: {query_a['body']}")
        item_a = query_a["body"]["items"][0]
        if item_a["cardId"] != baseline_item["cardId"]:
            raise SystemExit(f"Query A card id {item_a['cardId']} != baseline {baseline_item['cardId']}")
        if canonical(item_a["content"]["source"]) != canonical(baseline_item["content"]["source"]):
            raise SystemExit("Query A source is not byte-identical to the original control")
        log(logs, f"Query A q={case_q!r} -> same id {item_a['cardId']}; source bytes match baseline and prior official source")

        step("query B: probe absent from every fixture string, expect empty items and total=0")
        query_b = search(ABSENT_Q)
        base.write_json(out / "http-query-b-absent.json", query_b)
        if query_b["status"] != 200:
            raise SystemExit(f"Query B HTTP {query_b['status']}: {query_b['body']}")
        if query_b["body"]["items"] != [] or query_b["body"]["total"] != 0:
            raise SystemExit(f"Query B must be empty total=0: {query_b['body']}")
        log(logs, f"Query B q={ABSENT_Q!r} -> items=[] total=0")
    finally:
        base.stop_loopback(server, thread, args.port)
        try:
            app.state.db.engine.dispose()
        except Exception:
            pass

    receipt = {
        "passed": True,
        "kind": "w19-keyword-control",
        "pin": base.PIN,
        "parentCandidate": PIN_PARENT,
        "searchType": "literal-substring-keyword",
        "vectorSearch": False,
        "httpNotBrowser": True,
        "notWholePackage": True,
        "equivalentOriginalCited": False,
        "equivalentOriginalNote": "W191/test_http.py is real 127.0.0.1 HTTP on 94d5e38 but uses a different fixture; case-fold queries only checked total; no byte-level source compare; no recorded absent-word precondition. eeb7a2a official run used a single same-case token.",
        "sequence": sequence,
        "queries": {
            "A": {"q": case_q, "status": 200, "total": 1, "cardId": item_a["cardId"], "sourceBytesMatchBaseline": True},
            "B": {"q": ABSENT_Q, "status": 200, "total": 0, "items": []},
        },
        "firstBreakpoint": None,
    }
    base.write_json(out / "receipt.json", receipt)
    base.write_json(out / "sequence.json", sequence)
    (out / "console.log").write_text("".join(logs), encoding="utf-8")
    log(logs, "OFFICIAL RESULT: keyword-control PASS (HTTP, not browser, not vector); W19 whole-package 未验")
    (out / "console.log").write_text("".join(logs), encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
