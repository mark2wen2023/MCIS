"""Isolated standard-library model, not production input validation or authentication."""
from dataclasses import dataclass
from decimal import Decimal, Context, localcontext
import re


# Contract: fixed-point seconds, at most 9 fractional digits, |input| <= 1e12.
# This is representational precision, not evidence accuracy. Never silently round.
_SECONDS = re.compile(r"-?(?:0|[1-9][0-9]{0,12})(?:\.[0-9]{1,9})?", re.ASCII)
_ARITHMETIC = Context(prec=32)


def number(value):
    if not isinstance(value, str) or not _SECONDS.fullmatch(value):
        raise ValueError('fixed-point seconds with at most 9 fractional digits required')
    d=Decimal(value)  # construction from a string is exact and context-independent
    if d.copy_abs()>Decimal('1000000000000'):
        raise ValueError('seconds outside supported range')
    return d

@dataclass(frozen=True)
class Source:
    case: str
    id: str
    revision: str
    locator: str

@dataclass(frozen=True)
class Event:
    id: str
    source: Source
    clock: str
    original_text: str
    kind: str
    start: str|None=None
    end: str|None=None
    before: tuple[str,...]=()
    after: tuple[str,...]=()

@dataclass(frozen=True)
class Correction:
    case: str
    clock: str
    revision: str
    offset: str
    uncertainty: str
    basis: tuple[Source,...]
    status: str # proposed/confirmed; status from trusted caller, not authentication


def interval(event, correction=None):
    if event.kind not in ('point','range','relative'): raise ValueError('kind')
    if event.kind=='relative':
        if correction is not None: raise ValueError('relative event cannot be clock shifted')
        return None
    lo,hi=number(event.start),number(event.end)
    if lo>hi or (event.kind=='point' and lo!=hi): raise ValueError('bad interval')
    if correction is None: return (lo,hi,False,None)
    c=correction
    if c.case!=event.source.case or c.clock!=event.clock or not c.revision: raise ValueError('wrong correction scope')
    if c.status not in ('proposed','confirmed'): raise ValueError('bad correction status')
    if not c.basis or any(s.case!=c.case for s in c.basis): raise ValueError('basis required')
    delta,unc=number(c.offset),number(c.uncertainty)
    if unc<0: raise ValueError('negative uncertainty')
    if c.status!='confirmed': return (lo,hi,False,None)
    # Three bounded fixed-point operands need at most 22 significant digits.
    # A private context avoids dependence on the caller's decimal precision/traps.
    with localcontext(_ARITHMETIC):
        return (lo+delta-unc,hi+delta+unc,True,c.revision)


def compare(a,b,ca=None,cb=None):
    """Disabled legacy entry point: it had no explicit common target basis.

    Use scoped.scoped_compare with explicitly selected scoped corrections.
    This guard prevents accidental use, not malicious in-process bypass.
    """
    raise ValueError('unsafe legacy comparison disabled; use scoped_compare')


def validate_events(events):
    if len(events)>1000: raise ValueError('budget')
    by={e.id:e for e in events}
    if len(by)!=len(events): raise ValueError('duplicate id')
    if len({e.source.case for e in events})>1: raise ValueError('cross case')
    edges={e.id:set() for e in events}
    for e in events:
        if not e.id or not all((e.source.case,e.source.id,e.source.revision,e.source.locator,e.original_text)): raise ValueError('missing provenance')
        if e.kind not in ('point','range','relative'): raise ValueError('kind')
        if e.kind=='relative':
            if e.start is not None or e.end is not None or not(e.before or e.after): raise ValueError('relative shape')
        else:
            if not e.clock: raise ValueError('clock')
            interval(e)
        for target in e.before+e.after:
            if target not in by: raise ValueError('unknown relation target')
        edges[e.id].update(e.before)
        for t in e.after: edges[t].add(e.id)
    # Iterative topological cycle detection: no invented absolute time or total order.
    degree={k:0 for k in edges}
    for outgoing in edges.values():
        for t in outgoing: degree[t]+=1
    ready=[k for k,v in degree.items() if v==0]; count=0
    while ready:
        node=ready.pop();count+=1
        for t in edges[node]:
            degree[t]-=1
            if degree[t]==0: ready.append(t)
    if count!=len(edges): raise ValueError('contradictory relative order')
    return True
