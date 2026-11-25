"""Research-only shape-preserving section interpolation."""
import math
from .section_interpolation import interpolate_section

def interpolate_pchip(points, heights):
    points=list(points)
    heights=list(heights)
    baseline=interpolate_section(points,heights)
    from scipy.interpolate import PchipInterpolator
    ordered=sorted(points)
    curve=PchipInterpolator([p[0] for p in ordered],[p[1] for p in ordered],extrapolate=False)
    for sample in baseline['samples']:
        z=sample['height_m']
        y=float(curve(z))
        if not math.isfinite(y) or y<0:
            raise ValueError('invalid interpolated half breadth')
        sample['half_breadth_m']=y
    baseline['method']='pchip'
    return baseline
