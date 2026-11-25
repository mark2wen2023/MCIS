"""Deterministic preview adapter. No model, retrieval, persistence or publication."""
from __future__ import annotations
import copy
import os
from ..common.context import problem

PROFILE = 'MCIS-KNOWLEDGE-SUGGESTION-1'
PROVIDER = 'template-stub-v1'
WARNING = '仅模板复制与截取，非模型推理；未核验事实、来源或使用权。标题和摘要可能截断，请人工编辑。'
LIMITATION = '模板整理预览，未经人工核验；仅供候选录入，不是事实认证、调查结论或责任认定。'


def suggest(body):
    # Import here to share the existing strict W19.1 boundary without a second validator.
    from .router import canonical, digest, validate_content
    canonical(body)
    if set(body) != {'kind', 'source'} or not isinstance(body.get('source'), dict):
        raise problem(422, 'INVALID_SUGGESTION', '仅接受卡片类型与公开/合成来源')
    # Validate untrusted source fields before slicing or indexing them.
    probe = dict(kind=body['kind'], source=body['source'], title='来源待核查', summary='待核查',
                 body='待核查', tags=['待审'], applicability=LIMITATION)
    validate_content(probe)
    if os.environ.get('MCIS_KNOWLEDGE_SUGGESTION_PROVIDER', PROVIDER) != PROVIDER:
        raise problem(503, 'SUGGESTIONS_UNAVAILABLE', '模板整理未启用；没有调用模型或回退服务')
    source = copy.deepcopy(body['source'])
    content = dict(kind=body['kind'], source=source, title=source['title'][:160],
                   summary=source['excerpt'][:600], body=source['excerpt'],
                   tags=['合成待审' if source['type'] == 'Synthetic' else '公开待审'], applicability=LIMITATION)
    # Whitespace-only prefixes remain readable while keeping the original excerpt intact.
    if not content['summary'].strip(): content['summary'] = '摘录开头为空白，请人工填写摘要。'
    if not content['title'].strip(): content['title'] = '来源标题开头为空白，请人工填写标题。'
    validate_content(content)
    return dict(profile=PROFILE, provider=PROVIDER, modelUsed=False, persisted=False,
                reviewRequired=True, inputDigest=digest(body), content=content, warnings=[WARNING])
