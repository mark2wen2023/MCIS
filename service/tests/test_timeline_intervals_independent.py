"""Independent local API checks; synthetic fixtures, no model invocation."""
import pytest
from .conftest import C, CASE, H
from mcis_service.db import get_doc, put_doc
from mcis_service.cases.models import CaseRow
from mcis_service.redaction.models import AccessPolicyRow


def post(client, start, end=None):
    return client.post(C + '/timeline/events', headers=H(), json={
        'timeSec': start, 'endTimeSec': end, 'title': '独立边界测试（虚构）', 'kind': 'Observation'})


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-Infinity'])
def test_nonfinite_json_no_event_or_audit_write(client, value):
    before = client.get(C+'/timeline').json()
    audit = client.get(C+'/audit', headers=H()).json()
    response = client.post(C+'/timeline/events', headers={**H(), 'Content-Type':'application/json'},
        content='{"timeSec":'+value+',"title":"synthetic","kind":"Observation"}')
    assert response.status_code == 422
    assert client.get(C+'/timeline').json() == before
    assert client.get(C+'/audit', headers=H()).json() == audit


def test_epoch_offset_not_display_timezone_drives_utc(client, app):
    with app.state.db.session() as s:
        case = get_doc(s, CaseRow, CASE, CASE)
        case['caseEpochUtc'] = '2026-05-18T14:15:00+08:00'
        case['displayTimeZoneOffsetMinutes'] = -300
        put_doc(s, CaseRow, CASE, CASE, case)
    result = post(client, -0.5, 0.25)
    assert result.status_code == 201
    assert result.json()['utc'] == '2026-05-18T06:14:59.500Z'
    assert result.json()['timeSec'] == -0.5
    assert result.json()['endTimeSec'] == 0.25
    assert result.json() in client.get(C+'/timeline', params={'fromSec':0.25,'toSec':0.25}).json()['events']


def test_permission_precedes_range_validation_and_readonly_stays_readonly(client, app):
    assert client.post(C+'/timeline/events', headers=H('ExternalExpert'), json={
        'timeSec':10,'endTimeSec':-10,'kind':'Observation','title':'synthetic'}).status_code == 403
    with app.state.db.session() as s:
        policy = get_doc(s, AccessPolicyRow, CASE, 'policy')
        policy['matrix']['Investigator']['timeline'] = 'Deny'
        put_doc(s, AccessPolicyRow, CASE, 'policy', policy)
    assert client.get(C+'/timeline', headers=H(), params={'fromSec':'nan'}).status_code == 403
    assert post(client, 0, 0).status_code == 403


@pytest.mark.parametrize('value', [-(10**400), 2**63-1, -(2**63)])
def test_extreme_integer_no_write(client, value):
    before = client.get(C+'/timeline').json()
    assert post(client, value, None).status_code == 422
    assert client.get(C+'/timeline').json() == before


def test_finite_query_outside_datetime_range_is_valid_numeric_filter(client):
    response = client.get(C+'/timeline', params={'fromSec':1e100,'toSec':1e101})
    assert response.status_code == 200
    assert response.json()['events'] == []
