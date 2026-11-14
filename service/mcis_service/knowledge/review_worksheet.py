"""Internal human review worksheet. It is not a review decision or publication."""
from __future__ import annotations
import copy
import json
import re

PROFILE = 'MCIS-KNOWLEDGE-REVIEW-WORKSHEET-1'
CHECKS = (
    ('source_identity', '核实发布者与来源身份', ('source.title', 'source.url'), '公开分类或链接本身不证明来源真实或权威。'),
    ('source_locator', '核对页段定位与原文摘录', ('source.locator', 'source.excerpt'), '回到原件核对；页码定位存在不代表已核查。'),
    ('claim_support', '核对结论是否得到摘录支持', ('summary', 'body', 'source.excerpt'), '区分原文事实、作者判断与整理者推断，保留反证。'),
    ('applicability', '核对适用条件和局限', ('kind', 'applicability', 'tags'), '相似案例或方法不自动适用于本案。'),
    ('use_rights', '核实使用权与使用范围', ('source.rightsNote',), '公开可读不等于允许任意再发布或训练。'),
    ('release_scope', '确认公开范围与隐私风险', ('title', 'summary', 'body', 'source'), '发布前逐项核对内容和受众；不得仅凭Public标签发布。'),
)

def build(body):
    from .router import canonical, digest, validate_content
    from ..common.context import problem
    canonical(body)
    if type(body) is not dict or set(body) != {'content', 'expectedDigest'}:
        raise problem(422, 'INVALID_WORKSHEET', '仅接受内容和期望版本')
    expected = body['expectedDigest']
    if type(expected) is not str or not re.fullmatch('[a-f0-9]{64}', expected):
        raise problem(422, 'INVALID_WORKSHEET', '期望版本须为SHA256')
    validate_content(body['content'])
    actual = digest(body['content'])
    if actual != expected:
        raise problem(409, 'VERSION_CHANGED', '内容版本改变，须重新生成审核工作单')
    return {
        'profile': PROFILE,
        'contentDigest': actual,
        'content': copy.deepcopy(body['content']),
        'sourceClassification': body['content']['source']['type'],
        'checks': [dict(id=key, title=title, contentPaths=list(paths),
                        guidance=guidance, status='pending')
                   for key, title, paths, guidance in CHECKS],
        'requiredReleaseApprovals': [
            dict(field=field, status='pending')
            for field in ('sourceVerified', 'rightsVerified', 'releaseApproved')],
        'reviewRequired': True, 'approvalGranted': False, 'persisted': False,
        'networkUsed': False, 'modelUsed': False,
        'distribution': 'internal_review_only',
        'warning': '这是待填写审核工作单，不是审核记录或批准凭证。导出不发布、不修改卡片；必须经现有权限和版本校验完成正式审核。合成样本不得作为真实事故证据。',
    }

def export_json(body):
    """JSON download text; escape HTML metacharacters, never render source HTML."""
    value = json.dumps(build(body), ensure_ascii=True, sort_keys=True,
                       separators=(',', ':'), allow_nan=False)
    return value.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026') + '\n'
