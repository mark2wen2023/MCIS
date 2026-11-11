"""Current response wording must not mutate the frozen analysis source."""
import copy
import hashlib

from mcis_service.analysis import router


def test_imported_yangze_note_keeps_all_numbers_sources_and_seed_bytes(client):
    before_bytes = router.SEED.read_bytes()
    before, digest = router.load_seed()
    snapshot = copy.deepcopy(before)
    source = next(c for c in before['cases'] if c['key'] == 'yangze22')
    response = client.get('/api/v1/cases/' + source['caseId'] + '/analysis')
    assert response.status_code == 200
    body = response.json()
    assert '未接入服务数据库' not in ''.join(body['notes'])
    assert 'W14 S0 报告航迹重建' in ''.join(body['notes'])
    assert '入库状态以案件管理服务为准' in ''.join(body['notes'])
    assert {k: v for k, v in body.items() if k not in ('meta', 'notes')} == {k: v for k, v in source.items() if k != 'notes'}
    assert body['notes'][1:] == source['notes'][1:]
    assert router.load_seed()[0] == snapshot
    assert router.SEED.read_bytes() == before_bytes
    assert hashlib.sha256(before_bytes).hexdigest() == digest == body['meta']['seedSha256']
