"""Compare explicit research hypotheses on a common supported bilinear domain."""
import math
from .research_baseline import record_offset_decision


def compare_hypotheses(stations, heights, cells, scenarios, support, *, frame_id, symmetry_confirmed):
    """No automatic selection, gap bridging, probability or displacement claim."""
    if symmetry_confirmed is not True:
        raise ValueError('explicit research symmetry assumption required')
    def finite(v):
        return type(v) in (int, float) and math.isfinite(v)
    for axis in (stations, heights):
        if len(axis)<2 or not all(finite(v) for v in axis) or any(b<=a for a,b in zip(axis,axis[1:])):
            raise ValueError('invalid axis')
    n,m=len(stations),len(heights)
    def shape(a,r,c):
        return isinstance(a,(list,tuple)) and len(a)==r and all(isinstance(row,(list,tuple)) and len(row)==c for row in a)
    if not shape(cells,n,m) or not shape(support,n-1,m-1) or any(type(v) is not bool for row in support for v in row):
        raise ValueError('invalid cells or support mask')
    if not isinstance(scenarios,dict) or len(scenarios)<2:
        raise ValueError('at least two explicit scenarios required')
    widths={}
    for name,s in scenarios.items():
        if not isinstance(name,str) or not name.strip() or not isinstance(s,dict) or not shape(s.get('choices'),n,m):
            raise ValueError('invalid scenario')
        grid=[]
        for i,row in enumerate(cells):
            values=[]
            for j,cell in enumerate(row):
                if cell.get('frame_id')!=frame_id:
                    raise ValueError('mixed research frames')
                decision=record_offset_decision(cell['original'],cell['candidates'],frame_id=frame_id,
                    selected_id=s['choices'][i][j],rationale=s.get('rationale'))
                values.append(decision['research_value_m'])
            grid.append(values)
        widths[name]=grid
    common=[]
    for i in range(n-1):
        for j in range(m-1):
            corners=((i,j),(i+1,j),(i,j+1),(i+1,j+1))
            if support[i][j] and all(g[a][b] is not None for g in widths.values() for a,b in corners):
                common.append((i,j))
    footprint=math.fsum((stations[i+1]-stations[i])*(heights[j+1]-heights[j]) for i,j in common)
    full=(stations[-1]-stations[0])*(heights[-1]-heights[0])
    if not math.isfinite(full) or full<=0:
        raise ValueError('invalid domain area')
    totals={}
    for name,g in widths.items():
        # Integral of 2*y over each common x-z patch, under bilinear interpolation.
        parts=[(stations[i+1]-stations[i])*(heights[j+1]-heights[j])*math.fsum(g[a][b]/2 for a,b in ((i,j),(i+1,j),(i,j+1),(i+1,j+1))) for i,j in common]
        totals[name]=dict(common_volume_m3=math.fsum(parts) if parts else None,patch_volume_m3=parts)
    vals=[v['common_volume_m3'] for v in totals.values() if v['common_volume_m3'] is not None]
    return dict(frame_id=frame_id,common_cells=[list(c) for c in common],coverage_fraction=footprint/full,
        scenarios=totals,volume_range_m3=max(vals)-min(vals) if vals else None,
        measure='symmetric_bilinear_common_domain_volume',displacement_certified=False,
        research_only=True,lofting_authorized=False)
