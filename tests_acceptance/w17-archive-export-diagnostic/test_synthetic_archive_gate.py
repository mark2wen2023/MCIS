"""Exact archive-gate replay using only synthetic cases and real HTTP handlers."""
import base64
import hashlib
import io
import json
import zipfile

from tests.test_working_record_archive import HEAD, CID, ROOT, checked, client_at, imported, snapshot

SYNTHETIC_BYTES = b"W17 completed synthetic evidence archive fixture\n"
CLOSED = {
    "code": "ARCHIVE_RESTORE_UNSUPPORTED",
    "message": "此案未通过完整恢复预检，未生成部分案件包",
}


def register(c):
    body = {
        "profile":"mcis-evidence-intake-v1",
        "fileName":"synthetic-source.txt",
        "contentBase64":base64.b64encode(SYNTHETIC_BYTES).decode(),
        "title":"Synthetic archive control",
        "source":"Synthetic",
        "extractedBy":"Synthetic",
        "extractedUtc":"2026-01-01T00:00:00Z",
        "category":"Document",
        "confidentiality":"Restricted",
        "note":"",
    }
    preview = checked(c,"post",ROOT+"/evidence-intakes:preview",body).json()
    return checked(c,"post",ROOT+"/evidence-intakes:commit",{
        **body,"confirmed":True,"requestDigest":preview["requestDigest"],
    }).json()


def files(c):
    root = c.app.state.settings.blob_dir
    return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_single_registered_source_roundtrips(tmp_path):
    with client_at(tmp_path/"source",True) as source:
        receipt = register(source)
        before = files(source)
        exported = checked(source,"get",ROOT+"/export")
        assert exported.headers["cache-control"] == "no-store"
        assert exported.headers["content-type"] == "application/zip"
        assert files(source) == before
        with zipfile.ZipFile(io.BytesIO(exported.content)) as z:
            manifest = json.loads(z.read("manifest.json"))
            assert manifest["packageVersion"] == "1.2.0"
            working = json.loads(z.read("working-records/backup.v1.json"))
            evidence = [item for item in working["importHistory"] if item["kind"]=="evidence-intake"]
            assert len(evidence) == 1 and evidence[0]["key"] == receipt["requestDigest"]
            assert z.read(evidence[0]["metadata"]["relativePath"]) == SYNTHETIC_BYTES
            assert working["interviews"] == working["reports"] == []
        with client_at(tmp_path/"destination") as destination:
            imported(destination,exported.content)
            archived = checked(destination,"get",ROOT+"/archive-history/evidence/"+receipt["evidenceId"]+"/content")
            assert archived.content == SYNTHETIC_BYTES
            assert archived.headers["x-sha256"] == hashlib.sha256(SYNTHETIC_BYTES).hexdigest()
            checked(destination,"get",ROOT+"/evidence-intakes/"+receipt["requestDigest"],status=409)


def test_untracked_file_reproduces_wrapped_409_without_mutation(tmp_path):
    with client_at(tmp_path/"source",True) as source:
        receipt = register(source)
        root = source.app.state.settings.blob_dir/CID
        (root/"synthetic-unknown.txt").write_bytes(b"Synthetic untracked file; must not vanish\x00")
        before_rows, before_files = snapshot(source), files(source)
        response = checked(source,"get",ROOT+"/export",status=409)
        assert response.json() == CLOSED
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["content-type"].startswith("application/json")
        assert "content-disposition" not in response.headers
        assert snapshot(source) == before_rows and files(source) == before_files
        denied = source.get(ROOT+"/export",headers={"X-MCIS-Role":"Public"})
        assert denied.status_code == 403 and denied.json()["code"] == "FORBIDDEN"
        assert CLOSED["code"] not in denied.text and "synthetic-unknown" not in denied.text
        assert snapshot(source) == before_rows and files(source) == before_files
