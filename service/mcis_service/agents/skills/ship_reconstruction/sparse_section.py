"""Research-only interpolation across explicitly supported adjacent offset cells."""
import math

def sample_sparse_section(cells, heights):
    """Cells are ordered reviewed height coordinates, with explicit semantic states.
    Only adjacent numeric cells support interpolation; blanks break the domain.
    """
    def finite(v):
        return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
    cells=list(cells)
    if not cells:
        raise ValueError('empty section')
    zs=[c['height_m'] for c in cells]
    if not all(finite(z) for z in zs) or any(b<=a for a,b in zip(zs,zs[1:])):
        raise ValueError('invalid height grid')
    for c in cells:
        state=c['semantic']
        y=c['value']
        if state not in ('measured','confirmed_zero','unknown','not_applicable','outside_domain','omitted'):
            raise ValueError('invalid semantic')
        if state in ('measured','confirmed_zero'):
            if not finite(y) or y<0 or (state=='confirmed_zero' and y!=0):
                raise ValueError('invalid numeric cell')
            e=c.get('evidence')
            if c.get('review')!='accepted' or not isinstance(e,dict) or not e.get('document_id') or not e.get('locator'):
                raise ValueError('reviewed evidence required')
        elif y is not None:
            raise ValueError('non-numeric semantic must retain null')
    out=[]
    for z in heights:
        if not finite(z):
            raise ValueError('invalid query height')
        sample=dict(height_m=z,half_breadth_m=None,basis='unsupported',sources=[])
        for c in cells:
            if z==c['height_m'] and c['value'] is not None:
                sample.update(half_breadth_m=c['value'],basis='direct_sample',sources=[c['evidence']])
                break
        else:
            for a,b in zip(cells,cells[1:]):
                if a['height_m']<z<b['height_m'] and a['value'] is not None and b['value'] is not None:
                    t=(z-a['height_m'])/(b['height_m']-a['height_m'])
                    sample.update(half_breadth_m=(1-t)*a['value']+t*b['value'],basis='interpolated',sources=[a['evidence'],b['evidence']])
                    break
        out.append(sample)
    return dict(samples=out,research_only=True,lofting_authorized=False)
