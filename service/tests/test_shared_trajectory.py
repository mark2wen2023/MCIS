"""Synthetic contract tests only; no real AIS, OCR, LLM, Unity or browser."""
import copy
import json
from pathlib import Path
from unittest.mock import patch
import socket

import pytest
from mcis_service.trajectory_exchange import validate_trajectory, TrajectoryError

@pytest.fixture
def doc():
    return json.loads((Path(__file__).parent/'fixtures/shared_trajectory_synthetic.json').read_text())

def test_fixture_no_mutation_or_network(doc):
    before=copy.deepcopy(doc)
    with patch.object(socket,'socket',side_effect=AssertionError('network forbidden')):
        result=validate_trajectory(doc)
    assert doc==before
    assert result['canReplaySynchronously'] and result['requiresHumanReview']
    assert not result['authenticityVerified'] and not result['visualOverlapIsCollisionEvidence']
    assert not result['orientation'][0]['headingAvailable']
    assert not result['orientation'][0]['courseUsedAsHeading']

@pytest.mark.parametrize('field,value',[('latDeg',90.0000001),('latDeg',-90.0000001),('lonDeg',180.0000001),('lonDeg',-180.0000001),('latDeg',float('nan')),('lonDeg',True)])
def test_invalid_coordinates(doc,field,value):
    doc['points'][0]['position']['value'][field]=value
    with pytest.raises(TrajectoryError):validate_trajectory(doc)

@pytest.mark.parametrize('field,value',[('latDeg',90),('latDeg',-90),('lonDeg',180),('lonDeg',-180)])
def test_coordinate_boundaries(doc,field,value):
    doc['points'][0]['position']['value'][field]=value
    assert validate_trajectory(doc)['canReplaySynchronously']

@pytest.mark.parametrize('stamp',['2026-02-30T00:00:00Z','2026-01-01T00:00:00+01:99','2026-01-01T00:00:00','2026-01-01T00:00:60Z'])
def test_invalid_utc(doc,stamp):
    doc['points'][0]['time']['sourceUtc']=stamp
    with pytest.raises(TrajectoryError):validate_trajectory(doc)

@pytest.mark.parametrize('status',['unresolved','conflict'])
def test_unaligned_preserved_and_blocked(doc,status):
    t=doc['points'][0]['time'];t.update(status=status,sourceRecordTime='original device clock unknown zone',sourceUtc=None,alignedUtc=None,correctionSeconds=None)
    before=copy.deepcopy(doc)
    r=validate_trajectory(doc)
    assert not r['canReplaySynchronously'];assert doc==before
    assert r['issues'][0]['code']=='TIME_'+status.upper()

@pytest.mark.parametrize('stamp',['2026-01-01T00:00:00Z','2025-12-31T23:59:59Z'])
def test_duplicate_or_reverse_times_not_sorted(doc,stamp):
    doc['points'][1]['time'].update(sourceRecordTime=stamp,sourceUtc=stamp,alignedUtc=stamp)
    assert not validate_trajectory(doc)['canReplaySynchronously']
    assert doc['points'][1]['time']['alignedUtc']==stamp

def test_correction_requires_matching_basis_delta(doc):
    t=doc['points'][1]['time'];t.update(status='corrected',correctionSeconds=2,alignedUtc='2026-01-01T00:00:12Z',basis='Synthetic comparison clock +2 seconds')
    assert validate_trajectory(doc)['canReplaySynchronously']
    t['correctionSeconds']=3
    with pytest.raises(TrajectoryError):validate_trajectory(doc)

def test_unresolved_cannot_claim_aligned(doc):
    doc['points'][0]['time']['status']='unresolved'
    with pytest.raises(TrajectoryError):validate_trajectory(doc)

