"""Ordinary synthetic regression for the two existing archive consumers."""
import base64
import json

from mcis_service.package.mcase import read_zip
from .test_bounded_timeline_archive_increment import populate
from .test_track_history import B as TRACK, client as track_client, request, setup
from .test_working_record_archive import HEAD, ROOT, checked, client_at, snapshot


def members(c):
    response = checked(c, "get", ROOT + "/export")
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-type"] == "application/zip"
    return response.content, read_zip(response.content)


def strict_preview(c, archive, status=200):
    return checked(
        c, "post", "/api/v1/packages/intakes:preview",
        {"contentBase64": base64.b64encode(archive).decode("ascii")}, status,
    )


def test_bare_event_preserves_legacy_restore_not_strict_intake(tmp_path):
    with client_at(tmp_path / "source", True) as source:
        event = checked(source, "post", ROOT + "/timeline/events", {
            "eventId": "TE-01", "timeSec": 2.25, "kind": "Event", "title": "Synthetic bare event",
            "confirmed": False,
        }, 201).json()
        archive, files = members(source)
        assert json.loads(files["manifest.json"])["packageVersion"] == "1.0.0"
        assert json.loads(files["analysis/timeline.json"]) == {"events": [event]}
        assert "timeline/records.v1.json" not in files
    with client_at(tmp_path / "strict") as strict:
        before = snapshot(strict)
        rejected = strict_preview(strict, archive, 422)
        assert rejected.json()["code"] == "PACKAGE_INTAKE_INVALID"
        assert snapshot(strict) == before
    with client_at(tmp_path / "legacy") as legacy:
        imported = legacy.post(
            "/api/v1/cases:import", headers=HEAD,
            files={"file": ("synthetic.mcase", archive)},
        )
        assert imported.status_code == 201, imported.text
        assert checked(legacy, "get", ROOT + "/timeline").json()["events"] == [event]


def test_empty_timeline_remains_strictly_readable_legacy_archive(tmp_path):
    with client_at(tmp_path / "source", True) as source:
        archive, files = members(source)
        assert json.loads(files["manifest.json"])["packageVersion"] == "1.0.0"
        assert json.loads(files["analysis/timeline.json"]) == {"events": []}
        assert "timeline/records.v1.json" not in files
    with client_at(tmp_path / "strict") as strict:
        before = snapshot(strict)
        assert strict_preview(strict, archive).json()["packageVersion"] == "1.0.0"
        assert snapshot(strict) == before


def test_conflicts_remain_fail_closed_when_events_working_archive_selected(tmp_path):
    with client_at(tmp_path / "source", True) as c:
        populate(c)
        checked(c, "post", ROOT + "/conflicts", {
            "conflictId": "C-01", "summary": "Synthetic conflict",
            "a": {"sourceLabel": "Invented A", "valueText": "known"},
            "b": {"sourceLabel": "Invented B", "valueText": "unknown"},
            "status": "Open",
        }, 201)
        before = snapshot(c)
        rejected = checked(c, "get", ROOT + "/export", status=409)
        assert rejected.json()["code"] == "ARCHIVE_RESTORE_UNSUPPORTED"
        assert "content-disposition" not in rejected.headers
        assert snapshot(c) == before


def test_w10_alone_remains_readable_and_w10_timeline_combination_fails_closed(tmp_path):
    with track_client(tmp_path / "source") as c:
        receipt = request(c, "post", TRACK + "/track-imports:commit", setup(c)).json()
        pure_track_archive = request(c, "get", TRACK + "/export").content
        assert json.loads(read_zip(pure_track_archive)["manifest.json"])["packageVersion"] == "1.3.0"
        with track_client(tmp_path / "verify") as target:
            assert strict_preview(target, pure_track_archive).json()["workingRecordsExtension"]["trackReceiptCount"] == 1
        request(c, "post", TRACK + "/timeline/events", {
            "timeSec": 0.005, "kind": "Observation", "title": "Synthetic mixed timeline",
            "evidenceIds": [receipt["sourceEvidenceId"]],
        }, status=201)
        before = snapshot(c)
        root = c.app.state.settings.blob_dir
        original = {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}
        rejected = request(c, "get", TRACK + "/export", status=409)
        assert rejected.json()["code"] == "ARCHIVE_RESTORE_UNSUPPORTED"
        assert "content-disposition" not in rejected.headers
        assert snapshot(c) == before
        assert {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()} == original
