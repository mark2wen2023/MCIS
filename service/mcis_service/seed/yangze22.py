"""Import public report metadata only. No trajectories, findings or liability are inferred."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..audit import service as audit
from ..cases.models import CaseRow, VesselRow
from ..common import contracts
from ..common.timeutil import iso, now_utc
from ..config import PROJECT_ROOT
from ..db import get_doc, put_doc
from ..evidence import service as ev
from ..evidence.models import EvidenceRow
from ..redaction.models import AccessPolicyRow
from ..redaction.policy import default_policy

CASE_ID = 'CJK-2024-1230-YangZe22-VegaDream'
SOURCE_HASHES = {
    'case.json': '63aad2f28aef4f67ecaf346dea13a2004f268ad9afc4b5d7f86783fcacb5b2c2',
    'report.txt': '7adad5bb499c28eb3985b79411c61dad593797e0d2a8aa64feb203077e43ee2b',
}
VESSEL_FIELDS = ('vesselId', 'name', 'imoNumber', 'callSign', 'mmsi', 'flagState',
                 'vesselTypeCode', 'loaM', 'beamM')


def load_source(source_root: Path | None = None):
    root = source_root or PROJECT_ROOT / 'reports/yangze22'
    blobs = {}
    for name, expected in SOURCE_HASHES.items():
        data = (root / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f'YANGZE public source checksum mismatch: {name}')
        blobs[name] = data
    source = json.loads(blobs['case.json'])
    if source['caseId'] != CASE_ID or source.get('isFictionalDemo') is not False:
        raise ValueError('YANGZE source identity mismatch')
    return source, blobs


def documents(source):
    case = {
        'caseId': CASE_ID, 'schemaVersion': '1.0.0', 'title': source['title'],
        'accidentType': 'Collision', 'accidentGrade': source['accidentGrade'],
        'incidentTimeUtc': source['incidentTimeUtc'], 'caseEpochUtc': source['incidentTimeUtc'],
        'displayTimeZoneOffsetMinutes': 480,
        'incidentLocation': {k: source['incidentLocation'][k] for k in ('latDeg', 'lonDeg')},
        'isFictionalDemo': False, 'agencyName': source['investigatingBody'],
        'placeName': source['incidentLocationText'],
        'summaryNotes': (
            '公开调查报告，非虚构。【直接】碰撞北京时间2024-12-30 22:01:54，报告正文p14–15；'
            '【推算】UTC=北京时间减8小时，位置十进制度由报告度分坐标转换。'
            'caseEpochUtc以碰撞时刻作为技术参考零点，不是额外事故事实。'
            '事故等级保留原文“较大”，未映射IMO严重程度。'
            '船长采用证书值；AIS静态差异、原文冲突及缺失保存在结构化来源证据。'
            '本次只导入元数据、船舶和来源证据，不提供轨迹或责任认定。'
            '逐字段出处见EV-203；原文见EV-201。'
        ),
    }
    vessels = [{**{k: v[k] for k in VESSEL_FIELDS}, 'caseId': CASE_ID} for v in source['vessels']]
    provenance = {
        'caseId': CASE_ID, 'sourceHashes': SOURCE_HASHES,
        'caseFields': {
            'title': {'kind': '直接', 'path': 'case.json#/title'},
            'accidentType': {'kind': '推算', 'path': 'case.json#/accidentType', 'mapping': '碰撞 -> Collision'},
            'accidentGrade': {'kind': '直接', 'path': 'case.json#/accidentGrade', 'note': '原文较大，不推断IMO级别'},
            'incidentTimeUtc': {'kind': '推算', 'source': source['collision']['timeSource'], 'mapping': '北京时间减8小时'},
            'caseEpochUtc': {'kind': '技术配置', 'note': '碰撞时刻作为参考零点，非新增事实'},
            'incidentLocation': {'kind': '推算', 'source': source['collision']['locationSource'], 'mapping': '度分换算十进制度'},
            'agencyName': {'kind': '直接', 'path': 'case.json#/investigatingBody'},
            'placeName': {'kind': '直接', 'path': 'case.json#/incidentLocationText'},
            'displayTimeZoneOffsetMinutes': {'kind': '技术配置', 'path': 'case.json#/displayTimeZoneOffsetMinutes'},
            'caseId/schemaVersion/isFictionalDemo': {'kind': '技术配置', 'note': '规范标识及非虚构来源标记'},
        },
        'vessels': [{
            'vesselId': v['vesselId'],
            'fields': {k: {'kind': '技术配置' if k == 'vesselId' else ('推算' if k == 'vesselTypeCode' else '直接'),
                           'path': f'case.json#/vessels/{i}/{k}',
                           'source': v['fieldSources'].get('vesselType' if k == 'vesselTypeCode' else k),
                           'note': 'vesselId为技术标识；船型为代码映射；船长采用证书值，不采用AIS静态值'}
                       for k in VESSEL_FIELDS}
        } for i, v in enumerate(source['vessels'])],
        'discrepancies': source['discrepancies'], 'missingData': source['missingData'],
        'excluded': '不导入轨迹、首尾吃水、责任、IMO等级；合同外字段保留原始证据，不丢弃来源。',
    }
    contracts.validate('case', case)
    for vessel in vessels:
        contracts.validate('vessel', vessel)
    return case, vessels, provenance


def seed(s, blob_root: Path, *, source_root: Path | None = None) -> bool:
    # Existing cases are user-owned: no overwrite, backfill or re-registration on restart.
    if get_doc(s, CaseRow, CASE_ID, CASE_ID) is not None:
        return False
    source, blobs = load_source(source_root)
    case, vessels, provenance = documents(source)
    blobs['import-provenance.json'] = json.dumps(provenance, ensure_ascii=False, indent=2).encode()
    entries = [('EV-201', 'report.txt', '公开报告文本'),
               ('EV-202', 'case.json', '公开报告结构化摘录（含差异与缺项）'),
               ('EV-203', 'import-provenance.json', '入库字段出处与转换清单')]
    extracted = iso(now_utc())
    items = []
    for eid, name, title in entries:
        item = {'evidenceId': eid, 'caseId': CASE_ID, 'title': title,
                'source': f'reports/yangze22/{name}' if name != 'import-provenance.json' else '公开报告入库适配器生成',
                'extractedBy': '公开报告导入', 'extractedUtc': extracted,
                'sha256': hashlib.sha256(blobs[name]).hexdigest(), 'relativePath': 'raw/public/' + name,
                'category': 'Document', 'confidentiality': 'Normal',
                'note': '公开资料非虚构。原文与结构化摘录分别保存；【直接】/【推算】及技术配置见字段清单。不作责任认定。'}
        contracts.validate('evidence-item', item)
        items.append((item, blobs[name]))
    # Transaction retries may leave immutable blob files; reuse only exact bytes.
    for item, data in items:
        target = ev.blob_path(blob_root, CASE_ID, item['relativePath'])
        if target.exists() and target.read_bytes() != data:
            raise ValueError('YANGZE existing source blob differs: ' + item['relativePath'])
    for item, data in items:
        if not ev.blob_path(blob_root, CASE_ID, item['relativePath']).exists():
            ev.write_blob(blob_root, CASE_ID, item['relativePath'], data)
    put_doc(s, CaseRow, CASE_ID, CASE_ID, case)
    for vessel in vessels:
        put_doc(s, VesselRow, CASE_ID, vessel['vesselId'], vessel)
    for item, _ in items:
        put_doc(s, EvidenceRow, CASE_ID, item['evidenceId'], item)
        ev.append_custody(s, case_id=CASE_ID, evidence_id=item['evidenceId'], kind='Register',
                         operator='公开报告导入', role='Investigator', sha256=item['sha256'],
                         detail='登记已校验公开来源；非原始AIS/VDR', item=item, utc=extracted)
    put_doc(s, AccessPolicyRow, CASE_ID, 'policy', default_policy())
    audit.append(s, case_id=CASE_ID, operator='公开报告导入', role='LeadInvestigator',
                 action='seed.load', category='Case', command='导入YANGZE22公开报告元数据',
                 after='2船/3来源证据；无轨迹，无自动责任认定', entity_type='case', entity_id=CASE_ID)
    return True
