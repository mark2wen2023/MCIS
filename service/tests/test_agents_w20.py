"""W20 self-tests. Fake-model fixtures are explicitly NOT real model validation."""
import copy
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

from mcis_service.agents import model_client
from mcis_service.redaction.policy import default_policy
from .conftest import C, H

RECORD = "IR-90"
PATH = f"{C}/agents/people_ops/interviews/{RECORD}:extract"
QUOTE = "右满舵避让"
ITEM = {"kind": "Operation", "subject": "ship.rudder", "summary": "当事人声称右满舵避让（虚构测试）",
        "claim": {"valueType": "Occurrence", "occurred": True}, "round": 1, "field": "Answer", "quote": QUOTE}


@pytest.fixture(autouse=True)
def clean_model_env(monkeypatch):
    monkeypatch.delenv("MCIS_AGENT_BASE_URL", raising=False)
    monkeypatch.delenv("MCIS_AGENT_MODEL", raising=False)


@pytest.fixture()
def interview(client):
    doc = {"recordId": RECORD, "interviewee": {"intervieweeId": "P90", "name": "测试甲", "role": "船员",
        "affiliation": "虚构", "phone": "13812345678", "idNumber": "123456789012345678"},
        "startUtc": "2026-11-12T00:00:00Z", "turns": [{"round": 1, "question": "请说明行动。",
        "answer": "我是测试甲，电话13812345678。😀随后右满舵避让。私人片段", "sensitiveFragments": ["私人片段"]}], "statements": []}
    r = client.post(f"{C}/interviews", json=doc, headers=H())
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture()
def fake_model(monkeypatch):
    monkeypatch.setenv("MCIS_AGENT_BASE_URL", "http://127.0.0.1:12345/v1")
    monkeypatch.setenv("MCIS_AGENT_MODEL", "controlled-fake-not-real-model")
    calls = []
    def complete(cfg, messages):
        calls.append(messages)
        return json.dumps({"statements": [ITEM]}, ensure_ascii=False)
    monkeypatch.setattr(model_client, "complete", complete)
    return calls


def execute(client):
    r = client.post(PATH, headers=H())
    assert r.status_code == 201, r.text
    return r.json()


def review(client, d, decision="Confirmed", **extra):
    return client.post(f"{C}/agents/drafts/{d['draftId']}/review", headers=H(operator="测试调查员"),
                       json={"decision": decision, **extra})


def test_disabled_no_inference(client, interview):
    assert client.post(PATH, headers=H()).json()["code"] == "MODEL_NOT_CONFIGURED"
    assert all(x["status"] == "not_connected" for x in client.get("/api/v1/agents").json())


def test_end_to_end_fake_is_only_draft_until_human_review(client, interview, fake_model):
    d = execute(client)
    assert d["status"] == "PendingReview" and d["model"] == "controlled-fake-not-real-model"
    assert d["citations"] == [{"recordId": RECORD, "round": 1, "quote": QUOTE}]
    assert len(d["promptDigest"]) == 64
    assert not client.get(f"{C}/interviews/{RECORD}", headers=H()).json()["statements"]
    assert client.post(f"{C}/agents/drafts/{d['draftId']}/review", headers=H("AgentService"), json={"decision": "Confirmed"}).status_code == 403
    assert review(client, d).status_code == 200
    st = client.get(f"{C}/interviews/{RECORD}", headers=H()).json()["statements"][0]
    assert st["reviewStatus"] == "Confirmed" and st["extractedBy"] == "Agent" and st["revision"] == 1
    raw = interview["turns"][0]["answer"].encode("utf-16-le")
    assert raw[st["span"]["start"]*2:(st["span"]["start"]+st["span"]["length"])*2].decode("utf-16-le") == QUOTE
    assert review(client, d).status_code == 409
    reg = client.get("/api/v1/agents").json()
    assert len([a for a in reg if a["status"] == "configured"]) == 1


def test_redaction_minimal_input_even_with_weakened_policy(client, interview, fake_model):
    p = default_policy();p["fieldRules"] = []
    assert client.put(f"{C}/access-policy", json=p, headers=H("LeadInvestigator")).status_code == 200
    execute(client)
    sent = json.dumps(fake_model[0], ensure_ascii=False)
    for secret in ("测试甲", "13812345678", "123456789012345678", "私人片段", "affiliation", "statements\": []"):
        assert secret not in sent
    user = json.loads(fake_model[0][1]["content"])
    assert set(user) == {"turns"} and set(user["turns"][0]) == {"round", "question", "answer"}


@pytest.mark.parametrize("role", ["Public", "ExternalExpert", "InterestedState"])
def test_forbidden_role_never_calls_model(client, interview, fake_model, role):
    assert client.post(PATH, headers=H(role)).status_code == 403
    assert fake_model == []


@pytest.mark.parametrize("role,category", [("Investigator", "testimony"), ("AgentService", "testimony"), ("Investigator", "agent_drafts")])
def test_policy_denial_never_calls_model(client, interview, fake_model, role, category):
    p = default_policy();p["matrix"][role][category] = "Deny"
    assert client.put(f"{C}/access-policy", json=p, headers=H("LeadInvestigator")).status_code == 200
    assert client.post(PATH, headers=H()).status_code == 403
    assert fake_model == []


@pytest.mark.parametrize("change", [{"quote": "不存在"}, {"quote": ""}, {"round": 99}, {"quote": "私人片段"}, {"quote": "<ROLE_01>"}])
def test_bad_citation_no_draft_no_write(client, interview, fake_model, monkeypatch, change):
    before = client.get(f"{C}/agents/drafts", headers=H()).json()
    item = {**ITEM, **change}
    monkeypatch.setattr(model_client, "complete", lambda *_: json.dumps({"statements": [item]}))
    assert client.post(PATH, headers=H()).status_code in (422, 502)
    assert client.get(f"{C}/agents/drafts", headers=H()).json() == before
    assert not client.get(f"{C}/interviews/{RECORD}", headers=H()).json()["statements"]


