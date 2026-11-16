"""New pure synthetic claims only: no files, databases, workers or refusal probes."""
from copy import deepcopy
import hashlib
from research.audio_completion_manifest.protocol import canonical, inspect


def fixture():
    members = [{'path': p, 'kind': 'file', 'size': 3, 'sha256': 'a'*64}
               for p in ('source.wav', 'raw.json', 'worker.log')]
    members.append({'path': 'home', 'kind': 'directory', 'size': 0, 'sha256': None})
    m = dict(schema='audio-job-completion/v1', caseId='synthetic-case', taskId='synthetic-task',
             generationId='synthetic-generation', auditId='synthetic-audit', members=members)
    c = {k: m[k] for k in ('caseId', 'taskId', 'generationId', 'auditId')}
    c.update(registration='new-protocol', exit='successful', writers='confirmed-closed', commit='confirmed',
             manifestSha256=hashlib.sha256(canonical(m)).hexdigest(), members=deepcopy(members))
    return m, c


def test_complete_claims_never_grant_actions():
    m, c = fixture(); before = deepcopy((m, c)); result = inspect(m, c)
    assert result['consistent_claims'] is True
    assert not any(result[k] for k in ('export_allowed','restore_ready','retry_allowed','delete_allowed','historical_proof'))
    assert (m, c) == before


def test_legacy_claims_remain_unknown():
    m, c = fixture(); c['registration'] = 'legacy'
    assert inspect(m, c)['consistent_claims'] is False


def test_unknown_exit_and_unclosed_writers_block():
    for key, value in [('exit','unknown'), ('exit','failed'), ('writers','unknown'), ('writers','running')]:
        m, c = fixture(); c[key] = value
        assert inspect(m, c)['consistent_claims'] is False


def test_unknown_or_pending_commit_blocks():
    for value in ('unknown', 'pending', 'rolled-back'):
        m, c = fixture(); c['commit'] = value
        assert inspect(m, c)['consistent_claims'] is False


def test_missing_and_extra_members_block():
    m, c = fixture(); c['members'].pop()
    assert inspect(m, c)['consistent_claims'] is False
    m, c = fixture(); c['members'].append({'path':'unexpected'})
    assert inspect(m, c)['consistent_claims'] is False


def test_task_and_audit_binding_must_match():
    for key in ('caseId','taskId','generationId','auditId'):
        m, c = fixture(); c[key] = 'different-synthetic-binding'
        assert inspect(m, c)['consistent_claims'] is False


def test_digest_and_size_must_match_recorded_claims():
    m, c = fixture(); c['members'][0]['size'] += 1
    assert inspect(m, c)['consistent_claims'] is False
    m, c = fixture(); c['manifestSha256'] = 'b'*64
    assert inspect(m, c)['consistent_claims'] is False


def test_incomplete_member_declaration_blocks():
    for field, value in [('size',None), ('sha256',None), ('kind','unknown')]:
        m, c = fixture(); m['members'][0][field] = value
        assert inspect(m, c)['consistent_claims'] is False
