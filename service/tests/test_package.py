""".mcase 导出/导入往返、完整性与哈希链校验、与 C# manifest 约定的兼容。"""
import hashlib
import io
import json
import zipfile
import pytest
from fastapi.testclient import TestClient

from mcis_service.common.csjson import ZERO_HASH, sha256_hex

from .conftest import C, CASE, H

LEAD = H("LeadInvestigator", "首席调查官")


@pytest.fixture
def basic_client(tmp_path, monkeypatch):
    """Explicit no-transcript/no-agent synthetic source for supported old import.
    Production seed is not modified; existing full-transcript rejection is tested
    separately. No real public case seed is loaded.
    """
    from mcis_service.main import create_app
    from mcis_service.seed import lily_mary
    from .conftest import make_settings
    app = create_app(make_settings(tmp_path / 'basic', seed=False))
    with monkeypatch.context() as patch:
        patch.setattr(lily_mary, 'seed_interviews', lambda s: None)
        patch.setattr(lily_mary, 'seed_agent_drafts', lambda s: None)
        with app.state.db.session() as session: lily_mary.seed(session, app.state.settings.blob_dir)
    with TestClient(app) as result: yield result


def _zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for k, v in files.items():
            z.writestr(k, v)
    return buf.getvalue()


def _unzip(data: bytes) -> dict[str, bytes]:
    z = zipfile.ZipFile(io.BytesIO(data))
    return {n: z.read(n) for n in z.namelist()}


def _manifest(case_id: str, files: dict[str, bytes]) -> bytes:
    from mcis_service.package.mcase import manifest_json
    return manifest_json(case_id, files, "2026-05-18T06:00:00Z").encode("utf-8")


def test_export_manifest_matches_csharp_convention(client):
    r = client.get(f"{C}/export", headers=LEAD)
    assert r.status_code == 200 and CASE in r.headers["content-disposition"]
    files = _unzip(r.content)
    m = json.loads(files["manifest.json"])
    assert m["packageFormat"] == "MCIS-MCASE" and m["packageVersion"] == "1.0.0" and m["caseId"] == CASE
    assert list(m) == ["packageFormat", "packageVersion", "caseId", "createdAtUtc", "lastModifiedAtUtc", "generatorVersion", "files"]
    listed = {f["relativePath"]: f for f in m["files"]}
    assert "manifest.json" not in listed
    for rel, f in listed.items():
        assert f["sha256"] == hashlib.sha256(files[rel]).hexdigest() and f["sizeBytes"] == len(files[rel])
    roles = {rel: f["role"] for rel, f in listed.items()}
    assert roles["case.json"] == "CaseDefinition" and roles["audit/audit.jsonl"] == "Audit"
    assert roles["raw/vdr/mary_vdr_12h.zip"] == "RawEvidence" and roles["evidence/index.json"] == "RawEvidence"
    assert roles["analysis/timeline.json"] == "Derived"
    case = json.loads(files["case.json"])
    assert list(case)[:3] == ["caseId", "schemaVersion", "title"] and case["caseId"] == CASE
    assert client.get(f"{C}/export", headers=H("ExternalExpert")).status_code == 403
    assert client.get(f"{C}/audit", params={"action": "package.export"}, headers=LEAD).json()


def test_round_trip_into_empty_service(basic_client, empty_client):
    client = basic_client
    data = client.get(f"{C}/export", headers=LEAD).content
    src_audit = _unzip(data)["audit/audit.jsonl"].decode().splitlines()
    v = empty_client.post("/api/v1/packages:verify", content=data, headers=LEAD).json()
    assert v["isValid"] and v["caseId"] == CASE
    r = empty_client.post("/api/v1/cases:import", content=data, headers=LEAD)
    assert r.status_code == 201, r.text
    assert r.json()["imported"]["evidence"] == 6
    for path in ["/evidence", "/timeline", "/conflicts", "/interviews/IR-03", "/recommendations", "/consultation/rounds", "/colreg"]:
        a = client.get(C + path, headers=LEAD).json()
        b = empty_client.get(C + path, headers=LEAD).json()
        assert a == b, path
    dst = empty_client.get(f"{C}/audit", params={"limit": 2000}, headers=LEAD).json()
    assert [e["line"] for e in dst[:len(src_audit)]] == src_audit
    assert dst[-1]["action"] == "package.import"
    assert empty_client.get(f"{C}/audit:verify", headers=LEAD).json()["valid"]
    assert empty_client.get(f"{C}/custody:verify-chain", headers=LEAD).json()["valid"]
    assert empty_client.post(f"{C}/evidence:verify-all", headers=LEAD).json()["mismatched"] == 0
    again = _unzip(empty_client.get(f"{C}/export", headers=LEAD).content)
    # The supported legacy round-trip fixture explicitly contains no testimony.
    assert {k:v for k,v in again.items() if k.startswith('testimony/')} == {k:v for k,v in _unzip(data).items() if k.startswith('testimony/')}
    assert 'testimony/IR-03.json' not in again


def test_duplicate_import_conflict(basic_client):
    client = basic_client
    data = client.get(f"{C}/export", headers=LEAD).content
    r = client.post("/api/v1/cases:import", content=data, headers=LEAD)
    assert r.status_code == 409 and r.json()["code"] == "CASE_EXISTS"


