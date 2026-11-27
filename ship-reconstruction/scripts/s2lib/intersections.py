"""原始有理 B 样条在已测纸面坐标系中的等高线交点（单位米）。"""
import numpy as np
from numpy.polynomial import Polynomial
from scipy.interpolate import BSpline, PPoly


def section_envelope(curve, axes, levels, tolerance=1e-8):
    geom = curve["geometry"]
    pts = np.asarray(geom["control_points"], dtype=float)
    degree, knots = geom["degree"], np.asarray(geom["knots"], dtype=float)
    if not len(pts) or len(knots) != len(pts) + degree + 1:
        return None
    if "source_to_wcs_row_major_ezdxf" in curve:
        matrix = np.asarray(curve["source_to_wcs_row_major_ezdxf"]).reshape(4, 4)
        pts = np.column_stack((pts, np.ones(len(pts)))) @ matrix
    xy1 = np.column_stack((pts[:, :2], np.ones(len(pts))))
    weights = np.asarray(geom["weights"] or np.ones(len(pts)))
    if len(weights) != len(pts) or not np.all(weights > 0):
        return None

    def polynomial(values):
        return PPoly.from_spline(BSpline(knots, values, degree))

    zn = polynomial((xy1 @ axes["Z"]) * weights)
    yn = polynomial((xy1 @ axes["Y"]) * weights)
    den = polynomial(weights)
    start, stop = knots[degree], knots[-degree-1]
    breaks = np.unique(knots[(knots >= start) & (knots <= stop)])
    result = {}
    for z in levels:
        eq = PPoly(zn.c - z * den.c, knots, extrapolate=False)
        roots = eq.roots(extrapolate=False)
        hits = list(roots[np.isfinite(roots) & (roots >= start) & (roots <= stop)])
        hits.extend(breaks[np.abs(eq(breaks)/den(breaks)) <= tolerance])
        for i in range(degree, len(pts)):
            span = knots[i+1] - knots[i]
            if span <= 0:
                continue
            # A horizontal rational span can attain its outer breadth inside the span.
            if np.sum(np.abs(eq.c[:, i]) * span**np.arange(degree, -1, -1)) > tolerance * min(weights):
                continue
            y, w = Polynomial(yn.c[::-1, i]), Polynomial(den.c[::-1, i])
            for root in (y.deriv()*w-y*w.deriv()).roots():
                if abs(root.imag) < 1e-10 and 0 <= root.real <= span:
                    hits.append(knots[i] + root.real)
        if hits:
            result[z] = float(np.max(np.abs(yn(hits)/den(hits))))
    return result
