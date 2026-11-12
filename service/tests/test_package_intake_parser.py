import hashlib
import io
import json
import zipfile

import pytest
from fastapi import HTTPException
from mcis_service.package.mcase import manifest_json
from mcis_service.package_intake import parser as p
from mcis_service.redaction.policy import default_policy


def base():
    case = dict(caseId="CASE-INTAKE", schemaVersion="1.0.0", title="测试", accidentCode="", accidentType="Collision",
                accidentGrade="", incidentTimeUtc="2026-01-01T00:00:00Z", caseEpochUtc="2026-01-01T00:00:00Z",
                displayTimeZoneOffsetMinutes=480, incidentLocation=dict(lonDeg=120, latDeg=30, heightM=0),
                seaLevelOffsetM=0, leadInvestigator="", agencyName="", isFictionalDemo=True, summaryNotes="")
    return {"case.json": json.dumps(case).encode(), "case.ext.json": b"{}", "vessels.json": b"[]",
            "evidence/index.json": b"[]", "audit/audit.jsonl": b"", "audit/custody.jsonl": b"",
            "access-policy.json": json.dumps(default_policy()).encode()}


def pack(files, manifest=None):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for path, blob in files.items():
            z.writestr(path, blob)
        z.writestr("manifest.json", manifest or manifest_json("CASE-INTAKE", files, "2026-01-01T00:00:00Z"))
    return out.getvalue()


def test_minimal_retains_original_bytes():
    files = base()
    result = p.parse_package(pack(files))
    assert all(result.files[k] == v for k, v in files.items())
    assert result.summary["caseId"] == "CASE-INTAKE"
    assert result.tracks == {} and result.audit_lines == []


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'NaN', b'1e999', b'"\\ud800"', b'[' * 70 + b'0' + b']' * 70])
def test_strict_json(raw):
    with pytest.raises(HTTPException):
        p.strict_json(raw)


@pytest.mark.parametrize("path,blob", [("unrecognized.json", b"{}"), ("analysis/timeline.json", b'{"events":[{}]}'),
    ("analysis/timeline.json", b'{"events":[],"extra":1}'), ("exports/report.pdf", b"pdf"), ("raw/.keep", b"not empty")])
def test_unsupported_not_discarded(path, blob):
    f = base(); f[path] = blob
    with pytest.raises(HTTPException): p.parse_package(pack(f))


@pytest.mark.parametrize("path", ["../a", "/a", "raw\\a", "a/../b", "a:b", "a\x00b", "a./b"])
def test_unsafe_names(path):
    with pytest.raises(HTTPException): p.safe_path(path)


def test_duplicate_and_ancestor_paths():
    for names in [("a", "A"), ("a", "a/b"), ("a/", "A/")]:
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w") as z:
            for name in names: z.writestr(name, b"")
        with pytest.raises(HTTPException): p.read_bounded(out.getvalue())


@pytest.mark.parametrize("limit", ["MAX_COMPRESSED", "MAX_MEMBER", "MAX_EXPANDED", "MAX_MEMBERS"])
def test_resource_limits(monkeypatch, limit):
    monkeypatch.setattr(p, limit, 1)
    with pytest.raises(HTTPException): p.parse_package(pack(base()))


def test_missing_case_fields_not_defaulted():
    f = base(); f["case.json"] = b'{"caseId":"CASE-INTAKE"}'
    with pytest.raises(HTTPException): p.parse_package(pack(f))


def test_manifest_size_and_extra_members():
    f = base(); m = json.loads(manifest_json("CASE-INTAKE", f, "2026-01-01T00:00:00Z"))
    m["files"][0]["sizeBytes"] += 1
    with pytest.raises(HTTPException): p.parse_package(pack(f, json.dumps(m)))
    m["files"] = m["files"][1:]
    with pytest.raises(HTTPException): p.parse_package(pack(f, json.dumps(m)))


def test_policy_escalation_rejected():
    f = base(); f["access-policy.json"] = b'{}'
    with pytest.raises(HTTPException): p.parse_package(pack(f))


