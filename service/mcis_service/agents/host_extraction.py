"""Opt-in protected callable extraction. No old routes, persistence or implicit model."""
import copy
import re
from dataclasses import dataclass
from types import SimpleNamespace
from urllib.parse import urlsplit
from fastapi import HTTPException
from . import extraction,model_client
from ..investigation import journal
from ..interviews import service as interviews,access
from ..redaction.gateway import get_policy,require
from ..common.context import problem

MAX_OUTPUT=256*1024

@dataclass(frozen=True)
class FixtureProvider:
    """Explicit fixed-output contract fixture; never genuine inference."""
    content:str
    def complete(self,messages):return self.content

@dataclass(frozen=True)
class LocalProvider:
    """Host supplies already selected config; never reads model/credential env."""
    config:model_client.ModelConfig
    def complete(self,messages):
        cfg=self.config
        try:
            u=urlsplit(cfg.base_url)
            valid=(type(cfg) is model_client.ModelConfig and u.scheme=='http' and u.hostname in ('127.0.0.1','::1')
                and u.port is not None and 1<=u.port<=65535 and not u.username and not u.password
                and not u.query and not u.fragment and u.path.rstrip('/')=='/v1'
                and isinstance(cfg.model,str) and 0<len(cfg.model)<=200 and bool(cfg.model.strip()) and all(ord(x)>=32 for x in cfg.model))
        except (ValueError,TypeError,AttributeError):valid=False
        if not valid:raise problem(503,'HOST_MODEL_CONFIG_INVALID','模型端点配置无效')
        return model_client.complete(cfg,messages)


def snapshot_in_session(s,db,settings,token,case_id,record_id):
    """Reuse the caller transaction; never opens/commits a nested session."""
    authority,generation=journal.auth(s,token,case_id)
    ctx=SimpleNamespace(db=db,settings=settings,role=authority.role,operator=authority.subject_id)
    require(ctx,s,case_id,'testimony')
    require(SimpleNamespace(role='AgentService'),s,case_id,'testimony')
    record=copy.deepcopy(interviews.load(s,case_id,record_id))
    if record['caseId']!=case_id or record['recordId']!=record_id:raise problem(409,'HOST_SOURCE_CHANGED','笔录绑定无效')
    access.document(s,ctx,record)
    policy=copy.deepcopy(get_policy(s,case_id))
    source=journal.source_current(ctx,s,case_id,record['evidenceId']) if record.get('evidenceId') else None
    binding={'caseId':case_id,'recordId':record_id,'caseIncarnation':generation,
        'caseEpochUtc':journal.load_case(s,case_id)['caseEpochUtc'],'record':record,'policy':policy,'source':source}
    checksum=extraction.digest(binding)
    if journal.auth(s,token,case_id)!=(authority,generation):raise problem(403,'HOST_EXTRACTION_DENIED','授权已变化')
    return checksum,record,policy,'registered_original_bytes' if source else 'interview_document_only'


def _snapshot(db,settings,token,case_id,record_id):
    with db.session() as s:
        return snapshot_in_session(s,db,settings,token,case_id,record_id)

def describe(db,settings,session_token,case_id,record_id):
    """Authorized descriptor only, with no interview text or source details."""
    binding,_,_,scope=_snapshot(db,settings,session_token,case_id,record_id)
    return {'bindingDigest':binding,'sourceScope':scope}


def run(db,settings,session_token,case_id,record_id,expected_binding_digest,provider=None):
    if not isinstance(expected_binding_digest,str) or not re.fullmatch('[0-9a-f]{64}',expected_binding_digest):
        raise problem(422,'HOST_BINDING_REQUIRED','需要有效来源绑定')
    binding,record,policy,scope=_snapshot(db,settings,session_token,case_id,record_id)
    if binding!=expected_binding_digest:raise problem(409,'HOST_SOURCE_CHANGED','来源或策略已变化')
    if provider is None:return {'status':'not_connected','inferencePerformed':False,'proposals':[],'sourceScope':scope}
    if type(provider) not in (FixtureProvider,LocalProvider):raise problem(422,'HOST_PROVIDER_INVALID','需要显式可信提供方')
    messages=extraction.prompt(record,policy)
    # Short recheck before egress. No lock spans inference; revocation cannot recall bytes already sent.
    if _snapshot(db,settings,session_token,case_id,record_id)[0]!=binding:raise problem(409,'HOST_SOURCE_CHANGED','来源或策略已变化')
    prompt_digest=extraction.digest(messages)
    try:
        content=provider.complete(copy.deepcopy(messages))
        if not isinstance(content,str) or len(content.encode('utf-8'))>MAX_OUTPUT:raise ValueError()
        payload=extraction.parse_output(content,record)
        statements,citations=extraction.checked_statements(payload,record,policy)
    except Exception:
        raise problem(502,'HOST_EXTRACTION_FAILED','抽取未成功，未保存提案') from None
    if _snapshot(db,settings,session_token,case_id,record_id)[0]!=binding:raise problem(409,'HOST_SOURCE_CHANGED','来源或策略已变化，未返回提案')
    mode='fixture' if type(provider) is FixtureProvider else 'local'
    receipt={'bindingDigest':binding,'promptDigest':prompt_digest,'outputDigest':extraction.digest(payload),
        'providerMode':mode,'modelIdentityVerified':False,'configuredModel':provider.config.model if mode=='local' else None,'persistentAudit':False,'signature':False,'sourceScope':scope}
    receipt['runChecksum']=extraction.digest(receipt)
    return {'status':'PendingReview','inferencePerformed':mode=='local','fixture':mode=='fixture',
        'proposals':statements,'citations':citations,'receipt':receipt,'saved':False,
        'citationMeaning':'exact_quote_match_only_not_fact_verification'}
