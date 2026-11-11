"""W16 模板、GISIS 与导出：先证明缺实现，再验证中文可提取与双语完整性。"""
from __future__ import annotations

import copy
import io
import json
import subprocess

import pytest
from docx import Document

from mcis_service.reports.exporter import export_report
from mcis_service.reports.gisis import build_gisis, serialize_gisis, validate_gisis
from mcis_service.reports.templates import GLOSSARY, TEMPLATES


def _report():
    sentence = {"sentenceId": "analysis-1", "status": "Draft", "textZh": "缺数据：W14 推演对比表未提供。",
                "textEn": "Missing data: W14 what-if comparison table was not provided.", "missing": True,
                "citations": [{"kind": "evidence", "id": "EV-001", "href": "#/evidence?id=EV-001", "registration": "registered"},
                              {"kind": "evidence", "id": "EV-999", "href": "#/evidence?id=EV-999", "registration": "unregistered"}]}
    section = {"sectionId": "analysis", "titleZh": "原因分析与教训", "titleEn": "Analysis and lessons",
               "status": "Draft", "missing": True, "textZh": sentence["textZh"], "textEn": sentence["textEn"], "sentences": [sentence]}
    return {"reportId": "RPT-001", "caseId": "CASE-2026-DEMO-LILY-MARY", "version": 1, "templateId": "imo-cic",
            "lang": "bilingual", "status": "Draft", "isFictionalDemo": True, "sections": [section],
            "disclaimerZh": "不作责任认定", "disclaimerEn": "This report does not apportion blame or liability"}


def test_templates_have_three_distinct_formats_and_bilingual_sources():
    assert {t["templateId"] for t in TEMPLATES} == {"imo-cic", "maib", "cn-msa"}
    for template in TEMPLATES:
        assert len(template["sections"]) == 7
        assert len({s["sectionId"] for s in template["sections"]}) == 7
        assert all(s["titleZh"] and s["titleEn"] and s["dataSources"] for s in template["sections"])
    chinese = next(t for t in TEMPLATES if t["templateId"] == "cn-msa")
    assert "责任" not in " ".join(s["titleZh"] for s in chinese["sections"])
    assert any(term["termEn"] == "Midships" and term["termZh"] == "正舵" for term in GLOSSARY)


@pytest.mark.parametrize("lang", ["zh", "en", "bilingual"])
def test_pdf_text_is_extractable_and_contains_status_citations_and_disclaimer(tmp_path, lang):
    data = export_report(_report(), format="pdf", lang=lang)
    assert data.startswith(b"%PDF")
    path = tmp_path / "report.pdf"
    path.write_bytes(data)
    text = subprocess.run(["pdftotext", "-layout", str(path), "-"], check=True, capture_output=True).stdout.decode()
    assert "DRAFT" in text and "不作责任认定" in text
    assert "This report does not apportion blame or liability" in text
    assert "Fictional" in text and "Draft" in text
    assert "[EV-001]" in text and "EV-999" in text
    if lang in ("zh", "bilingual"):
        assert "缺数据" in text and "W14" in text
    if lang in ("en", "bilingual"):
        assert "Missing data" in text


@pytest.mark.parametrize("lang", ["zh", "en", "bilingual"])
def test_docx_readback_has_document_and_page_state(lang):
    doc = Document(io.BytesIO(export_report(_report(), format="docx", lang=lang)))
    text = "\n".join(p.text for p in doc.paragraphs)
    text += "\n".join(cell.text for table in doc.tables for row in table.rows for cell in row.cells)
    assert "不作责任认定" in text and "This report does not apportion blame or liability" in text
    assert "DRAFT" in text and "Fictional" in text and "[EV-001]" in text
    assert "DRAFT" in doc.sections[0].header.paragraphs[0].text
    assert "不作责任认定" in doc.sections[0].footer.paragraphs[0].text
    if lang in ("zh", "bilingual"):
        assert "缺数据" in text
    if lang in ("en", "bilingual"):
        assert "Missing data" in text


def test_export_does_not_mutate_input_and_repeats_state_on_long_pdf(tmp_path):
    report = _report()
    report["sections"][0]["sentences"] *= 100
    before = copy.deepcopy(report)
    data = export_report(report, format="pdf", lang="bilingual")
    assert before == report
    path = tmp_path / "long.pdf"
    path.write_bytes(data)
    text = subprocess.run(["pdftotext", str(path), "-"], check=True, capture_output=True).stdout.decode()
    pages = [p for p in text.split("\f") if p.strip()]
    assert len(pages) > 2
    assert all("DRAFT" in p and "不作责任认定" in p for p in pages)


