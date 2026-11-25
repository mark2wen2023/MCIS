"""Research-only offset decisions; never modify or approve original evidence."""
import math
from copy import deepcopy


def _text(v):
    return isinstance(v, str) and bool(v.strip())


def _number(v):
    return type(v) in (int, float) and math.isfinite(v) and v >= 0


def _reference(v):
    return isinstance(v, dict) and all(_text(v.get(k)) for k in ('document_id', 'locator'))


def record_offset_decision(original, candidates, *, frame_id, selected_id=None, rationale=None):
    """Preserve source cell and alternatives; selection is explicit, never inferred.

    Candidates are normalized metres in the named research frame. A selection is
    a research hypothesis, not a design approval or an authenticated review.
    """
    if not _text(frame_id):
        raise ValueError('research frame identifier required')
    if not _reference(original):
        raise ValueError('original cell evidence required')
    if 'raw_text' not in original or (original['raw_text'] is not None and not isinstance(original['raw_text'], str)):
        raise ValueError('original raw text or null required')
    if not isinstance(candidates, list):
        raise ValueError('candidate list required')
    by_id = {}
    for c in candidates:
        if not isinstance(c, dict) or not _text(c.get('id')) or c['id'] in by_id:
            raise ValueError('invalid or duplicate candidate identifier')
        if c.get('frame_id') != frame_id or not _number(c.get('value_m')):
            raise ValueError('candidate must be a finite nonnegative half breadth in the research frame')
        if c.get('basis') not in ('direct', 'derived', 'estimated'):
            raise ValueError('unsupported basis')
        if not isinstance(c.get('sources'), list) or not c['sources'] or not all(_reference(r) for r in c['sources']):
            raise ValueError('candidate source required')
        if c['basis'] != 'direct' and not _text(c.get('method')):
            raise ValueError('calculation or estimation method required')
        if c['basis'] == 'estimated' and not _text(c.get('assumptions')):
            raise ValueError('estimate assumptions required')
        by_id[c['id']] = c
    if selected_id is not None:
        if not _text(selected_id) or selected_id not in by_id or not _text(rationale):
            raise ValueError('explicit candidate and selection rationale required')
    elif rationale is not None and not _text(rationale):
        raise ValueError('invalid rationale')
    return dict(original=deepcopy(original), candidates=deepcopy(candidates),
                frame_id=frame_id, selected_id=selected_id,
                research_value_m=None if selected_id is None else by_id[selected_id]['value_m'],
                decision='unresolved' if selected_id is None else 'research_hypothesis',
                rationale=rationale, design_approved=False, research_only=True,
                lofting_authorized=False)
