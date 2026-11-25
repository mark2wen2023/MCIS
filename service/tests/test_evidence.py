import base64
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import zipfile

import pytest

from mcis_service.common.csjson import sha256_hex
from mcis_service.config import PROJECT_ROOT

from .conftest import C, H

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



INTEROP_CASE = "SYN-CUSTODY-INTEROP"
INTEROP = f"/api/v1/cases/{INTEROP_CASE}"
REVIEW_REASON = '合成理由，含引号"和反斜杠\\\n另起一行'
REVIEW_IDS = {"EV-002", "EV-005"}
RESTRICTED = ["EV-006"]
DOTNET = Path(os.environ.get("DOTNET_ROOT", Path.home() / ".dotnet")) / "dotnet"


@pytest.fixture
def synthetic_interop_export(empty_client):
    """Create only one supported case; do not reuse the six-module demo."""
    lead = H("LeadInvestigator", "Synthetic Interop")
    case = {
        "caseId": INTEROP_CASE, "title": "Synthetic custody interop",
        "schemaVersion": "1.0.0", "accidentType": "Collision",
        "incidentTimeUtc": "2026-01-01T00:00:00Z", "caseEpochUtc": "2026-01-01T00:00:00Z",
        "incidentLocation": {"latDeg": 0, "lonDeg": 0}, "displayTimeZoneOffsetMinutes": 0,
        "isFictionalDemo": True,
    }
    created = empty_client.post("/api/v1/cases", json=case, headers=lead)
    assert created.status_code == 201, created.text
    for index in range(1, 7):
        evidence_id = f"EV-{index:03d}"
        content = f"Invented custody interop bytes {index}\n".encode("utf-8")
        body = {
            "title": f"Synthetic evidence {index}", "source": "Synthetic offline test",
            "extractedBy": "Synthetic Interop", "extractedUtc": "2026-01-01T00:00:00Z",
            "relativePath": f"evidence/{evidence_id}/original.txt", "category": "Document",
            "confidentiality": "Restricted" if evidence_id in RESTRICTED else "Normal",
            "contentBase64": base64.b64encode(content).decode("ascii"),
        }
        registered = empty_client.post(f"{INTEROP}/evidence", json=body, headers=lead)
        assert registered.status_code == 201, registered.text
        assert registered.json()["evidenceId"] == evidence_id
        assert registered.json()["sha256"] == hashlib.sha256(content).hexdigest()
    for evidence_id in sorted(REVIEW_IDS):
        review = empty_client.patch(
            f"{INTEROP}/evidence/{evidence_id}", json={"needsReview": True, "reason": REVIEW_REASON}, headers=lead,
        )
        assert review.status_code == 200, review.text
        assert review.json()["status"] == "NeedsReview"
    verified = empty_client.post(f"{INTEROP}/evidence/EV-001/verify", headers=lead)
    assert verified.status_code == 200, verified.text
    assert verified.json()["verifyMatched"] is True
    response = empty_client.get(f"{INTEROP}/export", headers=lead)
    # Do not interpret an HTTP error body as a ZIP.
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["cache-control"] == "no-store"
    with zipfile.ZipFile(io.BytesIO(response.content)) as package:
        assert json.loads(package.read("manifest.json"))["packageVersion"] == "1.0.0"
        return package.read("audit/custody.jsonl")


def test_custody_interop_zip_contains_exact_synthetic_ledger(synthetic_interop_export):
    previous = "0" * 64
    assert synthetic_interop_export.endswith(b"\n") and b"\r" not in synthetic_interop_export
    rows = {}
    for seq, line in enumerate(synthetic_interop_export[:-1].split(b"\n"), 1):
        event = json.loads(line)
        assert event["prev"] == previous and event["seq"] == seq
        previous = hashlib.sha256(line).hexdigest()
        rows.setdefault(event["action"], []).append((event,line))
    assert [e["evidence_id"] for e,_ in rows["custody.register"]] == [f"EV-{i:03d}" for i in range(1, 7)]
    assert [e["evidence_id"] for e,_ in rows["custody.register"] if e.get("confidentiality") == "Restricted"] == RESTRICTED
    assert {e["evidence_id"] for e,_ in rows["custody.review"]} == REVIEW_IDS
    assert len(rows["custody.review"]) == 2
    for event,line in rows["custody.review"]:
        assert event["detail"] == REVIEW_REASON and event["result"] == "needs_review"
        assert b'\\"' in line and b'\\\\' in line and b'\\n' in line
    assert [e["evidence_id"] for e,_ in rows["custody.verify"]] == ["EV-001"]


def test_custody_interop_demo_refuses_partial_export(empty_client):
    from mcis_service.seed.lily_mary import seed as seed_fictional_only

    app = empty_client.app
    with app.state.db.session() as session:
        assert seed_fictional_only(session, app.state.settings.blob_dir)
    response = empty_client.get(f"{C}/export", headers=H("LeadInvestigator"))
    assert response.status_code == 409
    assert response.json()["code"] == "ARCHIVE_RESTORE_UNSUPPORTED"
    assert response.headers["cache-control"] == "no-store"
    assert "content-disposition" not in response.headers


@pytest.mark.skipif(not DOTNET.is_file() or not COMPAT.is_file(), reason="需要现有 .NET 8 和 mcis-compat")
def test_custody_jsonl_accepted_by_csharp_ledger(synthetic_interop_export, tmp_path):
    """Default C# ledger verifies the real exported UTF-8 lines, without normalization."""
    evidence_file = tmp_path / "custody.jsonl"
    evidence_file.write_bytes(synthetic_interop_export)
    out = subprocess.run([str(COMPAT), "custody", str(evidence_file)], capture_output=True, text=True, timeout=300)
    assert out.returncode == 0, (out.stdout, out.stderr)
    res = json.loads(out.stdout.strip().splitlines()[-1])
    assert res["ok"] and res["items"] == 6 and res["events"] == 9
    assert {ident for ident, status in res["status"].items() if status == "NeedsReview"} == REVIEW_IDS
    assert res["status"]["EV-001"] == "Verified"
    assert res["restricted"] == RESTRICTED
