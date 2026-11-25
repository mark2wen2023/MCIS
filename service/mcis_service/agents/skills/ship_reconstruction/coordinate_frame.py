"""Explicit reviewed coordinate mapping for research offset data."""
import math

def normalize_offset(station, height, breadth, *, frame):
    required=('unit','x_origin_m','z_origin_m','x_direction','z_direction','source','review')
    if any(k not in frame for k in required) or frame['review']!='accepted':
        raise ValueError('reviewed coordinate frame required')
    source=frame['source']
    if not isinstance(source,dict) or not source.get('document_id') or not source.get('locator'):
        raise ValueError('frame provenance required')
    scale={'mm':.001,'cm':.01,'m':1}.get(frame['unit'])
    if scale is None or frame['x_direction'] not in ('forward','aft') or frame['z_direction'] not in ('up','down'):
        raise ValueError('unsupported frame')
    values=(station,height,breadth,frame['x_origin_m'],frame['z_origin_m'])
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in values) or breadth<0:
        raise ValueError('invalid numeric offset')
    x=frame['x_origin_m']+station*scale*(1 if frame['x_direction']=='forward' else -1)
    z=frame['z_origin_m']+height*scale*(1 if frame['z_direction']=='up' else -1)
    y=breadth*scale
    if not all(math.isfinite(v) for v in (x,y,z)):
        raise ValueError('coordinate overflow')
    return dict(station_x_m=x,height_z_m=z,half_breadth_m=y,frame_source=dict(source),research_only=True,lofting_authorized=False)
