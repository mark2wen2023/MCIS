"""Exact Knowledge router, real SQLite + in-process HTTP, synthetic content only."""
import argparse
import sys, json, tempfile, hashlib
from pathlib import Path
from urllib.parse import quote
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--checkout', type=Path, default=Path(__file__).resolve().parents[2], help='Root containing the pinned service and contracts; never modified')
root = parser.parse_args().checkout.resolve()
pins = json.loads(Path(__file__).with_name('backend-pins.json').read_text())
for rel, pin in pins.items():
    b = (root / rel).read_bytes()
    if hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\x00' + b).hexdigest() != pin:
        raise SystemExit(f'W19 fixed source pin mismatch: {rel}')
if not __debug__:
    raise SystemExit('W19 acceptance requires Python assert checks enabled')
sys.dont_write_bytecode = True
sys.path.insert(0, str(root / 'service'))
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, func, inspect
from mcis_service.db import Base, Database
from mcis_service.knowledge.router import router
from mcis_service.knowledge.models import KnowledgeCardRow, KnowledgeAuditRow
from mcis_service.knowledge_archive.models import Archive, Epoch, Snapshot
sample = {'kind': 'Method', 'title': '合成方法卡：区分观测与推断', 'summary': '仅用于演示知识卡审核，不是真实案件结论。', 'body': '记录观测材料、列出不确定性，再单独说明推断过程。此内容仅为软件合成样本。', 'tags': ['合成示例', '来源核查'], 'applicability': '仅供软件流程测试，不是正式海事调查指引。', 'source': {'type': 'Synthetic', 'title': 'MCIS知识卡合成示例', 'locator': '演示段落1', 'excerpt': '列出不确定性，再单独说明推断过程。', 'rightsNote': '由本软件测试构造，不含真实个人或内网资料。'}}


def headers(role):
    return {'X-MCIS-Role': role, 'X-MCIS-Operator': quote('合成-' + role)}


def app(db):
    a = FastAPI()
    a.state.db = db
    a.include_router(router)
    return a


checks = []


def check(label, value):
    assert value, label
    checks.append(label)


