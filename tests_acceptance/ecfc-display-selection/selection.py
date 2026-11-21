"""Synthetic display-selection experiment, not an ECFC contract or authorization.
No IO. Host supplies parsed graph and explicit test mapping; no production caller.
"""
from copy import deepcopy


def edge_key(envelope, edge_id):
    doc = envelope['document']
    edge = next((e for e in doc['draft']['edges'] if e['id'] == edge_id), None)
    if edge is None or envelope['sourceStatus'] != 'unchanged':
        return None
    return (envelope['caseId'], doc['revision'], doc['digest'], edge['id'], edge['from'], edge['to'])


def edge_display(envelope, edge_id, association, fragment):
    """Fixture-owned association only. Does not read/register/authorize evidence."""
    key = edge_key(envelope, edge_id)
    if key is None or association is None or tuple(association['graphKey']) != key:
        return None
    if (association['origin'] != 'synthetic_fixture' or fragment['origin'] != 'synthetic_fixture'
            or fragment['caseId'] != key[0] or fragment['version'] != association['fragmentVersion']
            or fragment['locator'] != association['locator']):
        return None
    # Only display fields: no graph digest, internal pin, file content or original IDs.
    return dict(label='连线独立出处（合成工装关联，非因果证明）', status='待审',
                sourceUtc=fragment['sourceUtc'], uncertaintySeconds=None,
                replayUtc=None, seekAvailable=False, eventVerified=False,
                locator=deepcopy(fragment['locator']), evidenceDirection='未判定',
                associationOrigin='synthetic_fixture')


def node_display(associated):
    if associated['status'] != 'associated_original_position':
        return None
    row = associated['record']
    return dict(label=associated['label'], status='待审',
                sourceUtc=row['time']['sourceUtc'], displayUtc=row['time']['alignedUtc'],
                correctionSeconds=row['time']['correctionSeconds'], uncertaintySeconds=None,
                timeReview='未签核', locator=deepcopy(row['locator']),
                manualTimeSeconds=associated['timeSeconds'], isPresumptive=associated['isPresumptive'],
                eventVerified=False, seekAvailable=False)


class Selection:
    """Local generation guard only; ticket is not a credential or durable mapping."""
    def __init__(self):
        self._generation = 0
        self._key = None
        self._visible = None

    def select(self, envelope, edge_id):
        self._generation += 1
        self._key = edge_key(envelope, edge_id)
        self._visible = None
        return (self._generation, self._key)

    def finish(self, ticket, result):
        if self._key is None or ticket != (self._generation, self._key):
            return False
        self._visible = deepcopy(result)
        return True

    @property
    def visible(self):
        return deepcopy(self._visible)
