"""Independent historical reproduction in memory; never changes implementation file."""
import inspect
from mcis_service.agents import router as agent_module
from .test_timeline_draft_target_permission import make_draft, set_timeline
from .conftest import C, H


def test_historical_missing_target_check_reproduces_in_memory(client, monkeypatch):
    source = inspect.getsource(agent_module._apply)
    line = '        require(ctx, s, case_id, "timeline", write=True)\n'
    assert source.count(line) == 1
    historical = source.replace(line, '')
    local = {}
    exec(compile(historical, '<historical-apply-probe>', 'exec'), agent_module.__dict__, local)
    monkeypatch.setattr(agent_module, '_apply', local['_apply'])
    draft = make_draft(client)
    before = client.get(C+'/timeline', headers=H()).json()['events']
    set_timeline(client, 'Investigator', 'ReadOnly')
    response = client.post(C+'/agents/drafts/'+draft+'/review', json={'decision':'Confirmed'}, headers=H())
    assert response.status_code == 200, response.text
    after = client.get(C+'/timeline', headers=H()).json()['events']
    assert len(after) == len(before)+1
    assert response.json()['status'] == 'Confirmed'
