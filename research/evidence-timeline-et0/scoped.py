"""Research-only scoped clock corrections. Not authentication or a persistence layer."""
from dataclasses import dataclass
from timeline import Source, Correction, number, interval

@dataclass(frozen=True)
class Scope:
    source: Source
    raw_start: str
    raw_end: str

@dataclass(frozen=True)
class ScopedCorrection:
    correction: Correction
    scope: Scope
    target_basis: str  # Explicit common case epoch or equivalent, not inferred from case.


def scoped_interval(event, selected=None):
    """Apply an explicitly selected correction only within its exact source and range.

    Partial overlap is deliberately rejected, not clipped or extrapolated. None means
    unaligned; a proposed correction remains unaligned. Relative-only events retain
    no numeric interval. A caller must validate the whole event collection separately.
    """
    if selected is None:
        return interval(event)
    c, scope = selected.correction, selected.scope
    if not isinstance(selected.target_basis, str) or not selected.target_basis.strip():
        raise ValueError('explicit target basis required')
    lo, hi = number(scope.raw_start), number(scope.raw_end)
    if lo > hi:
        raise ValueError('invalid scope')
    if scope.source != event.source:
        raise ValueError('source version or locator outside scope')
    if c.case != scope.source.case:
        raise ValueError('scope case mismatch')
    if event.kind == 'relative':
        raise ValueError('relative event has no raw time to calibrate')
    raw = interval(event)
    if raw[0] < lo or raw[1] > hi:
        raise ValueError('event not fully contained in calibration scope')
    return interval(event, c)


def scoped_compare(a, b, ca=None, cb=None):
    if a.source.case != b.source.case:
        raise ValueError('cross case')
    x, y = scoped_interval(a, ca), scoped_interval(b, cb)
    if x is None or y is None or not (x[2] and y[2]):
        return 'undetermined'
    # Confirmation alone does not put clocks on the same timeline.
    if ca.target_basis != cb.target_basis:
        return 'undetermined'
    if x[1] < y[0]: return 'before'
    if y[1] < x[0]: return 'after'
    return 'overlap-not-identity'
