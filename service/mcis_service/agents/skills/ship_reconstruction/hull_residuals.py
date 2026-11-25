"""Research-only half-breadth residuals at matching measured coordinates."""
import math

def residuals(observed, predicted, *, tolerance_m):
    def finite(v):
        return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
    if not finite(tolerance_m) or tolerance_m<=0:
        raise ValueError('invalid tolerance')
    def index(rows):
        out={}
        for r in rows:
            key=(r['station_x_m'],r['height_z_m'])
            y=r['half_breadth_m']
            if not all(finite(v) for v in key) or not finite(y) or y<0 or key in out:
                raise ValueError('invalid or duplicate coordinate')
            out[key]=r
        return out
    a,b=index(observed),index(predicted)
    details=[]
    missing=[]
    for key,r in sorted(a.items()):
        source=r.get('source')
        if not isinstance(source,dict) or not source.get('document_id') or not source.get('locator'):
            raise ValueError('missing observation provenance')
        if key not in b:
            missing.append({'coordinate':list(key),'source':source});continue
        error=b[key]['half_breadth_m']-r['half_breadth_m']
        details.append({'coordinate':list(key),'error_m':error,'source':source,'exceeds_tolerance':abs(error)>tolerance_m})
    errors=[d['error_m'] for d in details]
    return {'matched':len(errors),'missing':missing,'details':details,
            'max_abs_m':max(map(abs,errors),default=None),
            'mae_m':math.fsum(map(abs,errors))/len(errors) if errors else None,
            'rmse_m':math.hypot(*errors)/math.sqrt(len(errors)) if errors else None,
            'within_tolerance':bool(errors) and not missing and not any(d['exceeds_tolerance'] for d in details),
            'research_only':True,'lofting_authorized':False}
