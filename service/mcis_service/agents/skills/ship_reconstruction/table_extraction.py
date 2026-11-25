"""Cluster normalized CAD text anchors into candidate table rows.
Not a semantic offset extractor. Input must be cropped to a reviewed table region
and transformed into one planar coordinate frame by the caller.
"""
import math

def cluster_rows(cells, tolerance):
    if isinstance(tolerance, bool) or not isinstance(tolerance,(int,float)) or not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("positive finite tolerance required")
    clean=[]
    for c in cells:
        if not all(isinstance(c.get(k),(int,float)) and not isinstance(c[k],bool) and math.isfinite(c[k]) for k in ('x','y')):
            raise ValueError("invalid anchor")
        if not isinstance(c.get('text'),str) or not c.get('handle'):
            raise ValueError("missing text or evidence handle")
        clean.append(dict(c))
    rows=[]
    for c in sorted(clean,key=lambda c:(-c['y'],c['x'],str(c['handle']))):
        if not rows or rows[-1][0]['y']-c['y']>tolerance:
            rows.append([])
        rows[-1].append(c)
    return [sorted(r,key=lambda c:(c['x'],str(c['handle']))) for r in rows]