def test_tampered_package_rejected(basic_client, empty_client):
    client = basic_client
    files = _unzip(client.get(f"{C}/export", headers=LEAD).content)
    files["raw/vdr/lily_svdr.zip"] = files["raw/vdr/lily_svdr.zip"] + b"!"
    r = empty_client.post("/api/v1/cases:import", content=_zip(files), headers=LEAD)
    assert r.status_code == 422 and r.json()["code"] == "INTEGRITY_FAILED"
    assert "raw/vdr/lily_svdr.zip" in r.json()["detail"]["tamperedFiles"]
    del files["raw/vdr/lily_svdr.zip"]
    v = empty_client.post("/api/v1/packages:verify", content=_zip(files), headers=LEAD).json()
    assert not v["isValid"] and v["missingFiles"] == ["raw/vdr/lily_svdr.zip"]
    assert empty_client.get("/api/v1/cases").json() == []


def test_extra_file_is_reported_not_fatal(client):
    files = _unzip(client.get(f"{C}/export", headers=LEAD).content)
    files["notes/extra.txt"] = b"hello"
    v = client.post("/api/v1/packages:verify", content=_zip(files), headers=LEAD).json()
    assert v["isValid"] and v["extraFiles"] == ["notes/extra.txt"]


def test_broken_audit_chain_rejected(basic_client, empty_client):
    client = basic_client
    files = _unzip(client.get(f"{C}/export", headers=LEAD).content)
    lines = files["audit/audit.jsonl"].decode().splitlines()
    lines[3] = lines[3].replace('"before":""', '"before":"x"', 1) if '"before":""' in lines[3] else lines[3].replace("调查员", "调査员", 1)
    files["audit/audit.jsonl"] = ("\n".join(lines) + "\n").encode()
    files.pop("manifest.json")
    files["manifest.json"] = _manifest(CASE, files)   # 完整性通过，只剩链断裂
    r = empty_client.post("/api/v1/cases:import", content=_zip(files), headers=LEAD)
    assert r.status_code == 422 and r.json()["code"] == "CHAIN_BROKEN"


def test_minimal_unity_style_package(empty_client):
    """只有 case.json + custody.jsonl + 原始证据的 Unity 侧包也能导入（证据从 Register 行还原）。"""
    from mcis_service.evidence.service import custody_line
    blob = "VDR 原始数据（虚构）".encode()
    sha = sha256_hex(blob)
    item = {"title": "VDR", "source": "驾驶台", "extractedBy": "调查员 Z", "extractedUtc": "2026-01-02T03:04:05Z",
            "relativePath": "raw/vdr.bin", "caseId": "CASE-UNITY-MIN", "confidentiality": "Restricted"}
    l1 = custody_line(seq=1, utc="2026-01-02T04:00:00Z", operator="调查员 Z", kind="Register", evidence_id="EV-001",
                      sha256=sha, previous_sha256="", detail="", matched=None, prev=ZERO_HASH, item=item)
    l2 = custody_line(seq=2, utc="2026-01-02T05:00:00Z", operator="调查员 Z", kind="Verify", evidence_id="EV-001",
                      sha256=sha, previous_sha256=sha, detail="", matched=True, prev=sha256_hex(l1.encode()), item=None)
    case = {"schemaVersion": "1.0.0", "caseId": "CASE-UNITY-MIN", "title": "Unity 最小包（虚构）"}
    files = {"case.json": json.dumps(case, ensure_ascii=False).encode(), "audit/custody.jsonl": (l1 + "\n" + l2 + "\n").encode(),
             "raw/vdr.bin": blob}
    files["manifest.json"] = _manifest("CASE-UNITY-MIN", files)
    r = empty_client.post("/api/v1/cases:import", content=_zip(files), headers=LEAD)
    assert r.status_code == 201, r.text
    ev = empty_client.get("/api/v1/cases/CASE-UNITY-MIN/evidence", headers=LEAD).json()
    assert ev[0]["evidenceId"] == "EV-001" and ev[0]["confidentiality"] == "Restricted" and ev[0]["status"] == "Verified"


def test_multipart_upload(basic_client, empty_client):
    client = basic_client
    data = client.get(f"{C}/export", headers=LEAD).content
    r = empty_client.post("/api/v1/cases:import", files={"file": ("demo.mcase", data, "application/zip")}, headers=LEAD)
    assert r.status_code == 201


def test_legacy_transcript_import_explicitly_rejected_without_mutation(client, empty_client):
    data = client.get(f"{C}/export", headers=LEAD).content
    assert 'testimony/IR-03.json' in _unzip(data)
    before = empty_client.get('/api/v1/cases').json()
    for form in (False, True):
        kwargs = {'files': {'file': ('old.mcase', data, 'application/zip')}} if form else {'content': data}
        result = empty_client.post('/api/v1/cases:import', headers=LEAD, **kwargs)
        assert result.status_code == 422 and result.json()['code'] == 'INTERVIEW_IMPORT_UNSUPPORTED'
        assert empty_client.get('/api/v1/cases').json() == before