@pytest.mark.parametrize("content", ['not json', '{"statements":[]}', '{"statements":[],"statements":[]}', '{"statements":NaN}', '{"statements":{},"tool":"write"}'])
def test_malformed_output_fail_closed(client, interview, fake_model, monkeypatch, content):
    monkeypatch.setattr(model_client, "complete", lambda *_: content)
    assert client.post(PATH, headers=H()).json()["code"] == "MODEL_OUTPUT_INVALID"


def test_reject_and_modify(client, interview, fake_model):
    d = execute(client)
    assert review(client, d, "Rejected").status_code == 200
    assert not client.get(f"{C}/interviews/{RECORD}", headers=H()).json()["statements"]
    d = execute(client);p = copy.deepcopy(d["payload"]);p["statements"][0]["summary"] = "人工核实的陈述（虚构）"
    assert review(client, d, "Confirmed", payload=p).status_code == 422
    assert review(client, d, "Modified", payload=p).status_code == 200
    assert client.get(f"{C}/interviews/{RECORD}", headers=H()).json()["statements"][0]["summary"] == p["statements"][0]["summary"]


def test_changed_source_cannot_apply(client, interview, fake_model):
    d = execute(client)
    assert client.post(f"{C}/interviews/{RECORD}/turns", headers=H(), json={"question": "补充", "answer": "变化"}).status_code == 201
    assert review(client, d).json()["code"] == "SOURCE_CHANGED"
    assert not client.get(f"{C}/interviews/{RECORD}", headers=H()).json()["statements"]
    assert next(x for x in client.get(f"{C}/agents/drafts", headers=H()).json() if x["draftId"] == d["draftId"])["status"] == "PendingReview"


def test_no_forged_managed_draft_and_no_modified_source(client, interview, fake_model):
    d = execute(client)
    assert client.post(f"{C}/agents/drafts", headers=H("AgentService"), json=d).status_code == 422
    p = copy.deepcopy(d["payload"]);p["statements"][0]["quote"] = "随后"
    assert review(client, d, "Modified", payload=p).json()["code"] == "SOURCE_IMMUTABLE"


@pytest.mark.parametrize("base", ["https://api.openai.com/v1", "http://localhost:1234/v1", "http://127.0.0.1.evil:1234/v1", "http://127.0.0.1:1234/v1?token=x", "http://user:secret@127.0.0.1:1234/v1", "http://0.0.0.0:1234/v1"])
def test_remote_and_ambiguous_urls_rejected(client, interview, monkeypatch, base):
    monkeypatch.setenv("MCIS_AGENT_BASE_URL", base);monkeypatch.setenv("MCIS_AGENT_MODEL", "test")
    assert client.post(PATH, headers=H()).json()["code"] == "MODEL_CONFIG_INVALID"
    assert client.get("/api/v1/agents").json()[3]["status"] == "invalid_configuration"


def test_real_http_protocol_fake_server_not_real_model(client, interview, monkeypatch):
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_POST(self):
            requests.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"]))), dict(self.headers)))
            body = json.dumps({"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"statements": [ITEM]})}}]}).encode()
            self.send_response(200);self.end_headers();self.wfile.write(body)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True);thread.start()
    monkeypatch.setenv("MCIS_AGENT_BASE_URL", f"http://127.0.0.1:{server.server_port}/v1")
    monkeypatch.setenv("MCIS_AGENT_MODEL", "http-fixture-not-real-model")
    try:
        d = execute(client)
        assert review(client, d).status_code == 200
        path, body, headers = requests[0]
        assert path == "/v1/chat/completions" and body["model"] == "http-fixture-not-real-model"
        assert body["stream"] is False and "Authorization" not in headers
    finally:
        server.shutdown();server.server_close();thread.join()


def test_transport_timeout_no_sensitive_error(monkeypatch):
    class Broken:
        def __init__(self, **kw): assert kw["trust_env"] is False and kw["follow_redirects"] is False
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def stream(self, *a, **kw): raise httpx.ReadTimeout("secret upstream details")
    monkeypatch.setattr(model_client.httpx, "Client", Broken)
    with pytest.raises(Exception) as e:
        model_client.complete(model_client.ModelConfig("http://127.0.0.1:1/v1", "fake"), [])
    assert e.value.status_code == 504 and "secret" not in str(e.value.detail)


def test_redaction_union_in_original_coordinates():
    from mcis_service.agents.extraction import redacted_input
    doc = {"interviewee": {"name": "测试甲"}, "turns": [{"round": 1, "question": "说明", "answer": "测试甲隐私abcdef随后操舵",
        "sensitiveFragments": ["测试甲隐私abc", "abcdef", "bcde"]}]}
    data = redacted_input(doc, default_policy())
    assert data["turns"][0]["answer"] == "[已遮盖]随后操舵"
    assert doc["turns"][0]["answer"] == "测试甲隐私abcdef随后操舵"


@pytest.mark.parametrize("content", ['{"statements":[{"claim":{"scalar":1e400}}]}', '{"statements":[{"summary":"\\ud800"}]}'])
def test_nonfinite_or_invalid_unicode_model_output(client, interview, fake_model, monkeypatch, content):
    monkeypatch.setattr(model_client, "complete", lambda *_: content)
    assert client.post(PATH, headers=H()).json()["code"] == "MODEL_OUTPUT_INVALID"
