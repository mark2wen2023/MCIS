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
