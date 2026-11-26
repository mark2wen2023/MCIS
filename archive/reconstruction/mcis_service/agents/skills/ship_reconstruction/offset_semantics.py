"""Convert reviewed offset-table cells to SI observations, without guessing axes."""
import math
import re
from decimal import Decimal

_NUMBER = re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)')

def numeric(text, unit):
    if unit not in ('m','mm'):
        raise ValueError('unreviewed unit')
    if text is None or text.strip() in ('','—','-'):
        return None
    if not _NUMBER.fullmatch(text.strip()):
        raise ValueError('ambiguous numeric token')
    value = float(Decimal(text.strip()) / (1000 if unit=='mm' else 1))
    if not math.isfinite(value):
        raise ValueError('nonfinite coordinate')
    return value

def normalize_row(cells, stations_m, height_m, unit, document_id, row_locator):
    if len(cells)!=len(stations_m) or not document_id or not row_locator:
        raise ValueError('invalid reviewed mapping')
    def finite(v):
        return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
    if not finite(height_m) or not all(finite(x) for x in stations_m) or len(set(stations_m))!=len(stations_m):
        raise ValueError('invalid reviewed coordinates')
    if unit not in ('m','mm'):
        raise ValueError('unreviewed unit')
    rows=[]
    for i,(cell,x) in enumerate(zip(cells,stations_m)):
        if cell is not None and (not isinstance(cell.get('text'),str) or not cell.get('handle')):
            raise ValueError('missing cell evidence')
        y=numeric(None if cell is None else cell['text'],unit)
        if y is not None and y<0:
            raise ValueError('negative half breadth')
        locator = f'{row_locator}; column {i+1}; ' + ('absent cell' if cell is None else 'entity '+str(cell['handle']))
        rows.append(dict(station_x_m=x,height_z_m=height_m,half_breadth_m=y,source=dict(document_id=document_id,locator=locator)))
    return rows
