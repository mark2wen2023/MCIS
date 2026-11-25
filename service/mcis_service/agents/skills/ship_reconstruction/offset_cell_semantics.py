"""Preserve offset-cell semantics without inferring geometry from blanks."""
import math

SEMANTICS=frozenset(('unknown','not_applicable','outside_domain','omitted','confirmed_zero','measured'))

def classify_cell(value, *, semantic='unknown', evidence=None):
    if semantic not in SEMANTICS:
        raise ValueError('unsupported semantic')
    if value is not None:
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
            raise ValueError('invalid half breadth')
        if semantic not in ('measured','confirmed_zero'):
            raise ValueError('numeric cell requires explicit measured semantics')
        if semantic=='confirmed_zero' and value!=0:
            raise ValueError('confirmed zero requires zero')
    elif semantic in ('measured','confirmed_zero'):
        raise ValueError('numeric evidence required; blank cannot become zero')
    if semantic!='unknown':
        if not isinstance(evidence,dict) or not evidence.get('document_id') or not evidence.get('locator'):
            raise ValueError('semantic classification requires provenance')
    return dict(value=value,semantic=semantic,evidence=evidence,review='pending',lofting_authorized=False)
