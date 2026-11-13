"""Research-only direct temporal constraint checks, not evidence adjudication."""
from dataclasses import dataclass
from timeline import validate_events
from scoped import scoped_interval


@dataclass(frozen=True)
class Candidate:
    before_id: str
    after_id: str
    before_source: object
    after_source: object
    before_calibration_revision: str
    after_calibration_revision: str
    target_basis: str


def direct_candidates(events, selections):
    """Identify direct strict-before constraints impossible under selected intervals.

    Selections are trusted fixture inputs, keyed by event ID. This does not infer
    event identity, settle reliability, check transitive relations, or authenticate
    calibrations. Returned candidates require human review; no event is changed.
    Unaligned, relative-only, or differently based pairs remain unresolved.
    """
    events = tuple(events)
    validate_events(events)
    by_id = {event.id: event for event in events}
    if set(selections) - set(by_id):
        raise ValueError('selection for unknown event')
    intervals = {}
    for event in events:
        selected = selections.get(event.id)
        # A selection on a relative event is invalid rather than silently ignored.
        intervals[event.id] = scoped_interval(event, selected)
    edges = set()
    for event in events:
        edges.update((event.id, target) for target in event.before)
        edges.update((target, event.id) for target in event.after)
    result = []
    for before_id, after_id in sorted(edges):
        x, y = intervals[before_id], intervals[after_id]
        if x is None or y is None or not x[2] or not y[2]:
            continue
        a, b = selections[before_id], selections[after_id]
        if a.target_basis != b.target_basis:
            continue
        # A strict A < B is impossible if even the earliest A is at or
        # after the latest B. Equality is not a strict-before relation.
        if x[0] >= y[1]:
            result.append(Candidate(before_id, after_id, by_id[before_id].source,
                                    by_id[after_id].source, x[3], y[3], a.target_basis))
    return tuple(result)