@pytest.mark.parametrize('kind',['recorded','calculated','interpolated','manual_assumption','schematic'])
def test_provenance_never_promoted(doc,kind):
    doc['points'][0]['courseDeg']['kind']=kind
    doc['points'][0]['courseDeg']['sourceIds']=['synthetic-manual']
    assert validate_trajectory(doc)['requiresHumanReview']
    assert doc['points'][0]['courseDeg']['kind']==kind

def test_unknown_source_rejected(doc):
    doc['points'][0]['headingDeg']['sourceIds']=['not-known']
    with pytest.raises(TrajectoryError):validate_trajectory(doc)

def test_sources_cannot_duplicate(doc):
    doc['sources'].append(copy.deepcopy(doc['sources'][0]))
    with pytest.raises(TrajectoryError):validate_trajectory(doc)

@pytest.mark.parametrize('angle',[-0.0000001,360,511,float('inf')])
def test_invalid_heading(doc,angle):
    doc['points'][1]['headingDeg']['value']=angle
    with pytest.raises(TrajectoryError):validate_trajectory(doc)

def test_missing_value_not_zero(doc):
    doc['points'][0]['headingDeg']['value']=0
    with pytest.raises(TrajectoryError):validate_trajectory(doc)

def test_display_scale_does_not_change_dimensions(doc):
    before=copy.deepcopy(doc['vessel'])
    assert validate_trajectory(doc)['canReplaySynchronously'];assert doc['vessel']==before
    doc['display']['purpose']='true_scale'
    with pytest.raises(TrajectoryError):validate_trajectory(doc)

def test_missing_position_blocks(doc):
    doc['points'][0]['position'].update(value=None,kind='missing')
    assert not validate_trajectory(doc)['canReplaySynchronously']

def test_gaps_not_interpolated(doc):
    doc['points'][1]['time'].update(sourceUtc='2026-01-01T00:01:00Z',alignedUtc='2026-01-01T00:01:00Z')
    r=validate_trajectory(doc)
    assert r['gaps']==[{'fromPointId':'p1','toPointId':'p2','seconds':60.0,'interpolate':False}]
    assert not r['continuousReplayAllowed'] and len(doc['points'])==2

def test_declared_missing_interval(doc):
    interval={'startUtc':'2026-01-01T00:00:01Z','endUtc':'2026-01-01T00:00:09Z','sourceIds':['synthetic-ais'],'reason':'Synthetic lost records'}
    doc['sampling']['missingIntervals']=[interval]
    assert not validate_trajectory(doc)['continuousReplayAllowed']
    interval['endUtc']=interval['startUtc']
    with pytest.raises(TrajectoryError):validate_trajectory(doc)

def test_unknown_identity_not_guessed(doc):
    doc['vessel']['identityStatus']='unresolved';doc['vessel']['identifiers']=[]
    assert not validate_trajectory(doc)['canReplaySynchronously']

@pytest.mark.parametrize('target',[('caseId',None),('extra','uncontracted')])
def test_schema_closed(doc,target):
    doc[target[0]]=target[1]
    with pytest.raises(TrajectoryError):validate_trajectory(doc)

def test_asserted_identity_needs_identifier(doc):
    doc['vessel']['identifiers']=[]
    with pytest.raises(TrajectoryError):validate_trajectory(doc)

def test_unknown_units_rejected(doc):
    doc['units']['speed']='m/s'
    with pytest.raises(TrajectoryError):validate_trajectory(doc)

def test_no_missing_basis(doc):
    doc['points'][0]['headingDeg']['basis']=''
    with pytest.raises(TrajectoryError):validate_trajectory(doc)

def test_duplicate_point_rejected(doc):
    doc['points'][1]['pointId']='p1'
    with pytest.raises(TrajectoryError):validate_trajectory(doc)

def test_schema_is_valid_and_no_external_refs():
    from mcis_service.trajectory_exchange.validation import SCHEMA
    from jsonschema import Draft202012Validator
    schema=json.loads(SCHEMA.read_text());Draft202012Validator.check_schema(schema)
    assert '$ref' not in json.dumps(schema)
