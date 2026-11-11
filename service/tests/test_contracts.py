"""契约一致性：schema 本身合法、种子数据与接口输出符合 schema、openapi.yaml 与实际路由一一对应。"""
import json
import re

import pytest
import yaml
from jsonschema import Draft202012Validator

from mcis_service.common import contracts
from mcis_service.config import PROJECT_ROOT

from .conftest import C, H


def test_all_schemas_are_valid_2020_12():
    files = list((PROJECT_ROOT / "contracts" / "schemas").glob("*.schema.json"))
    assert len(files) >= 16
    for f in files:
        Draft202012Validator.check_schema(json.loads(f.read_text(encoding="utf-8")))


def _ok(ref, doc):
    errs = contracts.errors(ref, doc)
    assert not errs, f"{ref}: {errs[:5]}"


def test_seed_and_responses_conform(client):
    h = H("LeadInvestigator")
    _ok("case", client.get(C, headers=h).json())
    for v in client.get(f"{C}/vessels", headers=h).json():
        _ok("vessel", v)
    tracks = client.get(f"{C}/tracks", headers=h).json()["tracks"]
    assert {t["vesselId"] for t in tracks} == {"vessel_lily", "vessel_mary"}
    for t in tracks:
        for p in t["points"]:
            _ok("track-point", p)
    for e in client.get(f"{C}/evidence", headers=h).json():
        _ok("evidence-item", e)
        for ce in client.get(f"{C}/evidence/{e['evidenceId']}/custody", headers=h).json():
            _ok("custody-event", ce)
    for e in client.get(f"{C}/timeline", headers=h).json()["events"]:
        _ok("timeline-event", e)
    for c in client.get(f"{C}/conflicts", headers=h).json():
        _ok("conflict", c)
    for s in client.get(f"{C}/interviews", headers=h).json():
        _ok("interview", client.get(f"{C}/interviews/{s['recordId']}", headers=h).json())
    _ok("colreg", client.get(f"{C}/colreg", headers=h).json())
    for r in client.get(f"{C}/recommendations", headers=h).json():
        _ok("recommendation", r)
    for r in client.get(f"{C}/consultation/rounds", headers=h).json():
        _ok("consultation-round", r)
    for a in client.get(f"{C}/audit", headers=h).json():
        _ok("audit-event", a)
    for d in client.get(f"{C}/agents/drafts", headers=h).json():
        _ok("agent-draft", d)
    _ok("access-policy", client.get(f"{C}/access-policy", headers=h).json())
    _ok("sim-state#/$defs/state", client.get(f"{C}/sim/state", headers=h).json())
    _ok("sim-state#/$defs/command", client.post(f"{C}/sim/seek", json={"simTimeSec": 435}, headers=h).json())


def _norm(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", path)


def test_openapi_yaml_matches_routes(app):
    spec = yaml.safe_load((PROJECT_ROOT / "contracts" / "openapi.yaml").read_text(encoding="utf-8"))
    declared = {(m.upper(), _norm(p)) for p, item in spec["paths"].items() for m in item if m in ("get", "post", "put", "patch", "delete")}
    actual = {(m.upper(), _norm(p)) for p, item in app.openapi()["paths"].items() for m in item}
    assert declared - actual == set(), f"契约有、服务没有：{sorted(declared - actual)}"
    assert actual - declared == set(), f"服务有、契约没写：{sorted(actual - declared)}"


def test_contract_violation_is_422(client):
    r = client.post(f"{C}/timeline/events", json={"timeSec": 10, "title": "x", "kind": "Bogus"}, headers=H())
    assert r.status_code == 422 and r.json()["code"] == "CONTRACT_VIOLATION"
