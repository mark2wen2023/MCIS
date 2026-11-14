"""Bounded exact-match candidate inspection; no semantic inference or writes."""
import copy
import re
from sqlalchemy import select
from ..common.context import problem
from .models import KnowledgeCardRow

SCAN_LIMIT = 1000
RESULT_LIMIT = 50
PROFILE = 'MCIS-KNOWLEDGE-DUPLICATE-PREVIEW-1'


def source_key(content):
    source = content['source']
    return (source['type'], source.get('url'), source['locator'], source['excerpt'])


def preview(body, ctx):
    from .router import canonical, digest, internal, validate_content
    internal(ctx)
    validate_content(body)
    expected = canonical(body)
    key = source_key(body)
    matches = []
    with ctx.db.session() as session:
        rows = list(session.scalars(select(KnowledgeCardRow).order_by(
            KnowledgeCardRow.id.desc()).limit(SCAN_LIMIT + 1)))
        incomplete = len(rows) > SCAN_LIMIT
        scanned = min(len(rows), SCAN_LIMIT)
        for row in rows[:SCAN_LIMIT]:
            try:
                doc = row.doc
                content = doc['content']
                validate_content(content)
                if (not isinstance(row.card_id, str) or not re.fullmatch(r'KC-[a-f0-9]{32}', row.card_id)
                    or row.card_id != doc['cardId'] or row.status != doc['status']
                    or row.kind != content['kind']
                    or row.status not in ('Candidate', 'Published', 'Rejected', 'Withdrawn')
                    or digest(content) != doc['contentDigest']):
                    raise ValueError('stored binding')
            except Exception:
                # No partial result or raw stored input in the error response.
                raise problem(409, 'INVALID_STORED_CARD', '知识卡数据绑定不一致，请修复后重试') from None
            reasons = []
            if canonical(content) == expected:
                reasons.append('exact_content')
            if source_key(content) == key:
                reasons.append('same_source_excerpt')
            if reasons:
                matches.append(dict(cardId=row.card_id, status=row.status, kind=row.kind,
                                    title=content['title'], contentDigest=doc['contentDigest'], reasons=reasons))
    return dict(profile=PROFILE, inputDigest=digest(body), persisted=False, modelUsed=False,
                reviewRequired=True, matches=copy.deepcopy(matches[:RESULT_LIMIT]), scanned=scanned,
                scanIncomplete=incomplete, resultsTruncated=len(matches) > RESULT_LIMIT,
                warning='仅字面匹配提示，不代表同一事实或自动去重；无匹配不证明唯一。来源真实性、使用权和发布仍须人工审核。')
