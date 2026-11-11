"""报告格式、数据来源和少量 SMCP 中英术语；只定义结构，不编造调查事实。

IMO 第 14 章规定报告提交与公开，报告要素清单见 MSC.255(84) 第 2.12 条。
GISIS 映射依据 contracts/gisis-mapping.md；待核事项随字段保留，不推断正式平台取值。
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
    # TODO(W16.1 裁定3)：章节标题待 Mark 确认真实报告可用后，逐字采用 reports/haili5、reports/yangze22 原文报告章节标题（含责任认定类章节）；当前保留项目标题
    {"templateId": "cn-msa", "titleZh": "中国海事安全调查格式", "titleEn": "China MSA safety investigation structure",
     "standardRefs": [{"title": "项目安全调查模板：原因分析与教训；不作责任认定", "href": "#/report",
                       "pendingRuling": "章节标题待裁定落实"}],
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


# 与 contracts/gisis-mapping.md 逐行对应；partial 字段即使含待核事项也不改成 pending。
_GISIS_MAPPING = {
    "investigatingState": ("附录1·一般信息 .1*", "partial", "Table 1 为 GISIS 国家名录，本地为自由文本；与名录的对照待核"),
    "numberOfShips": ("附录1·一般信息 .2*", "exact", "取案件船舶登记数；没有船舶资料时为缺数据"),
    "incidentTimeUtc": ("附录1·一般事故数据 .2* / .3*", "partial", "通函为分栏当地日期和时间，本地为单个 UTC 时间；当地时区来源待核"),
    "latitude": ("附录1·一般事故数据 .4*", "exact", "十进制度；GISIS 录入格式待核"),
    "longitude": ("附录1·一般事故数据 .5*", "exact", "十进制度；GISIS 录入格式待核"),
    "locationCategory": ("附录1·一般事故数据 .6*", "exact", "Table 3 枚举；仅取案件显式字段，不从文字描述推断"),
    "eventType": ("附录1·一般事故数据 .7*；附录2 3.1（每船，非必填）", "partial", "Table 4 为两级取值，本地只有一级；二级取值待核"),
    "severity": ("附录1·一般事故数据 .8*；附录2 3.2*", "partial", "Table 5 三档；本地等级与 Table 5 对应待核（Serious / LessSerious 不自动归档）；每船分别取值待核"),
    "imoNumber": ("附录2 1.1*", "exact", "IMO 船舶识别号；保留格式与校验位校验"),
    "name": ("附录2 1.2*", "exact", "取船舶资料中的船名"),
    "flagState": ("附录2 1.5*", "exact", "GISIS 自动带出；本地取船舶资料"),
    "vesselType": ("附录2 1.6*", "partial", "本地为船型代码，与 GISIS 船型下拉表的对照待核"),
    "grossTonnage": ("附录2 1.7", "exact", "总吨；不得用排水量代替"),
    "deaths": ("附录2 4.1–4.3", "partial", "通函合计死亡或失踪，按船员、旅客、其他分三栏；本地为死亡合计数"),
    "missingPersons": ("附录2 4.1–4.3", "partial", "通函合计死亡或失踪，按船员、旅客、其他分三栏；本地为失踪合计数"),
    "injuries": ("附录2 4.4–4.6", "partial", "通函只计重伤并分船员、旅客、其他三栏；本地受伤是否等同重伤待核"),
    "shipLoss": ("附录2 4.7", "partial", "通函为是、否、不明三值，本地为布尔；缺值输出 null"),
    "pollution": ("附录2 4.12–4.15", "partial", "通函按污染物种类填类型和数量，无是否污染栏；本地布尔仅作摘要"),
    "pollutionDetails": ("附录2 4.11–4.15", "partial", "自由文本，不能代替按污染物表填报"),
    "reportStatus": ("—", "none", "本地字段，通函无对应；标注草稿、初步、最终"),
}


def _field(id, zh, en, *, required=True, source=None, scope="case", **rules):
    gisis_ref, mapping_status, mapping_note = _GISIS_MAPPING[id]
    return {"id": id, "labelZh": zh, "labelEn": en, "required": required,
            "sourceRefs": [source or f"case.{id}"], "rules": rules or {"type": "string", "minLength": 1}, "scope": scope,
            "gisisRef": gisis_ref, "mappingStatus": mapping_status, "mappingNote": mapping_note}


GISIS_FIELDS = [
    _field("imoNumber", "IMO 船舶识别号", "IMO ship identification number", scope="vessel", source="vessels[].imoNumber",
           type="string", pattern="^[0-9]{7}$", checksum="imo"),
    _field("name", "船名", "Ship name", scope="vessel", source="vessels[].name"),
    _field("flagState", "船旗国", "Flag State", scope="vessel", source="vessels[].flagState"),
    _field("vesselType", "船舶类型", "Ship type", scope="vessel", source="vessels[].vesselTypeCode"),
    _field("grossTonnage", "总吨", "Gross tonnage", required=False, scope="vessel", source="vessels[].grossTonnage", type="number", minimum=1),
    _field("numberOfShips", "涉事船舶数", "Number of ships involved", source="vessels[]", type="integer", minimum=1),
    _field("incidentTimeUtc", "事故日期时间（UTC）", "Occurrence date and time (UTC)", type="string", format="utc"),
    _field("latitude", "纬度", "Latitude", source="case.incidentLocation.latDeg", type="number", minimum=-90, maximum=90),
    _field("longitude", "经度", "Longitude", source="case.incidentLocation.lonDeg", type="number", minimum=-180, maximum=180),
    _field("locationCategory", "事发水域类型", "Location of initial casualty", source="case.incidentLocation.locationCategory", type="string",
           enum=["At berth", "Anchorage", "Port", "Port approach", "Inland waters", "Canal", "River", "Archipelagos",
                 "Coastal waters", "Open sea", "Unknown", "Strait/channel", "Traffic separation scheme", "Offshore installation"]),
    _field("eventType", "事件类型", "Occurrence type", source="case.accidentType", type="string",
           enum=["Collision", "Contact", "Grounding", "Fire", "Explosion", "Capsizing", "Sinking", "Flooding", "Loss of control", "Other"]),
    _field("severity", "事故严重程度", "Casualty severity", source="case.accidentGrade", type="string",
           enum=["Very serious marine casualty", "Marine casualty", "Marine incident"]),
    _field("deaths", "死亡人数", "Fatalities", required=False, type="integer", minimum=0),
    _field("missingPersons", "失踪人数", "Missing persons", required=False, type="integer", minimum=0),
    _field("injuries", "受伤人数", "Injured persons", required=False, type="integer", minimum=0),
    _field("pollution", "是否污染", "Pollution occurred", required=False, type="boolean"),
    _field("pollutionDetails", "污染说明", "Pollution details", required=False),
    _field("shipLoss", "船舶灭失", "Total loss of ship", required=False, type="boolean"),
    _field("investigatingState", "调查国", "Marine safety investigating State"),
    _field("reportStatus", "报告状态", "Report status", required=False, type="string", enum=["Draft", "Preliminary", "Final"]),
]


def get_template(template_id: str):
    """调用方可编辑副本，不会污染后续案件的模板。"""
    return next((deepcopy(t) for t in TEMPLATES if t["templateId"] == template_id), None)
