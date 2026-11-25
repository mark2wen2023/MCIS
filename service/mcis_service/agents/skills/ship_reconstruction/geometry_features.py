"""Research-only section turning-angle candidates, not confirmed chines."""
import math

def detect_candidates(points, *, angle_threshold_deg):
    def finite(v):
        return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
    if not finite(angle_threshold_deg) or not 0<angle_threshold_deg<180:
        raise ValueError('invalid angle threshold')
    points=list(points)
    if len(points)<3 or any(len(p)!=2 or not all(finite(v) for v in p) or p[1]<0 for p in points):
        raise ValueError('invalid section samples')
    if any(b[0]<=a[0] for a,b in zip(points,points[1:])):
        raise ValueError('heights must strictly increase')
    turns=[]
    for a,b,c in zip(points,points[1:],points[2:]):
        first=math.atan2(b[1]-a[1],b[0]-a[0])
        second=math.atan2(c[1]-b[1],c[0]-b[0])
        angle=abs(math.degrees(second-first))
        turns.append(dict(height_m=b[0],half_breadth_m=b[1],turn_deg=angle,candidate=angle>=angle_threshold_deg))
    return dict(turns=turns,threshold_deg=angle_threshold_deg,review='pending',research_only=True,lofting_authorized=False)
