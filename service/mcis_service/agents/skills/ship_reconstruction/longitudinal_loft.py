"""Experimental open hull surface on a common reviewed height grid.
No caps, symmetry assumption, extrapolation or production authorization.
"""
import math

def loft_open_side(stations, heights):
    def finite(v):
        return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
    if len(stations)<2 or len(heights)<2 or not all(finite(z) for z in heights):
        raise ValueError('insufficient or invalid grid')
    if any(b<=a for a,b in zip(heights,heights[1:])):
        raise ValueError('heights must increase')
    xs=[s['x_m'] for s in stations]
    if not all(finite(x) for x in xs) or any(b<=a for a,b in zip(xs,xs[1:])):
        raise ValueError('stations must increase')
    vertices=[]
    for s in stations:
        widths=s['half_breadths_m']
        if len(widths)!=len(heights) or any(not finite(y) or y<0 for y in widths):
            raise ValueError('invalid or missing half breadth')
        vertices.extend([s['x_m'],y,z] for y,z in zip(widths,heights))
    faces=[]
    n=len(heights)
    for i in range(len(stations)-1):
        for j in range(n-1):
            a=i*n+j
            faces.extend([[a,a+1,a+n],[a+1,a+n+1,a+n]])
    return {'vertices_m':vertices,'triangles':faces,'research_only':True,'closed':False,'lofting_authorized':False}
