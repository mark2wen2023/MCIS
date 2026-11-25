"""Experimental tensor-product spline over a rectangular half-breadth grid."""
import numpy as np

def fit_surface(stations_m, heights_m, widths_m):
    from scipy.interpolate import RectBivariateSpline
    x=np.asarray(stations_m,dtype=float)
    z=np.asarray(heights_m,dtype=float)
    y=np.asarray(widths_m,dtype=float)
    if x.ndim!=1 or z.ndim!=1 or len(x)<2 or len(z)<2 or y.shape!=(len(x),len(z)):
        raise ValueError('invalid rectangular grid')
    if not all(np.isfinite(a).all() for a in (x,z,y)) or (y<0).any() or (np.diff(x)<=0).any() or (np.diff(z)<=0).any():
        raise ValueError('invalid coordinates')
    spline=RectBivariateSpline(x,z,y,kx=min(3,len(x)-1),ky=min(3,len(z)-1),s=0)
    def evaluate(station,height):
        if not np.isfinite([station,height]).all() or not x[0]<=station<=x[-1] or not z[0]<=height<=z[-1]:
            raise ValueError('outside measured domain')
        width=float(spline.ev(station,height))
        if not np.isfinite(width) or width<0:
            raise ValueError('invalid spline half breadth')
        return width
    return evaluate
