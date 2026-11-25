"""Bound longitudinal chord error against a reviewed piecewise-linear reference.

Only one contiguous waterline, in metres and a reviewed x/y frame, is accepted.
The bound is relative to the supplied polyline, not the unknown physical hull.
Independent validation samples never influence knot selection.
"""
from bisect import bisect_right
from copy import deepcopy
import math
import hashlib
import json


def _finite(v):
    return type(v) in (int, float) and math.isfinite(v)


def _reference(ref):
    return isinstance(ref, dict) and all(isinstance(ref.get(k), str) and ref[k].strip()
                                         for k in ('document_id', 'locator'))


def _points(points, name):
    if not isinstance(points, (list, tuple)) or len(points) < (2 if name == 'reference' else 1):
        raise ValueError('invalid ' + name + ' points')
    for p in points:
        if not isinstance(p, dict) or not _finite(p.get('x_m')) or not _finite(p.get('half_breadth_m')) or p['half_breadth_m'] < 0 or not _reference(p.get('source')):
            raise ValueError('invalid ' + name + ' point')
    if any(b['x_m'] <= a['x_m'] for a, b in zip(points, points[1:])):
        raise ValueError('non-increasing ' + name + ' x')
    return deepcopy(list(points))


def _line(a, b, x):
    t = (x - a['x_m']) / (b['x_m'] - a['x_m'])
    y = (1-t)*a['half_breadth_m'] + t*b['half_breadth_m']
    if not math.isfinite(y):
        raise ValueError('nonfinite chord')
    return y


def reference_digest(reference):
    return hashlib.sha256(json.dumps(reference, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def adaptive_waterline(reference, *, mandatory_x_m, tolerance_m, max_knots,
                       frame_id, height_m, reference_review, holdout=None):
    """Return knots selected from reviewed source points, not fabricated points.

    Every consecutive source pair must represent a supported reference segment.
    Mandatory stations must already be source knots. The residual is half-breadth
    at matching x, not 3-D closest distance. Max error is attained at an original
    knot for piecewise-linear reference and candidate, in exact arithmetic.
    """
    if not isinstance(frame_id, str) or not frame_id.strip() or not _finite(height_m):
        raise ValueError('reviewed waterline frame and height required')
    if not _reference(reference_review) or reference_review.get('review') != 'accepted' or reference_review.get('contiguous_reference') is not True or reference_review.get('frame_id') != frame_id or not _finite(reference_review.get('height_m')) or reference_review['height_m'] != height_m:
        raise ValueError('matching contiguous waterline review required')
    if not _finite(tolerance_m) or tolerance_m < 0 or type(max_knots) is not int or max_knots < 2:
        raise ValueError('invalid error or knot budget')
    ref = _points(reference, 'reference')
    digest = reference_digest(ref)
    if reference_review.get('reference_sha256') != digest:
        raise ValueError('reference review digest mismatch')
    xs = [p['x_m'] for p in ref]
    if not math.isfinite(xs[-1]-xs[0]):
        raise ValueError('nonfinite reference span')
    if not isinstance(mandatory_x_m, (list, tuple)) or any(not _finite(x) or x not in xs for x in mandatory_x_m) or len(set(mandatory_x_m)) != len(mandatory_x_m):
        raise ValueError('mandatory stations must be unique source knots')
    selected = {0, len(ref)-1} | {xs.index(x) for x in mandatory_x_m}
    if len(selected) > max_knots:
        raise ValueError('mandatory stations exceed knot budget')
    # Iterative refinement; each selected vertex is an original evidence point.
    while True:
        order = sorted(selected)
        worst = (0.0, None)
        for a, b in zip(order, order[1:]):
            for i in range(a+1, b):
                err = abs(ref[i]['half_breadth_m'] - _line(ref[a], ref[b], xs[i]))
                if not math.isfinite(err):
                    raise ValueError('nonfinite residual')
                if err > worst[0]:
                    worst = (err, i)
        if worst[0] <= tolerance_m or len(selected) >= max_knots:
            break
        selected.add(worst[1])
    knots = [ref[i] for i in order]
    validation = None
    if holdout is not None:
        test = _points(holdout, 'holdout')
        if any(p['x_m'] < xs[0] or p['x_m'] > xs[-1] for p in test):
            raise ValueError('holdout outside supported domain')
        fit_refs = {(p['source']['document_id'], p['source']['locator']) for p in ref}
        if any((p['source']['document_id'],p['source']['locator']) in fit_refs for p in test):
            raise ValueError('holdout reuses reference locator')
        kx = [p['x_m'] for p in knots]
        errors = []
        for p in test:
            i = min(bisect_right(kx,p['x_m'])-1,len(knots)-2)
            errors.append(_line(knots[i],knots[i+1],p['x_m'])-p['half_breadth_m'])
        abs_errors = sorted(abs(e) for e in errors)
        # hypot avoids unnecessary overflow from squaring large residuals.
        validation = dict(count=len(errors),max_abs_m=max(abs_errors),
                          mae_m=math.fsum(e/len(errors) for e in abs_errors),
                          rmse_m=math.hypot(*(e/math.sqrt(len(errors)) for e in errors)),
                          p95_nearest_rank_m=abs_errors[math.ceil(.95*len(errors))-1],
                          signed_errors_m=errors,observations=test,
                          independence_authenticated=False)
    return dict(frame_id=frame_id,height_m=height_m,knots=deepcopy(knots),
                source_point_count=len(ref),reference_sha256=digest,reference_review=deepcopy(reference_review),
                max_reference_residual_m=worst[0],tolerance_m=tolerance_m,
                tolerance_met=worst[0]<=tolerance_m,holdout=validation,
                metric='same_x_half_breadth',reference_model='piecewise_linear',
                physical_hull_accuracy_certified=False,research_only=True,lofting_authorized=False)
