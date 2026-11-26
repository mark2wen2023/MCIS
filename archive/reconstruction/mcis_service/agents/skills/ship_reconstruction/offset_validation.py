"""Validate normalized offset observations without inventing missing geometry."""
import math

def validate_offsets(rows):
    """Coordinates are metres in a separately reviewed hull frame.
    Null half breadth means missing, not zero. Return diagnostics, not a surface.
    """
    points, missing, conflicts, invalid = {}, [], [], []
    for i, row in enumerate(rows):
        xyz = [row.get(k) for k in ('station_x_m','height_z_m','half_breadth_m')]
        source = row.get('source')
        if not isinstance(source, dict) or not source.get('document_id') or not source.get('locator'):
            invalid.append(i)
            continue
        if any(v is None for v in xyz):
            missing.append(i)
            continue
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in xyz) or xyz[2]<0:
            invalid.append(i)
            continue
        key = tuple(xyz[:2])
        if key in points and abs(points[key]-xyz[2])>1e-6:
            conflicts.append(i)
        else:
            points.setdefault(key,xyz[2])
    return {'unique_points':len(points),'missing_rows':missing,'conflicting_rows':conflicts,'invalid_rows':invalid,'lofting_authorized':False}
