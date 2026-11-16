"""Ordinary synthetic storage-state tests; no model/core or security probes."""
import base64
import hashlib
import io
import json
import zipfile

import pytest
from mcis_service.db import put_doc
from mcis_service.recommendations.models import ConsultationRoundRow, RecommendationRow
from mcis_service.timeline.models import TimelineEventRow, ConflictRow
from mcis_service.agents.models import AgentDraftRow
from mcis_service.colreg.models import ColregAnalysisRow
from mcis_service.sim.models import SimCommandRow
from .test_working_record_archive import client_at, checked, snapshot, CID, ROOT, HEAD

STATES = [(ConsultationRoundRow, '1'), (TimelineEventRow, 'event'),
          (RecommendationRow, 'rec'), (ConflictRow, 'conflict'),
          (AgentDraftRow, 'draft'), (ColregAnalysisRow, 'current'),
          (ColregAnalysisRow, 'inputs'), (SimCommandRow, 'command')]


def store(c, model, key, case_id=CID):
    # Deliberately storage fixtures: not a claim that any model/core executed.
    doc = {'caseId': case_id, 'syntheticFixture': True}
    with c.app.state.db.session() as s:
        if model is SimCommandRow:
            s.add(model(case_id=case_id, seq=1, doc=doc))
        else:
            put_doc(s, model, case_id, key, doc)


def files(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob('*') if p.is_file() and p.suffix not in ('.db', '.sqlite')
            and not p.name.endswith(('-wal', '-shm'))}


@pytest.mark.parametrize('model,key', STATES, ids=[m.__tablename__+'-'+k for m,k in STATES])
@pytest.mark.parametrize('with_timeline', [False, True])
def test_standalone_state_refuses_without_partial_export(tmp_path, model, key, with_timeline):
    with client_at(tmp_path/'source', True) as c:
        store(c, model, key)
        if with_timeline:
            store(c, TimelineEventRow, 'extra-event')
        before = snapshot(c)
        before_files = files(tmp_path/'source')
        response = c.get(ROOT+'/export', headers=HEAD)
        assert response.status_code == 409
        assert response.json()['code'] == 'ARCHIVE_RESTORE_UNSUPPORTED'
        assert not response.content.startswith(b'PK')
        assert snapshot(c) == before
        assert files(tmp_path/'source') == before_files


@pytest.mark.parametrize('other_state', [False, True])
def test_supported_empty_case_roundtrip_and_other_case_state(tmp_path, other_state):
    with client_at(tmp_path/'a', True) as a:
        if other_state:
            store(a, ColregAnalysisRow, 'inputs', 'OTHER-SYNTHETIC')
        raw = checked(a, 'get', ROOT+'/export').content
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            assert json.loads(z.read('manifest.json'))['packageVersion'] == '1.0.0'
        with client_at(tmp_path/'b') as b:
            body = {'contentBase64': base64.b64encode(raw).decode()}
            checked(b, 'post', '/api/v1/packages/intakes:preview', body)
            checked(b, 'post', '/api/v1/packages/intakes:commit',
                    {**body, 'confirmed': True, 'sourceSha256': hashlib.sha256(raw).hexdigest()})
            again = checked(b, 'get', ROOT+'/export').content
            with client_at(tmp_path/'c') as c:
                checked(c, 'post', '/api/v1/packages/intakes:commit',
                        {'contentBase64': base64.b64encode(again).decode(), 'confirmed': True,
                         'sourceSha256': hashlib.sha256(again).hexdigest()})


@pytest.mark.parametrize('path,body', [
    ('/recommendations', {'title': 'Synthetic', 'addressee': 'Synthetic',
                         'causeNodeIds': ['SYN'], 'dueUtc': '2099-01-01T00:00:00Z'}),
    ('/conflicts', {'summary': 'Synthetic conflict',
                    'a': {'sourceLabel': 'Synthetic A', 'valueText': 'A'},
                    'b': {'sourceLabel': 'Synthetic B', 'valueText': 'B'}}),
    ('/agents/drafts', {'agent': 'timeline', 'kind': 'timeline_anchor',
                        'payload': {'title': 'Synthetic, no model executed'},
                        'citations': [{'quote': 'Synthetic quote'}]}),
    ('/sim/commands', {'type': 'pause', 'reason': 'Synthetic; no Unity connection'}),
])
def test_api_created_state_also_refuses(tmp_path, path, body):
    with client_at(tmp_path/'api', True) as c:
        checked(c, 'post', ROOT+path, body, status=201)
        before = snapshot(c)
        response = checked(c, 'get', ROOT+'/export', status=409)
        assert response.json()['code'] == 'ARCHIVE_RESTORE_UNSUPPORTED'
        assert not response.content.startswith(b'PK')
        assert snapshot(c) == before
