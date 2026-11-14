"""Independent check that raw-span fixture data actually reached SQLite."""
from .test_agents_w20 import interview, RECORD
from .conftest import CASE
from mcis_service.db import get_doc
from mcis_service.interviews.models import InterviewRow


def test_fixture_original_turn_is_persisted_not_only_locally_assumed(client, interview):
    with client.app.state.db.session() as session:
        stored = get_doc(session, InterviewRow, CASE, RECORD)
    assert len(stored['turns']) == len(interview['turns']) == 1
    for key in ('round', 'question', 'answer', 'sensitiveFragments'):
        assert stored['turns'][0][key] == interview['turns'][0][key]
    assert '😀' in stored['turns'][0]['answer']
    assert stored['statements'] == []