def test_audit_lines_preserved_and_chain_checked():
    f = base()
    rec = dict(seq=1, prev="0" * 64, utc="2026-01-01T00:00:00Z", operator="test", action="case.create",
               category="Case", command="create", before="", after="")
    line = json.dumps(rec, ensure_ascii=False)
    f["audit/audit.jsonl"] = (line + "\n").encode()
    assert p.parse_package(pack(f)).audit_lines == [line]
    rec["prev"] = "1" * 64
    f["audit/audit.jsonl"] = json.dumps(rec).encode()
    with pytest.raises(HTTPException): p.parse_package(pack(f))


def test_unknown_track_vessel_rejected():
    f = base(); f["derived/tracks/ghost.track.json"] = b'{"vesselId":"ghost","points":[]}'
    with pytest.raises(HTTPException): p.parse_package(pack(f))


def test_crc_corruption():
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z: z.writestr("payload", b"UNIQUE-PAYLOAD")
    raw = out.getvalue().replace(b"UNIQUE-PAYLOAD", b"CORRUPT-BYTES!")
    with pytest.raises(HTTPException): p.read_bounded(raw)


def with_evidence():
    from mcis_service.evidence.service import custody_line
    f = base(); blob = b"original public source"
    ev = dict(evidenceId="EV-001", caseId="CASE-INTAKE", title="source", source="public", extractedBy="test",
              extractedUtc="2026-01-01T00:00:00Z", sha256=hashlib.sha256(blob).hexdigest(),
              relativePath="raw/source.txt", confidentiality="Normal", category="Document", note="")
    line = custody_line(seq=1, utc="2026-01-01T00:00:00Z", operator="test", kind="Register", evidence_id="EV-001",
                        sha256=ev["sha256"], previous_sha256="", detail="", matched=None, prev="0"*64, item=ev)
    f["raw/source.txt"] = blob
    f["evidence/index.json"] = json.dumps([ev]).encode()
    f["audit/custody.jsonl"] = (line + "\n").encode()
    return f


def valid_package():
    """Reusable valid basic package for route integration tests."""
    return pack(with_evidence())


def test_evidence_and_custody_preserved():
    f = with_evidence(); parsed = p.parse_package(pack(f))
    assert parsed.summary["evidence"] == 1
    assert parsed.custody_lines[0].encode() + b"\n" == f["audit/custody.jsonl"]


@pytest.mark.parametrize("mutation", ["missing", "hash", "no_chain", "case", "reference", "registration"])
def test_evidence_integrity(mutation):
    f = with_evidence()
    if mutation == "missing": del f["raw/source.txt"]
    elif mutation == "hash": f["raw/source.txt"] = b"changed"
    elif mutation == "no_chain": f["audit/custody.jsonl"] = b""
    elif mutation == "case": f["evidence/index.json"] = f["evidence/index.json"].replace(b"CASE-INTAKE", b"CASE-OTHER")
    elif mutation == "reference": f["audit/custody.jsonl"] = f["audit/custody.jsonl"].replace(b"EV-001", b"EV-999")
    else: f["audit/custody.jsonl"] = f["audit/custody.jsonl"].replace(b'"source":"public"', b'"source":"forged"')
    with pytest.raises(HTTPException): p.parse_package(pack(f))


def test_invalid_track_identifier_type():
    f = base(); f["derived/tracks/a.track.json"] = b'{"vesselId":[],"points":[]}'
    with pytest.raises(HTTPException): p.parse_package(pack(f))


def test_zip_encryption_flag():
    import struct
    raw = bytearray(pack(base()))
    for marker, offset in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):
        loc = raw.index(marker) + offset
        struct.pack_into("<H", raw, loc, struct.unpack_from("<H", raw, loc)[0] | 1)
    with pytest.raises(HTTPException): p.read_bounded(bytes(raw))


def test_unknown_keep_rejected():
    f = base(); f['arbitrary/.keep'] = b''
    with pytest.raises(HTTPException): p.parse_package(pack(f))


@pytest.mark.parametrize('cid', ['CASE.BAD', 'A' * 65])
def test_case_identifier_matches_intake_route(cid):
    f = base(); case = json.loads(f['case.json']); case['caseId'] = cid; f['case.json'] = json.dumps(case).encode()
    m = manifest_json(cid, f, '2026-01-01T00:00:00Z')
    with pytest.raises(HTTPException): p.parse_package(pack(f, m))
