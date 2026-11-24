"""用同一报告快照生成 PDF/DOCX：中文、双语、状态及来源均不依赖 LLM。"""
from __future__ import annotations

import io
from functools import lru_cache
from html import escape

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..config import PROJECT_ROOT
from .templates import DISCLAIMER_EN, DISCLAIMER_ZH, GLOSSARY, TEMPLATES

_INHERITED_ZH = "引用沿用原生成内容，仅用于追溯；不自动证明修改文字，也不表示修改文字仍是原文。请人工核对支持关系。"
_INHERITED_EN = "References are inherited from the generated text for traceability only; they do not automatically support the edited wording or identify it as an original quotation. Review the support manually."
_FONT = "MCIS-NotoSansSC-W16"
_STATUS_ZH = {"Draft": "草稿", "Confirmed": "已确认", "Modified": "已修改", "Dismissed": "已驳回"}


@lru_cache(maxsize=1)
def _font():
    """固定使用项目字体，使中文内容及 ToUnicode 提取可靠。"""
    pdfmetrics.registerFont(TTFont(_FONT, str(PROJECT_ROOT / "fonts" / "NotoSansSC-Regular.ttf")))
    return _FONT


def _draft(report):
    # “已修改”仍须最终确认；即使report.status被客户端误读，也以章节状态为准。
    return not report.get("sections") or any(section.get("status") != "Confirmed" for section in report["sections"])


def _state(report):
    return "DRAFT 草稿" if _draft(report) else "CONFIRMED 已确认"


def _visible_state(report):
    return _state(report) if _draft(report) else "CONFIRMED 已确认（章节 / sections）"


def _review_notice(report):
    return "" if _draft(report) else (
        "章节均已确认，不代表正式签发／归档 / "
        "All sections confirmed; not formal issuance or archiving.")


def _fiction(report):
    if report.get("isFictionalDemo") is True:
        return "虚构示例 / Fictional"
    if report.get("realDataStatus") == "authorized-public":
        return "公开报告资料 / Public report data"
    return "真实数据待确认 / Real data pending confirmation"


def _title(report):
    template = next((item for item in TEMPLATES if item["templateId"] == report.get("templateId")), None)
    return f"{template['titleZh']} / {template['titleEn']}" if template else "调查报告 / Safety investigation report"


def _status(value):
    return f"{value} / {_STATUS_ZH.get(value, value)}"


def _reference_label(citation):
    label = f"[{citation['id']}]"
    registration = citation.get("registration")
    if registration == "unregistered" or citation.get("unregistered"):
        label += "（未登记 / unregistered）"
    elif registration == "missing":
        label += "（缺数据 / missing）"
    if citation.get("needsReview"):
        label += "（需复核 / needs review）"
    return label


def _sentence_text(sentence, lang):
    text = sentence.get("textZh" if lang == "zh" else "textEn", "")
    if sentence.get("status") == "Dismissed":
        text = ("已驳回内容：" if lang == "zh" else "Dismissed content: ") + text
    citations = " ".join(_reference_label(c) for c in sentence.get("citations", []))
    text += " " + citations if citations else ""
    if sentence.get("source") == "Investigator" and citations:
        text += "\n" + (_INHERITED_ZH if lang == "zh" else _INHERITED_EN)
    return text


def _sentences(section):
    return section.get("sentences") or [{"textZh": section.get("textZh", ""), "textEn": section.get("textEn", ""),
                                         "status": section.get("status", "Draft"), "citations": []}]


def _references(report):
    # 同一来源多次出现只在引用表列一次，句中引用保持原顺序。
    found = {}
    for section in report.get("sections", []):
        for sentence in section.get("sentences", []):
            for citation in sentence.get("citations", []):
                found.setdefault((citation["kind"], citation["id"], citation["href"], citation.get("sourceRef", "")), citation)
    return list(found.values())


