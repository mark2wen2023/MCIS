"""Existing model facts for the source-binding design, NOT an implemented Skill."""
from mcis_service.evidence import service
from mcis_service.db import get_doc
from mcis_service.evidence.models import EvidenceRow
from .conftest import CASE


def test_custody_change_not_registration_is_current_version(client):
    with client.app.state.db.session() as s:
        item = get_doc(s, EvidenceRow, CASE, 'EV-003')
        before = item['sha256']
        replacement = 'b' * 64 if before != 'b' * 64 else 'c' * 64
        service.append_custody(s, case_id=CASE, evidence_id='EV-003', kind='Change',
            operator='虚构版本核验', role='LeadInvestigator', sha256=replacement,
            previous_sha256=before, detail='仅测试登记版本，不写原件')
        state = service.derive(item, service.custody_events(s, CASE, 'EV-003'))
        assert item['sha256'] == before
        assert state['currentSha256'] == replacement
        assert state['status'] == 'Unverified'
        assert get_doc(s, EvidenceRow, CASE, 'EV-003')['sha256'] == before


def test_clear_review_flag_does_not_verify_hash_or_approve_observation(client):
    with client.app.state.db.session() as s:
        item = get_doc(s, EvidenceRow, CASE, 'EV-003')
        service.append_custody(s, case_id=CASE, evidence_id='EV-003', kind='Change',
            operator='虚构版本核验', role='LeadInvestigator', sha256='d'*64,
            previous_sha256=item['sha256'], detail='模拟后续版本')
        for flag in (True, False):
            service.append_custody(s, case_id=CASE, evidence_id='EV-003', kind='Review',
                operator='虚构版本核验', role='LeadInvestigator', sha256='d'*64,
                detail='标记，不是事实批准', review=flag)
        state = service.derive(item, service.custody_events(s, CASE, 'EV-003'))
        assert state['needsReview'] is False
        assert state['status'] == 'Unverified'
        assert 'observationApproval' not in state


def test_access_activity_not_content_change(client):
    with client.app.state.db.session() as s:
        item = get_doc(s, EvidenceRow, CASE, 'EV-003')
        before = service.derive(item, service.custody_events(s, CASE, 'EV-003'))
        service.append_custody(s, case_id=CASE, evidence_id='EV-003', kind='Access',
            operator='虚构版本核验', role='LeadInvestigator', sha256=before['currentSha256'], detail='查看')
        after = service.derive(item, service.custody_events(s, CASE, 'EV-003'))
        assert after['currentSha256'] == before['currentSha256']
        assert after['status'] == before['status']
        assert after['accessCount'] == before['accessCount'] + 1
