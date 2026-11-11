"""报告格式、数据来源和少量 SMCP 中英术语；只定义结构，不编造调查事实。

IMO 第 14 章规定报告提交与公开，报告要素清单见 MSC.255(84) 第 2.12 条。
GISIS 字段是本地准备格式，正式平台字段及条件仍需由架构师确认。
"""
from __future__ import annotations

from copy import deepcopy

DISCLAIMER_ZH = "不作责任认定"
DISCLAIMER_EN = "This report does not apportion blame or liability"
CIC_URL = "https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/MSCResolutions/MSC.255(84).pdf"
GISIS_URL = "https://www.imo.org/en/ourwork/iiis/pages/reporting.aspx"
SMCP_URL = "https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/AssemblyDocuments/A.918%2822%29.pdf"

_SOURCES = {
    "summary": ["case", "vessels", "evidence"],
    "facts": ["case", "vessels", "evidence", "interview-crosscheck"],
    "analysis": ["colreg-check", "interview-crosscheck", "whatif", "systemic", "evidence"],
    "conclusions": ["colreg-check", "interview-crosscheck", "whatif", "systemic"],
    "actions": ["recommendation", "consultation"],
    "recommendations": ["recommendation", "consultation", "evidence"],
    "appendix": ["evidence", "glossary", "gisis"],
}


def _sections(titles):
    return [{"sectionId": sid, "titleZh": zh, "titleEn": en, "dataSources": list(_SOURCES[sid])}
            for sid, zh, en in titles]


TEMPLATES = [
    {"templateId": "imo-cic", "titleZh": "IMO 事故调查规则格式", "titleEn": "IMO Casualty Investigation Code",
     "standardRefs": [{"title": "MSC.255(84) 第14章及第2.12条", "href": CIC_URL}],
     "sections": _sections([
         ("summary", "概要", "Summary"), ("facts", "船舶资料与事实经过", "Ship particulars and factual narrative"),
         ("analysis", "原因分析", "Analysis of causal factors"), ("conclusions", "调查发现与结论", "Findings and conclusions"),
         ("actions", "已采取的安全措施", "Safety action taken"), ("recommendations", "安全建议", "Safety recommendations"),
         ("appendix", "附录与来源", "Appendices and sources")])},
    {"templateId": "maib", "titleZh": "MAIB 报告结构", "titleEn": "MAIB report structure",
     "standardRefs": [{"title": "MAIB 报告六部分结构", "href": "https://www.gov.uk/government/organisations/marine-accident-investigation-branch"}],
     "sections": _sections([
         ("summary", "概要", "Synopsis"), ("facts", "事实资料", "Factual information"),
         ("analysis", "分析", "Analysis"), ("conclusions", "结论", "Conclusions"),
         ("actions", "已采取措施", "Action taken"), ("recommendations", "安全建议", "Recommendations"),
         ("appendix", "附录", "Annexes")])},
    {"templateId": "cn-msa", "titleZh": "中国海事安全调查格式", "titleEn": "China MSA safety investigation structure",
     "standardRefs": [{"title": "项目安全调查模板：原因分析与教训；不作责任认定", "href": "#/report"}],
     "sections": _sections([
         ("summary", "事故概况", "Overview"), ("facts", "船舶资料与事故经过", "Vessel information and sequence of events"),
         ("analysis", "原因分析与教训", "Causal analysis and lessons"), ("conclusions", "安全调查结论", "Safety investigation conclusions"),
         ("actions", "应急处置与已采取措施", "Emergency response and action taken"),
         ("recommendations", "安全管理建议", "Safety management recommendations"), ("appendix", "证据与术语附录", "Evidence and terminology appendix")])},
]

# 英文采用 A.918(22) 的少量术语/舵令；中文为本项目译文，非 IMO 官方中文版本。
GLOSSARY = [
    {"termEn": "Midships", "termZh": "正舵", "note": "SMCP A2/1；中文为项目译文"},
    {"termEn": "Port", "termZh": "左舷／左舵", "note": "方向或舵令须结合上下文"},
    {"termEn": "Starboard", "termZh": "右舷／右舵", "note": "方向或舵令须结合上下文"},
    {"termEn": "Steady", "termZh": "把定", "note": "SMCP A2/1；中文为项目译文"},
    {"termEn": "Stand by engine", "termZh": "备车", "note": "SMCP A2/2；中文为项目译文"},
    {"termEn": "Underkeel clearance", "termZh": "富余水深", "note": "SMCP B1/1.1；中文为项目译文"},
]


def _field(id, zh, en, *, required=True, source=None, scope="case", **rules):
    return {"id": id, "labelZh": zh, "labelEn": en, "required": required,
            "sourceRefs": [source or f"case.{id}"], "rules": rules or {"type": "string", "minLength": 1}, "scope": scope}


GISIS_FIELDS = [
    _field("imoNumber", "IMO 船舶识别号", "IMO ship identification number", scope="vessel", source="vessels[].imoNumber",
           type="string", pattern="^[0-9]{7}$", checksum="imo"),
    _field("name", "船名", "Ship name", scope="vessel", source="vessels[].name"),
    _field("flagState", "船旗国", "Flag State", scope="vessel", source="vessels[].flagState"),
    _field("vesselType", "船舶类型", "Ship type", scope="vessel", source="vessels[].vesselTypeCode"),
    _field("grossTonnage", "总吨", "Gross tonnage", scope="vessel", source="vessels[].grossTonnage", type="number", minimum=1),
    _field("incidentTimeUtc", "事故日期时间（UTC）", "Occurrence date and time (UTC)", type="string", format="utc"),
    _field("latitude", "纬度", "Latitude", source="case.incidentLocation.latDeg", type="number", minimum=-90, maximum=90),
    _field("longitude", "经度", "Longitude", source="case.incidentLocation.lonDeg", type="number", minimum=-180, maximum=180),
    _field("eventType", "事件类型", "Occurrence type", source="case.accidentType", type="string",
           enum=["Collision", "Contact", "Grounding", "Fire", "Explosion", "Capsizing", "Sinking", "Flooding", "Loss of control", "Other"]),
    _field("severity", "事故严重程度", "Casualty severity", source="case.accidentGrade", type="string",
           enum=["Very serious", "Serious", "Less serious", "Marine incident"]),
    _field("deaths", "死亡人数", "Fatalities", type="integer", minimum=0),
    _field("missingPersons", "失踪人数", "Missing persons", type="integer", minimum=0),
    _field("injuries", "受伤人数", "Injured persons", type="integer", minimum=0),
    _field("pollution", "是否污染", "Pollution occurred", type="boolean"),
    _field("pollutionDetails", "污染说明", "Pollution details", required=False),
    _field("shipLoss", "船舶灭失", "Total loss of ship", type="boolean"),
    _field("investigatingState", "调查国", "Marine safety investigating State"),
    _field("reportStatus", "报告状态", "Report status", type="string", enum=["Draft", "Preliminary", "Final"]),
]


def get_template(template_id: str):
    """调用方可编辑副本，不会污染后续案件的模板。"""
    return next((deepcopy(t) for t in TEMPLATES if t["templateId"] == template_id), None)