def render_pdf(report: dict, lang: str, *, include_glossary=True) -> bytes:
    font = _font()
    buffer = io.BytesIO()
    body = ParagraphStyle("rpt-body", fontName=font, fontSize=9, leading=14, wordWrap="CJK", spaceAfter=5)
    heading = ParagraphStyle("rpt-heading", parent=body, fontSize=12, leading=18, spaceBefore=12, spaceAfter=8)
    cover = ParagraphStyle("rpt-cover", parent=body, fontSize=17, leading=25, alignment=TA_CENTER, spaceAfter=15)
    small = ParagraphStyle("rpt-small", parent=body, fontSize=7.5, leading=11)
    page_width, page_height = A4
    available = page_width - 84

    def p(text, style=body):
        return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)

    def page(canvas, doc):
        canvas.saveState()
        canvas.setFont(font, 8)
        canvas.setFillColor(colors.HexColor("#b45309") if _draft(report) else colors.HexColor("#166534"))
        canvas.drawString(42, page_height - 27, _visible_state(report))
        canvas.setFillColor(colors.black)
        canvas.drawRightString(page_width - 42, page_height - 27, _fiction(report))
        if _review_notice(report):
            canvas.setFont(font, 6.5)
            canvas.drawString(42, page_height - 39, _review_notice(report))
        canvas.setFont(font, 6.7)
        canvas.drawCentredString(page_width / 2, 27, f"{DISCLAIMER_ZH} / {DISCLAIMER_EN}")
        canvas.drawRightString(page_width - 42, 15, str(doc.page))
        if _draft(report):
            canvas.saveState()
            canvas.setFillColor(colors.Color(0.8, 0.8, 0.8, alpha=0.15))
            canvas.translate(page_width / 2, page_height / 2)
            canvas.rotate(35)
            canvas.setFont(font, 48)
            canvas.drawCentredString(0, 0, "DRAFT 草稿")
            canvas.restoreState()
        canvas.restoreState()

    flow = [p(_title(report), cover), p(_visible_state(report), heading), p(_fiction(report), heading),
            p(f"{report.get('caseId', '')} · {report.get('reportId', '')} · v{report.get('version', 1)}", small),
            p(f"{DISCLAIMER_ZH} / {DISCLAIMER_EN}", heading), Spacer(1, 9)]
    if _review_notice(report):
        flow.insert(2, p(_review_notice(report), small))
    for number, section in enumerate(report.get("sections", []), 1):
        section_title = section.get("titleZh") if lang == "zh" else section.get("titleEn")
        if lang == "bilingual":
            section_title = f"{section.get('titleZh', '')} / {section.get('titleEn', '')}"
        flow.append(p(f"{number}. {section_title} [{_status(section.get('status', 'Draft'))}]", heading))
        if section.get("missing"):
            flow.append(p("含缺数据项 / Contains missing data", small))
        if lang == "bilingual":
            rows = [[p("中文", small), p("English", small)]]
            rows.extend([[p(_sentence_text(s, "zh")), p(_sentence_text(s, "en"))] for s in _sentences(section)])
            table = Table(rows, colWidths=[available / 2, available / 2], repeatRows=1, splitByRow=1, splitInRow=1)
            table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef4f8")),
                ("LINEBELOW", (0, 0), (-1, 0), 0.4, colors.HexColor("#b0bdca")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            flow.append(table)
        else:
            flow.extend(p(_sentence_text(sentence, lang)) for sentence in _sentences(section))
    flow.append(p("引用表 / References", heading))
    refs = _references(report)
    if not refs:
        flow.append(p("缺数据：未提供引用 / Missing data: no references provided"))
    for citation in refs:
        flow.append(p(f"{_reference_label(citation)} {citation['kind']} — {citation['href']} | {citation.get('sourceRef', '')}", small))
    if include_glossary:
        flow.append(p("术语表 / SMCP glossary（中文为项目译文）", heading))
        flow.extend(p(f"{term['termZh']} / {term['termEn']}", small) for term in GLOSSARY)
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=42, leftMargin=42, topMargin=48, bottomMargin=46,
                            title=f"{report.get('reportId', '')} {_state(report)}", author="MCIS 调查工作台")
    doc.build(flow, onFirstPage=page, onLaterPages=page)
    return buffer.getvalue()


def _docx_font(style):
    style.font.name = "Noto Sans SC"
    style.font.size = Pt(9)
    rpr = style.element.get_or_add_rPr()
    fonts = rpr.rFonts
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.insert(0, fonts)
    fonts.set(qn("w:eastAsia"), "Noto Sans SC")


