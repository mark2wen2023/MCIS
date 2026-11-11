import base64
import hashlib
import io
import json
import subprocess
import zipfile

import pytest

from mcis_service.common.csjson import sha256_hex
from mcis_service.config import PROJECT_ROOT

from .conftest import C, H, HAS_DOTNET

COMPAT = PROJECT_ROOT / "tools" / "mcis-compat" / "mcis-compat.sh"


def test_evidence_list_flags(client):
    ev = client.get(f"{C}/evidence", headers=H()).json()
    assert [e["evidenceId"] for e in ev] == [f"EV-00{i}" for i in range(1, 7)]
    by = {e["evidenceId"]: e for e in ev}
    assert all(e["caseId"] == "CASE-2026-DEMO-LILY-MARY" for e in ev)
    assert by["EV-005"]["needsReview"] and by["EV-005"]["status"] == "NeedsReview"
    assert by["EV-006"]["confidentiality"] == "Restricted"
    assert by["EV-001"]["status"] == "Verified"


def test_restricted_hidden_from_public_and_external(client):
    ids = lambda role: {e["evidenceId"] for e in client.get(f"{C}/evidence", headers=H(role)).json()}
    assert "EV-006" in ids("LeadInvestigator")
    assert "EV-006" not in ids("ExternalExpert")
    assert client.get(f"{C}/evidence/EV-006", headers=H("ExternalExpert")).status_code == 403
    assert "EV-006" not in ids("AgentService")
    assert client.get(f"{C}/evidence", headers=H("Public")).status_code == 403


def test_register_access_verify_custody_chain(client):
    content = "第 3# 浮标观测记录（虚构）\n".encode()
    body = {"title": "浮标观测记录", "source": "航标处（虚构）", "extractedBy": "调查员 D",
            "extractedUtc": "2026-05-23T02:00:00Z", "relativePath": "evidence/EV-007/buoy.txt", "category": "Document",
            "contentBase64": base64.b64encode(content).decode()}
    r = client.post(f"{C}/evidence", json=body, headers=H(operator="调查员 D"))
    assert r.status_code == 201, r.text
    assert r.json()["evidenceId"] == "EV-007"
    assert r.json()["sha256"] == hashlib.sha256(content).hexdigest() and r.json()["status"] == "Unverified"
    assert client.post(f"{C}/evidence", json={**body, "confidentiality": "Secret"}, headers=H()).status_code == 422
    assert client.post(f"{C}/evidence", json=body, headers=H("ExternalExpert")).status_code == 403

    assert client.post(f"{C}/evidence/EV-007/access", json={"purpose": "比对"}, headers=H(operator="调查员 D")).status_code == 201
    v = client.post(f"{C}/evidence/EV-007/verify", headers=H()).json()
    assert v["verifyMatched"] is True and v["kind"] == "Verify"
    assert client.get(f"{C}/evidence/EV-007", headers=H()).json()["status"] == "Verified"
    assert client.get(f"{C}/evidence/EV-007/content", headers=H()).content == content

    chain = client.get(f"{C}/evidence/EV-007/custody", headers=H()).json()
    assert [e["kind"] for e in chain] == ["Register", "Access", "Verify", "Access"]
    reg = json.loads(chain[0]["line"])
    # 与 C# CustodyEvent.ToJsonLine 一致的键顺序
    assert list(reg) == ["utc", "operator", "action", "category", "command", "before", "after", "seq", "evidence_id", "sha256",
                         "detail", "title", "source", "extracted_by", "extracted_utc", "path", "case_id", "prev"]
    assert reg["command"] == "登记证据 EV-007" and reg["category"] == "Custody" and "\\u" not in chain[0]["line"]
    acc = json.loads(chain[1]["line"])
    assert acc["after"] == "比对" and acc["before"] == ""
    assert acc["prev"] == sha256_hex(chain[0]["line"].encode())  # 案件内仅此证据在新增，前一行即登记行
    assert client.get(f"{C}/custody:verify-chain", headers=H()).json()["valid"]
    # 访问写了 audit
    a = client.get(f"{C}/audit", params={"entityId": "EV-007"}, headers=H()).json()
    assert [x["action"] for x in a] == ["custody.register", "custody.access", "custody.verify", "custody.access"]


def test_needs_review_via_review_event(client):
    assert client.patch(f"{C}/evidence/EV-001", json={"needsReview": True}, headers=H()).status_code == 422  # 缺理由
    r = client.patch(f"{C}/evidence/EV-001", json={"needsReview": True, "reason": "时间戳与 VDR 不符"}, headers=H())
    assert r.status_code == 200 and r.json()["status"] == "NeedsReview"
    assert client.patch(f"{C}/evidence/EV-001", json={"needsReview": True, "reason": "x"}, headers=H()).status_code == 409
    last = client.get(f"{C}/evidence/EV-001/custody", headers=H()).json()[-1]
    line = json.loads(last["line"])
    assert line["action"] == "custody.review" and line["result"] == "needs_review" and line["after"] == "NeedsReview"
    assert line["command"] == "标注需复核 EV-001"
    r = client.patch(f"{C}/evidence/EV-001", json={"needsReview": False, "reason": "已核实"}, headers=H()).json()
    assert r["needsReview"] is False and r["status"] == "Verified"
    assert client.patch(f"{C}/evidence/EV-001", json={"needsReview": True, "reason": "x"}, headers=H("ExternalExpert")).status_code == 403


def test_tampered_blob_detected(client, app):
    st = app.state.settings
    f = st.data_dir / "blobs" / "CASE-2026-DEMO-LILY-MARY" / "raw" / "vdr" / "lily_svdr.zip"
    f.write_bytes(f.read_bytes() + b"x")
    r = client.post(f"{C}/evidence:verify-all", headers=H()).json()
    res = {x["evidenceId"]: x["matched"] for x in r["results"]}
    assert res["EV-002"] is False and res["EV-001"] is True and r["mismatched"] == 1
    assert client.get(f"{C}/evidence/EV-002", headers=H()).json()["status"] == "Mismatch"


@pytest.mark.skipif(not HAS_DOTNET or not COMPAT.exists(), reason="需要 ~/.dotnet")
def test_custody_jsonl_accepted_by_csharp_ledger(client, tmp_path):
    """用 Unity 侧原样 C#（CustodyLedger.Load）校验导出的 custody.jsonl：链完整 + 每行与 ToJsonLine 逐字节一致。"""
    client.patch(f"{C}/evidence/EV-002", json={"needsReview": True, "reason": "含引号\"与换行\n的理由"}, headers=H())
    z = zipfile.ZipFile(io.BytesIO(client.get(f"{C}/export", headers=H("LeadInvestigator")).content))
    p = tmp_path / "custody.jsonl"
    p.write_bytes(z.read("audit/custody.jsonl"))
    out = subprocess.run([str(COMPAT), "custody", str(p)], capture_output=True, text=True, timeout=300)
    res = json.loads(out.stdout.strip().splitlines()[-1])
    assert res["ok"], res
    assert res["items"] == 6 and res["status"]["EV-002"] == "NeedsReview" and res["status"]["EV-005"] == "NeedsReview"
    assert res["restricted"] == ["EV-006"]
