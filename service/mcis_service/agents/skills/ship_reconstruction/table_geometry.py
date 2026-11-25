"""Conservative rectangular CAD grid detection in a reviewed planar region."""
import math

def detect_grid(segments, tolerance):
    def finite(v):
        return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
    if not finite(tolerance) or tolerance<=0:
        raise ValueError('invalid tolerance')
    horizontal,vertical=[],[]
    for s in segments:
        a,b=s['start'],s['end']
        if len(a)!=2 or len(b)!=2 or not all(finite(v) for v in (*a,*b)) or not s.get('handle'):
            raise ValueError('invalid segment')
        dx,dy=abs(a[0]-b[0]),abs(a[1]-b[1])
        if dy<=tolerance and dx>2*tolerance:
            horizontal.append(((a[1]+b[1])/2,min(a[0],b[0]),max(a[0],b[0]),s['handle']))
        elif dx<=tolerance and dy>2*tolerance:
            vertical.append(((a[0]+b[0])/2,min(a[1],b[1]),max(a[1],b[1]),s['handle']))
    xs=sorted({v[0] for v in vertical})
    ys=sorted({h[0] for h in horizontal})
    issues=[]
    if len(xs)<2 or len(ys)<2:
        issues.append('insufficient_grid_lines')
    elif any(b-a<=2*tolerance for axis in (xs,ys) for a,b in zip(axis,axis[1:])):
        issues.append('ambiguous_grid_spacing')
    else:
        for x in xs:
            if not any(v[0]==x and v[1]<=ys[0]+tolerance and v[2]>=ys[-1]-tolerance for v in vertical):
                issues.append('incomplete_vertical')
        for y in ys:
            if not any(h[0]==y and h[1]<=xs[0]+tolerance and h[2]>=xs[-1]-tolerance for h in horizontal):
                issues.append('incomplete_horizontal')
    return {'x_boundaries':xs,'y_boundaries':ys,'issues':issues,'candidate_complete':not issues,'review':'pending','handles':[s[3] for s in horizontal+vertical]}
