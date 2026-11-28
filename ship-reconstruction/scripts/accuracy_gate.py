"""Fail-closed accuracy assessment of independent holdout samples, in metres."""
import math


def assess(samples, policy):
    result = dict(holdout_policy_passed=False, status='insufficient_evidence', total=len(samples))
    keys = ('min_coverage', 'max_rmse_m', 'max_abs_m', 'max_curve_rmse_m')
    def finite(v):
        return type(v) in (int, float) and math.isfinite(v)
    if not isinstance(policy, dict) or any(not finite(policy.get(k)) for k in keys) or not 0 < policy['min_coverage'] <= 1 or any(policy[k] <= 0 for k in keys[1:]):
        return dict(result, reason='missing_or_invalid_policy')
    if not samples:
        return dict(result, reason='no_holdout')
    groups = {}
    seen = set()
    for s in samples:
        source, index, v = s.get('source'), s.get('sample'), s.get('dy_m')
        if not isinstance(source, str) or not source or type(index) is not int or index < 0 or (source,index) in seen or (v is not None and not finite(v)):
            return dict(result, status='rejected', reason='invalid_sample')
        seen.add((source,index)); groups.setdefault(source, []).append(v)
    def metrics(values):
        valid = [v for v in values if v is not None]
        return dict(coverage=len(valid)/len(values), rmse_m=math.hypot(*valid)/math.sqrt(len(valid)) if valid else None, max_abs_m=max(map(abs,valid)) if valid else None)
    overall = metrics([s['dy_m'] for s in samples]); curves = {k:metrics(v) for k,v in groups.items()}
    result.update(overall=overall, curves=curves, policy=dict(policy))
    if any(m['coverage'] < policy['min_coverage'] for m in [overall,*curves.values()]):
        return dict(result, reason='coverage')
    if overall['rmse_m'] > policy['max_rmse_m'] or overall['max_abs_m'] > policy['max_abs_m'] or any(m['rmse_m'] > policy['max_curve_rmse_m'] for m in curves.values()):
        return dict(result, status='rejected', reason='residual_limit')
    return dict(result, holdout_policy_passed=True, status='passed', reason='holdout_policy_passed')
