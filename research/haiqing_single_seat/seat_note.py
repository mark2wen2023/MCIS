"""Research-only exact-frame packet projection. No tool registration or dispatch.
frame/trusted_pins belong to the local host, never model/UI arguments. This is
not an authentication boundary; only the pinned synthetic exercise is supported.
"""
from copy import deepcopy

CASE = 'SYN-XREPO-001'
UTC = '2026-02-01T12:02:04.250Z'
GAP_POINTER = '/sampling/missingIntervals/1'
GAP = {'startUtc': '2026-02-01T12:02:01.000Z', 'endUtc': '2026-02-01T12:02:07.500Z'}
CLAIM = 'Evidence is insufficient to determine whether either vessel turned.'
LIMIT = 'This exact UTC evidence does not establish the maneuver.'
SPECS = (
    ('SYN-VESSEL-A', 'SYN-E-A', 'item_001', 'declared_gap', GAP_POINTER,
     'Vessel A has a declared evidence gap at the selected UTC.'),
    ('SYN-VESSEL-B', 'SYN-E-B', 'item_002', 'no_observation_at_time', None,
     'Vessel B has no exact observation at the selected UTC.'),
)

class ScopeError(ValueError):
    pass


def prepare(frame, *, trusted_pins):
    """Fixed host scope only; originals/pins never enter the review packet."""
    if not isinstance(frame, dict) or frame.get('caseId') != CASE or frame.get('alignedUtc') != UTC:
        raise ScopeError('case_or_time')
    vessels = frame.get('vessels')
    if not isinstance(vessels, (list, tuple)) or len(vessels) != 2 or not isinstance(trusted_pins, (list, tuple)) or len(trusted_pins) != 2:
        raise ScopeError('pair')
    items, local = [], {}
    for vessel, pin, (vid, eid, item_id, status, pointer, source) in zip(vessels, trusted_pins, SPECS, strict=True):
        locator = {'jsonPointer': pointer} if pointer else None
        if (not isinstance(vessel, dict) or not isinstance(pin, dict)
                or vessel.get('vesselId') != vid or pin.get('evidenceId') != eid
                or pin.get('caseId') != CASE or vessel.get('original') != pin
                or vessel.get('status') != status or vessel.get('locator') != locator
                or vessel.get('gap') != (GAP if pointer else None)
                or any(vessel.get(k) is not None for k in ('time', 'position', 'headingDeg', 'courseDeg'))):
            raise ScopeError('point_or_locator')
        items.append({'itemId': item_id, 'sourceText': source})
        local[item_id] = ({'original': deepcopy(pin), 'locator': locator} if locator else None)
    return {'items': items}, local


def handoff(host_validate, args, *, frame, trusted_pins):
    """Existing host shape check followed by this fixed exercise's literal rubric.
    Equality here is not general semantic detection, authentication or fact review.
    """
    packet, local = prepare(frame, trusted_pins=trusted_pins)
    reviews = host_validate(args, packet)
    for item, review in zip(packet['items'], reviews, strict=True):
        if (review['itemId'] != item['itemId'] or review['label'] != 'insufficient'
                or review['quote'] != item['sourceText'] or review['rationale'] != CLAIM
                or review['uncertainty'] != LIMIT):
            raise ScopeError('insufficient_only')
    return {'status': 'proposed_note_pending_human_review', 'caseId': CASE,
            'alignedUtc': UTC, 'text': CLAIM, 'items': deepcopy(reviews),
            'references': deepcopy(local), 'factActivated': False, 'saved': False}

# T100 is a separate test-only typed entry. No change to the T124 text entry.
T100_CONSUMER = 'ebe153b2753923b9b93c6d09281aad6f98a1d9d6'
T100_PRODUCER = '3b613a5bda111cdfd3d5a4177710a2a4c304dc08'

def bind_t100_test_receipt(trusted_pending, *, consumer_commit, producer_commit):
    """Trusted fixture host ONLY, immediately after pinned consumer.run succeeds.
    This factory is not authentication: callers must not expose it to model/UI input.
    The closure holds a private snapshot; no receipt storage or production dispatch.
    """
    if consumer_commit != T100_CONSUMER or producer_commit != T100_PRODUCER:
        raise ScopeError('t100_version')
    if (type(trusted_pending) is not dict
            or set(trusted_pending) != {'scope','caseId','alignedUtc','observations','reviewState','turnConclusion','causation','saved','sourceAuthenticityVerified'}
            or trusted_pending['scope'] != 'synthetic_registered_stdout_test_only'
            or trusted_pending['caseId'] != CASE
            or trusted_pending['alignedUtc'] != '2026-02-01T12:01:40.000Z'
            or trusted_pending['reviewState'] != 'pending'
            or trusted_pending['turnConclusion'] is not None
            or trusted_pending['causation'] is not None
            or trusted_pending['saved'] is not False
            or trusted_pending['sourceAuthenticityVerified'] is not False
            or type(trusted_pending['observations']) is not list
            or len(trusted_pending['observations']) != 2):
        raise ScopeError('t100_pending')
    # Full schema, exact source digests and independent registration checks belong
    # to pinned consume(); do not duplicate that parser here.
    snapshot = deepcopy(trusted_pending)
    def same(a, b):
        if type(a) is not type(b): return False
        if type(a) is dict:
            return a.keys() == b.keys() and all(same(a[k],b[k]) for k in a)
        if type(a) is list:
            return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
        return type(a) in (str,int,float,bool,type(None)) and a==b
    def accept(pending):
        if not same(pending, snapshot):
            raise ScopeError('t100_same_run_binding')
        return {'status':'proposed_note_pending_human_review',
                'caseId':snapshot['caseId'],'alignedUtc':snapshot['alignedUtc'],
                'observations':deepcopy(snapshot['observations']),
                'text':'Single-time heading records do not establish a turn or cause.',
                'turnConclusion':None,'causation':None,'factActivated':False,'saved':False}
    return accept
