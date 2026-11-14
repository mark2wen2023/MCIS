"""Whole-case raw export preflight; existing local roles are NOT authenticated identity."""
from fastapi import HTTPException
from ..common import contracts
from ..common.context import problem
from ..db import get_doc, list_docs
from ..cases.models import CaseRow, VesselRow, TrackPointRow
from ..environment.models import EnvironmentObservationRow
from ..evidence.models import EvidenceRow
from ..timeline.models import TimelineEventRow, ConflictRow
from ..colreg.models import ColregAnalysisRow
from ..agents.models import AgentDraftRow
from ..interviews.models import InterviewRow
from ..recommendations.models import RecommendationRow, ConsultationRoundRow
from ..redaction.models import AccessPolicyRow
from ..redaction.policy import default_policy
from ..redaction.gateway import filter_evidence, level_of
from ..reports.access import require_content


def deny():
    raise problem(403, 'PACKAGE_CONTENT_FORBIDDEN', '当前策略不允许导出完整案件原文')


def policy_for(s, case_id):
    policy = get_doc(s, AccessPolicyRow, case_id, 'policy')
    if policy is None:
        policy = default_policy()
    try:
        contracts.validate('access-policy', policy)
    except HTTPException:
        deny()
    return policy


def full(policy, role, category):
    if level_of(policy, role, category) not in ('ReadWrite', 'ReadOnly'):
        deny()


def preflight(s, case_id, role):
    # Invoked inside the export's existing BEGIN IMMEDIATE, before filesystem reads.
    case = get_doc(s, CaseRow, case_id, case_id)
    if case is None:
        raise problem(404, 'CASE_NOT_FOUND', '案件不存在')
    policy = policy_for(s, case_id)
    # These raw JSON/index/audit members are always emitted, including empty arrays.
    for category in ('ais_sim', 'evidence_meta', 'audit', 'timeline', 'recommendations', 'agent_drafts'):
        full(policy, role, category)
    # DB scope selects this case. Conflicting embedded bindings must never redirect gates.
    for model in (CaseRow, VesselRow, TrackPointRow, EnvironmentObservationRow, EvidenceRow, TimelineEventRow,
                  ConflictRow, ColregAnalysisRow, AgentDraftRow, InterviewRow,
                  RecommendationRow, ConsultationRoundRow):
        for doc in list_docs(s, model, case_id):
            if not isinstance(doc, dict) or ('caseId' in doc and doc['caseId'] != case_id):
                raise problem(409, 'PACKAGE_CASE_BINDING', '案件记录绑定不一致，未导出')
    for item in list_docs(s, EvidenceRow, case_id):
        if item.get('caseId') != case_id:
            raise problem(409, 'PACKAGE_CASE_BINDING', '证据案件绑定不一致，未导出')
        if not filter_evidence([item], role, policy):
            deny()
        if item.get('confidentiality') == 'Restricted':
            full(policy, role, 'testimony')
        if item.get('category') == 'VDR':
            full(policy, role, 'vdr_audio')


def members(s, case_id, role, files):
    """Every emitted original member is classified; unsupported new members fail closed."""
    policy = policy_for(s, case_id)
    exact = {'case.json':'ais_sim', 'case.ext.json':'ais_sim', 'vessels.json':'ais_sim',
             'environment/observations.json':'ais_sim', 'analysis/timeline.json':'timeline',
             'analysis/time-alignment.json':'timeline', 'analysis/colreg.json':'colreg',
             'recommendations.json':'recommendations', 'consultation/rounds.json':'recommendations',
             'agents/drafts.json':'agent_drafts', 'access-policy.json':'audit'}
    for path, raw in files.items():
        if path.endswith('/.keep') and raw == b'':
            continue
        category = exact.get(path)
        if category is None:
            if path.startswith(('raw/', 'evidence/')): category = 'evidence_meta'
            elif path.startswith('derived/tracks/'): category = 'ais_sim'
            elif path.startswith('testimony/'): category = 'testimony'
            elif path in ('audit/audit.jsonl', 'audit/custody.jsonl', 'audit/agent.jsonl'): category = 'audit'
            elif path == 'hfacs/backup.v1.json':
                require_content(s, case_id, role)
                continue
            else:
                raise problem(409, 'PACKAGE_MEMBER_UNCLASSIFIED', '案件包包含未分类成员，未导出')
        full(policy, role, category)