def test_gisis_does_not_invent_missing_values_or_tonnage():
    case = {"caseId": "CASE-2026-DEMO-LILY-MARY", "isFictionalDemo": True, "accidentGrade": "VerySerious",
            "incidentTimeUtc": "2026-05-18T06:24:00Z", "incidentLocation": {"latDeg": 21.7, "lonDeg": 113.7}, "accidentType": "Collision"}
    vessels = [{"vesselId": "lily", "name": "Lily", "imoNumber": "IMO 9074729", "displacementTons": 24500}]
    doc = build_gisis(case, vessels)
    fields = {f["id"]: f for f in doc["fields"]}
    assert fields["vessels.lily.grossTonnage"]["value"] is None
    assert fields["vessels.lily.grossTonnage"]["missing"] is True
    assert fields["deaths"]["value"] is None and fields["deaths"]["missingLabel"] == "缺数据 / Missing data"
    assert fields["severity"]["value"] == "Very serious marine casualty"
    assert fields["vessels.lily.imoNumber"]["value"] == "9074729"
    assert all(f["sourceRefs"] and f["rules"] and f["labelZh"] and f["labelEn"] for f in doc["fields"])
    assert doc["isFictionalDemo"] is True


def test_gisis_validation_rules_and_temporary_overrides():
    doc = build_gisis({"caseId": "CASE-2026-DEMO-LILY-MARY", "isFictionalDemo": True}, [{"vesselId": "lily"}])
    original = copy.deepcopy(doc)
    validation = validate_gisis(doc, {"latitude": 91, "longitude": "invalid", "deaths": -1,
                                      "incidentTimeUtc": "2026-05-18T06:24:00+08:00", "unknown": 1,
                                      "vessels.lily.imoNumber": "1234568", "severity": "ungraded"})
    assert validation["valid"] is False
    errors = {e["fieldId"]: e["code"] for e in validation["errors"]}
    for field in ("latitude", "longitude", "deaths", "incidentTimeUtc", "unknown", "vessels.lily.imoNumber", "severity"):
        assert field in errors
    assert doc == original
    fields = {f["id"]: f for f in validation["fields"]}
    assert fields["latitude"]["value"] == 91
    assert fields["latitude"]["missing"] is False
    assert fields["latitude"]["sourceRefs"] == [
        "request.values.latitude (Investigator temporary input; original sources: case.incidentLocation.latDeg)"]
    assert "request.values.vessels.lily.imoNumber" in fields["vessels.lily.imoNumber"]["sourceRefs"][0]
    assert "vessels.lily.imoNumber" in fields["vessels.lily.imoNumber"]["sourceRefs"][0]
    assert next(f for f in doc["fields"] if f["id"] == "latitude")["sourceRefs"] == ["case.incidentLocation.latDeg"]


def test_gisis_json_csv_preserve_null_missing_and_provenance():
    doc = build_gisis({"caseId": "CASE-2026-DEMO-LILY-MARY", "isFictionalDemo": True}, [])
    raw = serialize_gisis(doc, "json")
    parsed = json.loads(raw)
    assert parsed == doc
    csv = serialize_gisis(doc, "csv").decode("utf-8-sig")
    assert "null" in csv and "missing" in csv and "sourceRefs" in csv
    assert "不作责任认定" in doc["notice"]


def test_gisis_valid_complete_projection_preserves_zero_and_false():
    case = {"caseId": "CASE-2026-DEMO-LILY-MARY", "isFictionalDemo": True,
            "incidentTimeUtc": "2026-05-18T06:24:00Z", "incidentLocation": {"latDeg": 0, "lonDeg": 0, "locationCategory": "Unknown"},
            "accidentGrade": "VerySerious", "accidentType": "Collision", "deaths": 0, "missingPersons": 0,
            "injuries": 0, "pollution": False, "shipLoss": False, "investigatingState": "示例调查国（虚构）", "reportStatus": "Draft"}
    vessel = {"vesselId": "lily", "name": "Lily", "imoNumber": "9074729", "flagState": "虚构船旗国",
              "vesselTypeCode": "BulkCarrier", "grossTonnage": 10000}
    doc = build_gisis(case, [vessel])
    result = validate_gisis(doc, {})
    assert result["valid"] is True and result["errors"] == []
    fields = {field["id"]: field for field in result["fields"]}
    assert fields["deaths"]["value"] == 0 and not fields["deaths"]["missing"]
    assert fields["pollution"]["value"] is False and not fields["pollution"]["missing"]


def test_confirmed_export_does_not_label_itself_draft(tmp_path):
    report = _report()
    report["status"] = "Confirmed"
    report["sections"][0]["status"] = "Confirmed"
    report["sections"][0]["sentences"][0]["status"] = "Confirmed"
    data = export_report(report, format="pdf", lang="zh", include_glossary=False)
    path = tmp_path / "confirmed.pdf"
    path.write_bytes(data)
    text = subprocess.run(["pdftotext", str(path), "-"], check=True, capture_output=True).stdout.decode()
    assert "CONFIRMED" in text and "DRAFT" not in text
    document = Document(io.BytesIO(export_report(report, format="docx", lang="zh", include_glossary=False)))
    assert "CONFIRMED" in document.sections[0].header.paragraphs[0].text
    assert "DRAFT" not in document.sections[0].header.paragraphs[0].text