def _docx_sentence(cell, sentence, lang):
    cell.text = _sentence_text(sentence, lang)
    if lang != "zh" or sentence.get("source") != "Investigator" or not sentence.get("citations"):
        return
    # A Chinese run needs an explicit East Asian font and language in narrow table columns.
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            rpr = run._element.get_or_add_rPr()
            rpr.get_or_add_rFonts().set(qn("w:eastAsia"), "Noto Sans CJK SC")
            language = OxmlElement("w:lang")
            language.set(qn("w:eastAsia"), "zh-CN")
            rpr.append(language)


def _repeat_docx_header(row):
    """OOXML header row; office applications repeat it on continuation pages."""
    header = OxmlElement("w:tblHeader")
    row._tr.get_or_add_trPr().append(header)


def render_docx(report: dict, lang: str, *, include_glossary=True) -> bytes:
    document = Document()
    for name in ("Normal", "Title", "Heading 1", "Heading 2"):
        _docx_font(document.styles[name])
    section = document.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.header.paragraphs[0].text = f"{_visible_state(report)} | {_fiction(report)}"
    if _review_notice(report):
        section.header_distance = Inches(0.25)
        section.header.paragraphs[0].add_run("\n" + _review_notice(report))
        for run in section.header.paragraphs[0].runs:
            run.font.size = Pt(8)
    section.footer.paragraphs[0].text = f"{DISCLAIMER_ZH} / {DISCLAIMER_EN}"
    for run in section.footer.paragraphs[0].runs:
        run.font.size = Pt(7)
    document.add_heading(_title(report), 0)
    document.add_paragraph(_visible_state(report))
    if _review_notice(report):
        document.add_paragraph(_review_notice(report))
    document.add_paragraph(_fiction(report))
    document.add_paragraph(f"{report.get('caseId', '')} | {report.get('reportId', '')} | v{report.get('version', 1)}")
    document.add_paragraph(f"{DISCLAIMER_ZH} / {DISCLAIMER_EN}")
    for number, section_data in enumerate(report.get("sections", []), 1):
        title = section_data.get("titleZh") if lang == "zh" else section_data.get("titleEn")
        if lang == "bilingual":
            title = f"{section_data.get('titleZh', '')} / {section_data.get('titleEn', '')}"
        document.add_heading(f"{number}. {title} [{_status(section_data.get('status', 'Draft'))}]", level=1)
        if section_data.get("missing"):
            document.add_paragraph("含缺数据项 / Contains missing data")
        if lang == "bilingual":
            table = document.add_table(rows=1, cols=2)
            table.style = "Table Grid"
            table.rows[0].cells[0].text = "中文"
            table.rows[0].cells[1].text = "English"
            _repeat_docx_header(table.rows[0])
            for sentence in _sentences(section_data):
                cells = table.add_row().cells
                _docx_sentence(cells[0], sentence, "zh")
                _docx_sentence(cells[1], sentence, "en")
        else:
            for sentence in _sentences(section_data):
                document.add_paragraph(_sentence_text(sentence, lang))
    document.add_heading("引用表 / References", level=1)
    refs = _references(report)
    if not refs:
        document.add_paragraph("缺数据：未提供引用 / Missing data: no references provided")
    for citation in refs:
        document.add_paragraph(f"{_reference_label(citation)} {citation['kind']} — {citation['href']} | {citation.get('sourceRef', '')}")
    if include_glossary:
        document.add_heading("术语表 / SMCP glossary（中文为项目译文）", level=1)
        table = document.add_table(rows=1, cols=2)
        table.rows[0].cells[0].text = "中文（项目译文）"
        table.rows[0].cells[1].text = "English"
        _repeat_docx_header(table.rows[0])
        for term in GLOSSARY:
            cells = table.add_row().cells
            cells[0].text = term["termZh"]
            cells[1].text = term["termEn"]
        # Keep short glossary rows compact so a repeated header is not stranded on its own page.
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.space_after = Pt(0)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def export_report(report: dict, *, format: str, lang: str, include_glossary=True) -> bytes:
    """只读生成文件内容；调用方负责真实数据门禁、授权、审计与下载响应头。"""
    if lang not in ("zh", "en", "bilingual"):
        raise ValueError("report language must be zh, en or bilingual")
    if format == "pdf":
        return render_pdf(report, lang, include_glossary=include_glossary)
    if format == "docx":
        return render_docx(report, lang, include_glossary=include_glossary)
    raise ValueError("report format must be pdf or docx")
