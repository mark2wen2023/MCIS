"""Explicit two-phase remote host boundary. No routes or automatic env selection.

A trusted caller must show describe_egress's disclosure to its user and pass the
approved digest only after that user's approval. A digest is a scope binding,
not proof of a human click. Never accept it from untrusted model/tool output.
"""
import copy
import re
from . import deepseek_client as d, host_extraction as h, extraction as e
from ..common.context import problem


def _prepare(args, cfg):
    d.validate_config(cfg)
    binding, record, policy, scope = h._snapshot(*args)
    messages = e.prompt(record, policy)
    disclosure = {'destination': d.ENDPOINT, 'provider': 'DeepSeek', 'model': cfg.model,
                  'caseId': args[3], 'recordId': args[4], 'bindingDigest': binding,
                  'promptDigest': e.digest(messages), 'content': 'redacted-interview-turns',
                  'purpose': 'unreviewed-statement-extraction', 'sourceScope': scope,
                  'scopeVersion': 1}
    # Session binding prevents transfer to another authorized user's session.
    digest = e.digest({'disclosure': disclosure, 'sessionBinding': e.digest(args[2])})
    return disclosure, digest, record, policy, messages


def describe_egress(db, settings, session_token, case_id, record_id, cfg):
    disclosure, digest, *_ = _prepare((db, settings, session_token, case_id, record_id), cfg)
    return {**disclosure, 'approvalDigest': digest, 'approvalRequired': True,
            'requestAttempted': False, 'humanApprovalVerified': False}


def run(db, settings, session_token, case_id, record_id, cfg=None, *, approved_disclosure_digest=None):
    args = (db, settings, session_token, case_id, record_id)
    if cfg is None:
        scope = h.describe(*args)['sourceScope']
        return {'status': 'not_connected', 'inferencePerformed': False, 'proposals': [], 'sourceScope': scope}
    if type(approved_disclosure_digest) is not str or not re.fullmatch('[0-9a-f]{64}', approved_disclosure_digest):
        raise problem(403, 'REMOTE_APPROVAL_REQUIRED', '需要明确批准本次 DeepSeek 数据发送范围')
    disclosure, digest, record, policy, messages = _prepare(args, cfg)
    if digest != approved_disclosure_digest:
        raise problem(409, 'REMOTE_APPROVAL_SCOPE_CHANGED', '来源、模型或授权范围已变化，请重新确认')
    # Current policy, source bytes, membership and session are checked immediately
    # before egress and again after inference. Already sent bytes cannot be recalled.
    if _prepare(args, cfg)[1] != digest:
        raise problem(409, 'REMOTE_APPROVAL_SCOPE_CHANGED', '发送范围已变化')
    try:
        content = d.complete(cfg, copy.deepcopy(messages))
        if type(content) is not str or len(content.encode('utf-8')) > h.MAX_OUTPUT:
            raise ValueError()
        payload = e.parse_output(content, record)
        statements, citations = e.checked_statements(payload, record, policy)
    except Exception:
        raise problem(502, 'REMOTE_EXTRACTION_FAILED', '远端抽取未成功，未保存提案') from None
    if _prepare(args, cfg)[1] != digest:
        raise problem(409, 'REMOTE_APPROVAL_SCOPE_CHANGED', '来源或授权已变化，未返回提案')
    receipt = {'bindingDigest': disclosure['bindingDigest'], 'promptDigest': disclosure['promptDigest'],
               'outputDigest': e.digest(payload), 'providerMode': 'remote-deepseek',
               'configuredModel': cfg.model, 'modelIdentityVerified': False,
               'sourceScope': disclosure['sourceScope'], 'persistentAudit': False,
               'signature': False, 'humanApprovalVerified': False}
    receipt['runChecksum'] = e.digest(receipt)
    return {'status': 'PendingReview', 'inferencePerformed': True, 'fixture': False,
            'proposals': statements, 'citations': citations, 'receipt': receipt,
            'saved': False, 'citationMeaning': 'exact_quote_match_only_not_fact_verification'}
