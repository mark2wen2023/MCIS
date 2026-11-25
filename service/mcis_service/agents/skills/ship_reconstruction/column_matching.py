"""Match CAD text to reviewed column anchors; never shift missing cells."""
import math

def match_columns(row, anchors, tolerance):
    def finite(v):
        return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
    if not finite(tolerance) or tolerance <= 0:
        raise ValueError("invalid tolerance")
    if not anchors or not all(finite(x) for x in anchors):
        raise ValueError("invalid column anchors")
    if any(b-a <= 2*tolerance for a,b in zip(anchors,anchors[1:])):
        raise ValueError("unordered or overlapping column windows")
    slots=[None]*len(anchors)
    issues=[]
    blocked=set()
    for cell in row:
        if not finite(cell.get('x')) or not cell.get('handle') or not isinstance(cell.get('text'),str):
            raise ValueError("invalid cell")
        matches=[i for i,x in enumerate(anchors) if abs(cell['x']-x)<=tolerance]
        if len(matches)!=1:
            issues.append({'code':'unmatched_cell','handle':cell['handle']})
            continue
        i=matches[0]
        if i in blocked or slots[i] is not None:
            issues.append({'code':'duplicate_cell','column':i,'handle':cell['handle']})
            blocked.add(i)
            slots[i]=None
        else:
            slots[i]=dict(cell)
    return {'cells':slots,'issues':issues,'blocked_columns':sorted(blocked)}