query = '/api/v1/knowledge/cards?status=Published&q=' + quote('合成') + '&tag=' + quote('来源核查') + '&limit=20&offset=0'
with tempfile.TemporaryDirectory(prefix='mcis-w19-withdraw-') as directory:
    path = Path(directory) / 'only-knowledge.db'
    url = 'sqlite:///' + str(path)
    db = Database(url)
    try:
        Base.metadata.create_all(db.engine)
        check('only_five_knowledge_tables', set(inspect(db.engine).get_table_names()) == {'knowledge_cards', 'knowledge_audit', 'knowledge_archives', 'knowledge_audit_snapshot_epoch', 'knowledge_audit_snapshots'})
        with TestClient(app(db)) as c:
            r = c.post('/api/v1/knowledge/cards', json=sample, headers=headers('Investigator'))
            check('create_candidate', r.status_code == 201 and r.json()['status'] == 'Candidate')
            card = r.json()
            cid = card['cardId']
            digest = card['contentDigest']
            detail = '/api/v1/knowledge/cards/' + cid
            review = detail + '/review'
            check('candidate_external_hidden', c.get(detail, headers=headers('Public')).status_code == 404)
            publish = {'decision': 'Published', 'expectedDigest': digest, 'note': '纯合成验收发布', 'sourceVerified': True, 'rightsVerified': True, 'releaseApproved': True}
            check('investigator_cannot_publish', c.post(review, json=publish, headers=headers('Investigator')).status_code == 403)
            check('missing_release_approval_rejected', c.post(review, json={**publish, 'releaseApproved': False}, headers=headers('LeadInvestigator')).status_code == 422)
            with db.session() as s:
                check('denials_no_audit', s.scalar(select(func.count()).select_from(KnowledgeAuditRow)) == 1)
            r = c.post(review, json=publish, headers=headers('LeadInvestigator'))
            check('lead_publishes', r.status_code == 200 and r.json()['status'] == 'Published')
            roles = ['Public', 'AgentService', 'ExternalExpert', 'InterestedState']
            for role in roles:
                r = c.get(query, headers=headers(role))
                check(role + '_published_query', r.status_code == 200 and [x['cardId'] for x in r.json()['items']] == [cid])
                r = c.get(detail, headers=headers(role))
                check(role + '_published_detail_redacted', r.status_code == 200 and all((k not in r.json() for k in ['createdBy', 'reviewedBy', 'reviewNote', 'approvals'])))
            withdrawal = {'decision': 'Withdrawn', 'expectedDigest': digest, 'note': '纯合成验收撤回'}
            check('investigator_cannot_withdraw', c.post(review, json=withdrawal, headers=headers('Investigator')).status_code == 403)
            check('wrong_version_rejected', c.post(review, json={**withdrawal, 'expectedDigest': '0' * 64}, headers=headers('LeadInvestigator')).status_code == 409)
            r = c.post(review, json=withdrawal, headers=headers('LeadInvestigator'))
            check('lead_withdraws', r.status_code == 200 and r.json()['status'] == 'Withdrawn' and (r.json()['contentDigest'] == digest))
            for role in roles:
                r = c.get(query, headers=headers(role))
                check(role + '_same_query_empty', r.status_code == 200 and r.json()['items'] == [])
                check(role + '_withdrawn_detail_hidden', c.get(detail, headers=headers(role)).status_code == 404)
                check(role + '_internal_queue_denied', c.get('/api/v1/knowledge/cards?status=Withdrawn', headers=headers(role)).status_code == 403)
            check('repeat_withdraw_rejected', c.post(review, json=withdrawal, headers=headers('LeadInvestigator')).status_code == 409)
            check('external_audit_denied', c.get('/api/v1/knowledge/audit', headers=headers('Public')).status_code == 403)
            audit = c.get('/api/v1/knowledge/audit', headers=headers('Investigator')).json()
            check('exact_audit_actions', [e['action'] for e in audit] == ['knowledge.create', 'knowledge.published', 'knowledge.withdrawn'])
            check('actual_recorded_roles', [e['role'] for e in audit] == ['Investigator', 'LeadInvestigator', 'LeadInvestigator'])
            check('actual_recorded_operators', [e['operator'] for e in audit] == ['合成-Investigator', '合成-LeadInvestigator', '合成-LeadInvestigator'])
            check('audit_chain_valid', c.get('/api/v1/knowledge/audit:verify', headers=headers('Investigator')).json() == {'valid': True, 'count': 3})
        db.engine.dispose()
        db = Database(url)
        with TestClient(app(db)) as c:
            for role in roles:
                r = c.get(query, headers=headers(role))
                check(role + '_reopen_query_empty', r.status_code == 200 and r.json()['items'] == [])
                check(role + '_reopen_detail_hidden', c.get(detail, headers=headers(role)).status_code == 404)
            r = c.get(detail, headers=headers('Investigator'))
            check('internal_history_kept', r.status_code == 200 and r.json()['status'] == 'Withdrawn' and (r.json()['contentDigest'] == digest))
            check('audit_persists_without_extra_events', c.get('/api/v1/knowledge/audit', headers=headers('Investigator')).json() == audit)
        with db.session() as s:
            check('one_card_three_snapshots', s.scalar(select(func.count()).select_from(KnowledgeCardRow)) == 1 and s.scalar(select(func.count()).select_from(Snapshot)) == 3)
            check('no_archive_import', s.scalar(select(func.count()).select_from(Archive)) == 0)
    finally:
        db.engine.dispose()
check('temporary_directory_removed', not Path(directory).exists())
print(json.dumps({'passed': len(checks), 'checks': checks, 'source': '7ba7970ba4f77ebce11463d663e0f02a6c3f7928', 'identity_boundary': 'existing self-declared demo role headers; not production authentication', 'transport': 'real FastAPI TestClient in-process; no listener', 'model': False}, ensure_ascii=False))
