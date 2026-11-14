import pytest
from .conftest import C, H, CASE
from mcis_service.db import put_doc, get_doc
from mcis_service.timeline.models import TimelineEventRow


def add(client, **kw):
    return client.post(C+'/timeline/events', headers=H(), json={
        'timeSec': -1, 'endTimeSec': 0, 'title': '边界测试（虚构）',
        'kind': 'Observation', 'sourceLabel': '测试来源（虚构）',
        'presumptive': True, 'confirmed': False, 'evidenceIds': ['EV-001'], **kw})


def test_zero_endpoint_included_preserves_sources_and_draft(client):
    r = add(client); assert r.status_code == 201
    ev = r.json()
    assert ev['utc'] == '2026-05-18T06:14:59Z'
    rows = client.get(C+'/timeline', params={'fromSec': 0, 'toSec': 0}).json()['events']
    assert ev in rows
    assert ev not in client.get(C+'/timeline', params={'fromSec': 1e-7}).json()['events']
    assert ev not in client.get(C+'/timeline', params={'includeDrafts': False}).json()['events']
    assert ev['presumptive'] and ev['confirmed'] is False and ev['evidenceIds']==['EV-001']


@pytest.mark.parametrize('value', [None, True, '1', {}, [], 1e100, 10**400])
def test_invalid_start_no_write(client, value):
    before = client.get(C+'/timeline').json()
    assert add(client, timeSec=value, endTimeSec=None).status_code == 422
    assert client.get(C+'/timeline').json() == before


@pytest.mark.parametrize('end', [-2, True, '0', {}, [], 1e100, 10**400])
def test_invalid_end(client, end):
    assert add(client, endTimeSec=end).status_code == 422


@pytest.mark.parametrize('params', [{'fromSec': 'nan'}, {'toSec': 'inf'}, {'fromSec': '-inf'}, {'fromSec': 2, 'toSec': 1}])
def test_invalid_window(client, params):
    assert client.get(C+'/timeline', params=params).status_code == 422


@pytest.mark.parametrize('end', [None, -1])
def test_null_or_equal_end_is_point(client, end):
    ev = add(client, endTimeSec=end).json()
    assert ev in client.get(C+'/timeline', params={'fromSec': -1, 'toSec': -1}).json()['events']
    assert ev not in client.get(C+'/timeline', params={'toSec': -1.0000001}).json()['events']


def test_no_repair_of_historical_reversed_interval(client, app):
    old = {'eventId':'TE-9999','caseId':CASE,'timeSec':5,'endTimeSec':3,'utc':'2026-05-18T06:15:05Z','title':'历史测试（虚构）','kind':'Observation'}
    with app.state.db.session() as s:
        put_doc(s, TimelineEventRow, CASE, old['eventId'], old)
    assert old in client.get(C+'/timeline').json()['events']
    with app.state.db.session() as s:
        assert get_doc(s, TimelineEventRow, CASE, old['eventId'])==old
