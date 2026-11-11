"""报告只读来源适配：每个结论句引用原始业务条目，不补造缺失数据。

W14/W15 尚无服务合同，默认适配器只返回缺数据。未来可替换 SOURCE_ADAPTERS
中对应 callable；协议是 (session, case) -> {missing: bool, items: [...]}，每个
item 必须带 id、textZh、textEn，可带 evidenceIds。适配器不得写数据库或运行引擎。
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable
from urllib.parse import quote

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..cases import service as cases
from ..colreg import evidence_refs
from ..colreg.models import ColregAnalysisRow
from ..common import contracts
from ..db import get_doc, list_docs
from ..evidence import service as evidence
from ..interviews.models import InterviewRow
from ..recommendations.models import ConsultationRoundRow, RecommendationRow


SourceAdapter = Callable[[Session, dict[str, Any]], dict[str, Any]]


def _unavailable(_s: Session, _case: dict[str, Any]) -> dict[str, Any]:
    return {'missing': True, 'items': []}


SOURCE_ADAPTERS: dict[str, SourceAdapter] = {'whatif': _unavailable, 'systemic': _unavailable}

VERDICT_ZH = {
    'Complies': '符合', 'Partial': '部分符合', 'NotComplied': '未符合',
    'NotApplicable': '不适用', 'NeedsReview': '需研判',
    'NotAssessable': '缺证据无法评估', 'Undetermined': '未确定',
}
STATUS_ZH = {'Draft': '草稿', 'Confirmed': '已确认', 'Modified': '已修改', 'Rejected': '已驳回'}
OUTCOME_ZH = {'Consistent': '一致', 'Contradictory': '矛盾', 'Unverifiable': '无法核实'}


def _url(page: str, **query: Any) -> str:
    return '#/' + page + '?' + '&'.join(f'{quote(str(k), safe="")}={quote(str(v), safe="")}'
                                       for k, v in query.items() if v is not None)


def _citation(kind: str, identifier: str, href: str, *, registration: str = 'registered',
              source_ref: str = '', needs_review: bool = False) -> dict[str, Any]:
    return {'kind': kind, 'id': identifier, 'href': href, 'registration': registration,
            'unregistered': registration == 'unregistered', 'sourceRef': source_ref,
            'needsReview': needs_review}


def _sentence(identifier: str, zh: str, en: str, citations: list[dict[str, Any]], *,
              missing: bool = False, source_status: str = '') -> dict[str, Any]:
    return {'sentenceId': identifier, 'status': 'Draft', 'source': 'Generated',
            'textZh': zh, 'textEn': en, 'generatedText': {'textZh': zh, 'textEn': en},
            'reviewedBy': None, 'reviewedAt': None, 'reviews': [], 'missing': missing,
            'citations': deepcopy(citations), 'sourceStatus': source_status}


def _missing(identifier: str, zh: str, en: str, citations: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return _sentence(identifier, '缺数据：' + zh, 'Missing data: ' + en, citations or [],
                     missing=True, source_status='Missing')


def missing_sentence(identifier: str, zh: str, en: str,
                     citations: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """供规则章节单独生成入口复用的标准缺数据句。"""
    return _missing(identifier, zh, en, citations)


def _clone(sentence: dict[str, Any], identifier: str) -> dict[str, Any]:
    out = deepcopy(sentence)
    out['sentenceId'] = identifier
    return out


def build_sections(s: Session, case: dict[str, Any], template: dict[str, Any]) -> list[dict[str, Any]]:
    """从当前已存档来源创建全 Draft 章节，绝不调用 COLREG evaluate / runs.ensure。

    案件与船舶字段属于元数据，不伪装为有证据支持的结论；其 citations 可为空，
    sourceStatus=CaseFields。来源业务结论逐句引用原条目，未登记证据保留且标记。
    """
    case_id = case['caseId']
    items = evidence.list_items(s, case_id)
    evidence_by_id = {x['evidenceId']: x for x in items}
    validated_evidence: dict[str, dict[str, Any]] = {}

    def ev_citation(identifier: Any) -> dict[str, Any]:
        # 调用 W6 共享校验器（其实现使用 Evidence 库及公共 evidenceRef 合同）。
        key = str(identifier)
        if key not in validated_evidence:
            registration = 'registered'
            try:
                evidence_refs.require_registered(s, case_id, [identifier])
            except HTTPException as exc:
                if exc.status_code != 422 or not isinstance(exc.detail, dict) or \
                        exc.detail.get('code') != 'evidence_not_registered':
                    raise
                registration = 'unregistered'
            validated_evidence[key] = _citation(
                'evidence', key, _url('evidence', id=key, case=case_id), registration=registration,
                source_ref=f'evidence/{key}', needs_review=bool(evidence_by_id.get(key, {}).get('needsReview')))
        return deepcopy(validated_evidence[key])

    def ev_citations(identifiers: list[Any] | None) -> list[dict[str, Any]]:
        # 去重只影响重复引用，不丢弃任何未登记或格式不合法的编号。
        seen: set[str] = set()
        out = []
        for identifier in identifiers or []:
            if str(identifier) not in seen:
                seen.add(str(identifier))
                out.append(ev_citation(identifier))
        return out

    colreg = get_doc(s, ColregAnalysisRow, case_id, 'current') or {'checks': [], 'bands': []}
    index = get_doc(s, ColregAnalysisRow, case_id, 'runs') or {}
    active_id = index.get('activeRunId')
    active = get_doc(s, ColregAnalysisRow, case_id, 'run:' + str(active_id)) if active_id else None
    # 仅取与 current 同一份分析的注解，避免外部导入后旧注解被误贴到新结果。
    annotations = (active or {}).get('annotations', {}) if (active or {}).get('analysis') == colreg else {}
    check_annotations = annotations.get('checks') or {}
    checks = colreg.get('checks') or []
    interviews = list_docs(s, InterviewRow, case_id)
    recommendations = list_docs(s, RecommendationRow, case_id)
    rounds = list_docs(s, ConsultationRoundRow, case_id)
    vessels = cases.vessels(s, case_id)
    vessel_names = {x['vesselId']: x.get('name') or x['vesselId'] for x in vessels}
    grouped: dict[str, list[dict[str, Any]]] = {
        name: [] for name in ('summary', 'facts', 'analysis', 'conclusions', 'actions', 'recommendations', 'appendix')}

    # 元数据直接指出字段来源，不借用没有关联关系的证据编号。
    incident = case.get('incidentTimeUtc')
    location = case.get('incidentLocation') or {}
    case_text_zh = f'案件字段：{case_id}；事件类型={case.get("accidentType") or "缺数据"}；事故时间 UTC={incident or "缺数据"}。'
    case_text_en = f'Case fields: {case_id}; event type={case.get("accidentType") or "Missing data"}; incident time UTC={incident or "Missing data"}.'
    grouped['summary'].append(_sentence('summary-case-fields', case_text_zh, case_text_en, [],
                                        missing=not incident, source_status='CaseFields'))
    if location:
        grouped['facts'].append(_sentence(
            'facts-case-position',
            f'案件位置字段：纬度={location.get("latDeg", "缺数据")}；经度={location.get("lonDeg", "缺数据")}。',
            f'Case location fields: latitude={location.get("latDeg", "Missing data")}; longitude={location.get("lonDeg", "Missing data")}.',
            [], missing=location.get('latDeg') is None or location.get('lonDeg') is None,
            source_status='CaseFields'))
    for vessel in vessels:
        vid = vessel['vesselId']
        grouped['facts'].append(_sentence(
            'facts-vessel-' + vid,
            f'船舶字段：{vessel.get("name") or vid}；IMO={vessel.get("imoNumber") or "缺数据"}；船旗={vessel.get("flagState") or "缺数据"}；类型={vessel.get("vesselTypeCode") or "缺数据"}。',
            f'Vessel fields: name={vessel.get("name") or vid}; IMO={vessel.get("imoNumber") or "Missing data"}; flag={vessel.get("flagState") or "Missing data"}; type={vessel.get("vesselTypeCode") or "Missing data"}.',
            [], missing=any(not vessel.get(k) for k in ('imoNumber', 'flagState', 'vesselTypeCode')),
            source_status='CaseFields'))

    for item in items:
        eid = item['evidenceId']
        status = item.get('status') or 'Unverified'
        needs_review = bool(item.get('needsReview'))
        zh = f'证据台账 {eid} 登记标题“{item.get("title", "")}”，保管链状态={status}'
        en = f'Evidence register {eid}: custody status={status}; source title (original language): "{item.get("title", "")}"'
        if needs_review:
            zh += '，需复核'
            en += '; review required'
        grouped['facts'].append(_sentence('facts-evidence-' + eid, zh + '。', en + '.',
                                          [ev_citation(eid)], source_status=status))
        grouped['appendix'].append(_sentence(
            'appendix-evidence-' + eid,
            f'引用登记 {eid}：来源={item.get("source", "缺数据")}；提取时间 UTC={item.get("extractedUtc", "缺数据")}；状态={status}。',
            f'Reference register {eid}: extraction UTC={item.get("extractedUtc", "Missing data")}; custody status={status}; source label (original language): "{item.get("source", "")}".',
            [ev_citation(eid)], source_status=status))

    if items:
        grouped['summary'].append(_sentence(
            'summary-evidence-count', f'证据台账已登记 {len(items)} 项证据。',
            f'The evidence register contains {len(items)} registered items.',
            [ev_citation(x['evidenceId']) for x in items], source_status='Registered'))
    else:
        grouped['facts'].append(_missing('facts-evidence-missing', '本案尚无已登记证据。',
                                         'no registered evidence is available for this case.'))

    for check in checks:
        cid = str(check['checkId'])
        review_status = check.get('reviewStatus') or 'Draft'
        verdict = check.get('verdict') or 'Undetermined'
        rule = check.get('rule') or ''
        vessel_name = vessel_names.get(check.get('vesselId'), check.get('vesselId') or '')
        annotation = check_annotations.get(cid) or {}
        refs = [_citation('colreg-check', cid, _url('colreg', case=case_id, check=cid, run=active_id),
                          source_ref=f'colreg/current/checks/{cid}')]
        refs.extend(ev_citations(check.get('evidenceIds')))
        zh = f'规则核查 {cid}（{vessel_name} / {rule}）记录判定为“{VERDICT_ZH.get(verdict, verdict)}”，复核状态={review_status}（{STATUS_ZH.get(review_status, review_status)}）'
        en = f'COLREG check {cid} ({vessel_name} / {rule}) records verdict={verdict}; review status={review_status}'
        if review_status == 'Draft':
            zh += '；该项尚未人工确认，不作为最终结论'
            en += '; this item has not been confirmed by an investigator and is not a final finding'
        if annotation.get('reviewedBy'):
            zh += f'；复核人={annotation["reviewedBy"]}，复核时间 UTC={annotation.get("reviewedAt") or "缺数据"}'
            en += f'; reviewer={annotation["reviewedBy"]}; reviewed UTC={annotation.get("reviewedAt") or "Missing data"}'
        if check.get('requiredAction') or check.get('actualAction'):
            zh += f'；应采取={check.get("requiredAction") or "缺数据"}；实际行动={check.get("actualAction") or "缺数据"}'
            en += f'; required action (source text)="{check.get("requiredAction") or "Missing data"}"; actual action (source text)="{check.get("actualAction") or "Missing data"}"'
        if not check.get('evidenceIds'):
            zh += '；缺数据：该核查项未提供证据引用'
            en += '; Missing data: this check provides no evidence references'
        sentence = _sentence('analysis-colreg-' + cid, zh + '。', en + '.', refs,
                             missing=not check.get('evidenceIds'), source_status=review_status)
        grouped['analysis'].append(sentence)
        if review_status in ('Confirmed', 'Modified'):
            grouped['conclusions'].append(_clone(sentence, 'conclusions-colreg-' + cid))
    if not checks:
        grouped['analysis'].append(_missing('analysis-colreg-missing', 'COLREG 核查项未提供。',
                                            'COLREG checks have not been provided.'))

    confirmed_crosschecks: list[dict[str, Any]] = []
    for record in interviews:
        rid = record['recordId']
        for result in record.get('crossChecks') or []:
            sid = result['statementId']
            state = result.get('state') or 'PendingConfirmation'
            refs = [_citation('interview-crosscheck', sid,
                              _url('interview', case=case_id, id=rid, statement=sid),
                              source_ref=f'interviews/{rid}/crosscheck/{sid}')]
            ref_ids = list(result.get('evidenceIds') or [])
            if record.get('evidenceId'):
                ref_ids.insert(0, record['evidenceId'])
            refs.extend(ev_citations(ref_ids))
            outcome = result.get('outcome') or 'Unverifiable'
            if state == 'Confirmed':
                zh = f'询问比对 {sid} 已人工确认，结果记录为“{OUTCOME_ZH.get(outcome, outcome)}”；陈述原文摘要={result.get("claimedText") or "缺数据"}；观测记录={result.get("observedText") or "缺数据"}。'
                en = f'Interview crosscheck {sid} was confirmed by an investigator; recorded outcome={outcome}; claimed source text="{result.get("claimedText") or "Missing data"}"; observed source text="{result.get("observedText") or "Missing data"}".'
                sentence = _sentence('analysis-interview-' + sid, zh, en, refs, source_status=state)
                grouped['analysis'].append(sentence)
                confirmed_crosschecks.append(sentence)
            else:
                state_zh = '待确认，尚不作为生效结论' if state == 'PendingConfirmation' else f'状态={state}，不进入分析结论'
                grouped['appendix'].append(_sentence(
                    'appendix-interview-' + sid,
                    f'询问比对 {sid}：{state_zh}；台账结果={OUTCOME_ZH.get(outcome, outcome)}。',
                    f'Interview crosscheck {sid}: state={state}; recorded outcome={outcome}; excluded from effective analysis findings.',
                    refs, source_status=state))
    for sentence in confirmed_crosschecks:
        grouped['conclusions'].append(_clone(sentence, sentence['sentenceId'].replace('analysis-', 'conclusions-', 1)))

    for kind, label_zh, label_en, number in (
            ('whatif', '推演对比表', 'what-if comparison table', 'W14'),
            ('systemic', '系统分析', 'systemic analysis', 'W15')):
        source = SOURCE_ADAPTERS.get(kind, _unavailable)(s, deepcopy(case))
        supplied = source.get('items') or []
        if source.get('missing', True) or not supplied:
            grouped['analysis'].append(_missing(
                'analysis-' + kind + '-missing', f'{number} {label_zh}未提供',
                f'{number} {label_en} has not been provided',
                [_citation(kind, number, _url(kind, case=case_id), registration='missing',
                           source_ref=number)]))
            continue
        for i, value in enumerate(supplied, 1):
            # 没有双语正文或编号的来源不能被包装成已存在的结论。
            if not all(isinstance(value.get(k), str) and value[k].strip() for k in ('id', 'textZh', 'textEn')):
                grouped['analysis'].append(_missing(
                    f'analysis-{kind}-invalid-{i}', f'{number} 来源条目缺少编号或双语文本',
                    f'{number} source item lacks an identifier or bilingual text'))
                continue
            identifier = value['id']
            refs = [_citation(kind, identifier, _url(kind, case=case_id, id=identifier),
                              source_ref=f'{number}/{identifier}')]
            refs.extend(ev_citations(value.get('evidenceIds')))
            grouped['analysis'].append(_sentence(
                f'analysis-{kind}-{i}-{identifier}', value['textZh'], value['textEn'], refs,
                source_status=str(value.get('reviewStatus') or 'Provided')))

    for rec in recommendations:
        rid = rec['id']
        status = rec.get('status') or 'Draft'
        refs = [_citation('recommendation', rid, _url('recs', case=case_id, id=rid),
                          source_ref=f'recommendations/{rid}')]
        refs.extend(ev_citations(rec.get('evidenceIds')))
        sentence = _sentence(
            'recommendations-' + rid,
            f'安全建议 {rid}：“{rec.get("title") or "缺数据"}”；对象={rec.get("addressee") or "缺数据"}；状态={status}；期限 UTC={rec.get("dueUtc") or "缺数据"}。',
            f'Safety recommendation {rid}: status={status}; due UTC={rec.get("dueUtc") or "Missing data"}; source title="{rec.get("title") or "Missing data"}"; addressee (source text)="{rec.get("addressee") or "Missing data"}".',
            refs, source_status=status)
        grouped['recommendations'].append(sentence)
        if status in ('Implemented', 'Closed'):
            grouped['actions'].append(_sentence(
                'actions-' + rid,
                f'安全建议 {rid} 的落实台账状态={status}；核实说明={rec.get("verificationNote") or "缺数据"}。',
                f'The action register for recommendation {rid} records status={status}; verification note (source text)="{rec.get("verificationNote") or "Missing data"}".',
                refs, missing=not rec.get('verificationNote'), source_status=status))
    if recommendations:
        grouped['summary'].append(_sentence(
            'summary-recommendations-count', f'安全建议台账记录 {len(recommendations)} 条建议，逐条落实状态见建议章节。',
            f'The safety recommendation register contains {len(recommendations)} entries; individual action states are listed in the recommendations section.',
            [_citation('recommendation', x['id'], _url('recs', case=case_id, id=x['id']),
                       source_ref=f'recommendations/{x["id"]}') for x in recommendations],
            source_status='Registered'))
    for rnd in rounds:
        n = rnd.get('roundNo')
        # 轮次属于台账元数据；当前合同没有 consultation 引用种类，且轮次未关联
        # 具体建议编号，不能把全案建议冒充为该轮次事实的出处。
        grouped['appendix'].append(_sentence(
            f'appendix-consultation-{n}',
            f'征求意见台账第 {n} 轮：草案版本={rnd.get("draftVersion") or "缺数据"}；截止时间 UTC={rnd.get("deadlineUtc") or "缺数据"}；状态={"已关闭" if rnd.get("isClosed") else "进行中"}。',
            f'Consultation register round {n}: draft version (source text)="{rnd.get("draftVersion") or "Missing data"}"; deadline UTC={rnd.get("deadlineUtc") or "Missing data"}; closed={bool(rnd.get("isClosed"))}.',
            [], source_status='CaseFields'))

    if not grouped['conclusions']:
        grouped['conclusions'].append(_missing(
            'conclusions-reviewed-missing', '尚无已人工确认或修改的规则核查、或已确认的询问比对结论。',
            'no confirmed or modified COLREG findings or confirmed interview crosschecks are available.'))
    for name, zh, en in (
            ('actions', '已采取措施记录未提供。', 'records of action taken have not been provided.'),
            ('recommendations', '安全建议未提供。', 'safety recommendations have not been provided.'),
            ('appendix', '证据和待确认来源清单未提供。', 'evidence and pending-source registers have not been provided.')):
        if not grouped[name]:
            grouped[name].append(_missing(name + '-missing', zh, en))

    sections = []
    for spec in template['sections']:
        identifier = spec['sectionId']
        sentences = grouped.get(identifier) or [_missing(identifier + '-missing', '章节来源未提供。',
                                                         'section sources have not been provided.')]
        zh = '\n'.join(x['textZh'] for x in sentences)
        en = '\n'.join(x['textEn'] for x in sentences)
        section = {'sectionId': identifier, 'titleZh': spec['titleZh'], 'titleEn': spec['titleEn'],
                   'dataSources': list(spec.get('dataSources') or []), 'status': 'Draft', 'source': 'Generated',
                   'textZh': zh, 'textEn': en, 'generatedText': {'textZh': zh, 'textEn': en},
                   'reviewedBy': None, 'reviewedAt': None, 'reviews': [],
                   'missing': any(x['missing'] for x in sentences), 'sentences': sentences}
        contracts.validate('report#/$defs/section', section)
        sections.append(section)
    return sections
