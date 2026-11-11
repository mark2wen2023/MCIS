"""W16.1 GISIS 映射裁定回归；全部采用内存合成数据，不读取真实报告。"""
from copy import deepcopy
import csv
import io
import json

import pytest

from mcis_service.common import contracts
from mcis_service.reports.gisis import build_gisis, serialize_gisis, validate_gisis
from mcis_service.reports.templates import GISIS_FIELDS, get_template


LOCATION_CATEGORIES = [
    'At berth', 'Anchorage', 'Port', 'Port approach', 'Inland waters', 'Canal',
    'River', 'Archipelagos', 'Coastal waters', 'Open sea', 'Unknown',
    'Strait/channel', 'Traffic separation scheme', 'Offshore installation',
]
SEVERITIES = ['Very serious marine casualty', 'Marine casualty', 'Marine incident']


def fields(case=None, vessels=None):
    return {f['id']: f for f in build_gisis(
        {'caseId': 'SYNTHETIC', 'isFictionalDemo': True, **(case or {})}, vessels or [])['fields']}


def test_every_gisis_definition_has_circular_mapping_and_correct_local_requiredness():
    definitions = {f['id']: f for f in GISIS_FIELDS}
    expected = {
        'investigatingState': (True, 'partial', '附录1·一般信息 .1*'),
        'numberOfShips': (True, 'exact', '附录1·一般信息 .2*'),
        'incidentTimeUtc': (True, 'partial', '附录1·一般事故数据 .2* / .3*'),
        'latitude': (True, 'exact', '附录1·一般事故数据 .4*'),
        'longitude': (True, 'exact', '附录1·一般事故数据 .5*'),
        'locationCategory': (True, 'exact', '附录1·一般事故数据 .6*'),
        'eventType': (True, 'partial', '附录1·一般事故数据 .7*'),
        'severity': (True, 'partial', '附录1·一般事故数据 .8*'),
        'imoNumber': (True, 'exact', '附录2 1.1*'),
        'name': (True, 'exact', '附录2 1.2*'),
        'flagState': (True, 'exact', '附录2 1.5*'),
        'vesselType': (True, 'partial', '附录2 1.6*'),
        'grossTonnage': (False, 'exact', '附录2 1.7'),
        'deaths': (False, 'partial', '附录2 4.1–4.3'),
        'missingPersons': (False, 'partial', '附录2 4.1–4.3'),
        'injuries': (False, 'partial', '附录2 4.4–4.6'),
        'shipLoss': (False, 'partial', '附录2 4.7'),
        'pollution': (False, 'partial', '附录2 4.12–4.15'),
        'pollutionDetails': (False, 'partial', '附录2 4.11–4.15'),
        'reportStatus': (False, 'none', '—'),
    }
    assert set(definitions) == set(expected)
    for field_id, (required, status, reference) in expected.items():
        definition = definitions[field_id]
        assert definition['required'] is required
        assert definition['mappingStatus'] == status
        assert reference in definition['gisisRef']
        assert definition['mappingNote']
    for field_id in ('investigatingState', 'incidentTimeUtc', 'eventType', 'severity', 'vesselType', 'injuries'):
        assert '待核' in definitions[field_id]['mappingNote']


def test_new_required_fields_use_only_registered_ships_and_explicit_location_category():
    projected = fields({'incidentLocation': {'description': 'At berth in a port'}},
                       [{'vesselId': 'lily'}, {'vesselId': 'mary'}])
    assert projected['numberOfShips']['value'] == 2
    assert not projected['numberOfShips']['missing']
    assert projected['locationCategory']['value'] is None
    assert projected['locationCategory']['missing']
    assert projected['locationCategory']['rules']['enum'] == LOCATION_CATEGORIES
    assert projected['locationCategory']['sourceRefs'] == ['case.incidentLocation.locationCategory']
    assert fields()['numberOfShips']['missing']
    assert fields()['numberOfShips']['value'] is None
    explicit = fields({'incidentLocation': {'locationCategory': 'River'}})
    assert explicit['locationCategory']['value'] == 'River'
    assert not explicit['locationCategory']['missing']


@pytest.mark.parametrize('grade, expected', [
    ('VerySerious', 'Very serious marine casualty'),
    ('Very serious', 'Very serious marine casualty'),
    ('MarineIncident', 'Marine incident'), ('Marine incident', 'Marine incident'),
    ('Serious', None), ('LessSerious', None), ('Less serious', None),
    ('Marine casualty', None), ('unknown-grade', None), (None, None),
])
def test_severity_only_maps_confirmed_local_grades(grade, expected):
    severity = fields({'accidentGrade': grade})['severity']
    assert severity['rules']['enum'] == SEVERITIES
    assert severity['value'] == expected
    assert severity['missing'] is (expected is None)
    if expected is None:
        assert '本地等级与 Table 5 对应待核' in severity['mappingNote']


def test_projection_and_exports_preserve_mapping_metadata_and_schema():
    doc = build_gisis({'caseId': 'SYNTHETIC', 'isFictionalDemo': True}, [{'vesselId': 'lily'}])
    for field in doc['fields']:
        assert not contracts.errors('report#/$defs/gisisField', field)
        assert all(key in field for key in ('gisisRef', 'mappingStatus', 'mappingNote'))
    assert not contracts.errors('report#/$defs/gisis', doc)
    invalid = deepcopy(doc['fields'][0])
    invalid['mappingStatus'] = 'invented'
    assert contracts.errors('report#/$defs/gisisField', invalid)
    assert json.loads(serialize_gisis(doc, 'json')) == doc
    csv_rows = list(csv.DictReader(io.StringIO(serialize_gisis(doc, 'csv').decode('utf-8-sig'))))
    assert csv_rows[0]['gisisRef'] == doc['fields'][0]['gisisRef']
    assert csv_rows[0]['mappingStatus'] == doc['fields'][0]['mappingStatus']
    assert csv_rows[0]['mappingNote'] == doc['fields'][0]['mappingNote']


def test_optional_circular_fields_do_not_emit_required_errors_and_enums_are_checked():
    doc = build_gisis({'caseId': 'SYNTHETIC', 'isFictionalDemo': True}, [])
    validation = validate_gisis(doc, {'locationCategory': 'Imagined area', 'severity': 'Serious'})
    errors = {(e['fieldId'], e['code']) for e in validation['errors']}
    assert ('locationCategory', 'field_enum') in errors
    assert ('severity', 'field_enum') in errors
    optional = {f['id'] for f in doc['fields'] if not f['required']}
    assert {'deaths', 'missingPersons', 'injuries', 'pollution', 'pollutionDetails', 'shipLoss', 'reportStatus'} <= optional
    assert all(not field_id.endswith('.grossTonnage') and field_id not in optional
               for field_id, code in errors if code == 'field_required')


def test_cn_msa_chapters_keep_pending_ruling_marker_without_claiming_real_titles():
    template = get_template('cn-msa')
    assert any(ref.get('pendingRuling') == '章节标题待裁定落实' for ref in template['standardRefs'])
    assert template['sections'][0]['titleZh'] == '事故概况'
    assert not any('pendingRuling' in ref for tid in ('imo-cic', 'maib')
                   for ref in get_template(tid)['standardRefs'])
