"""Invoke via unchanged released service PYTHONPATH, with fresh target directories."""
import sys
from pathlib import Path
from helpers import *
raw=Path(sys.argv[1]).read_bytes();root=Path(sys.argv[2]);results=[]
for route in ('generic','preview','commit'):
 with client(root/route) as c:
  before=state(c)
  r=c.post('/api/v1/cases:import',content=raw,headers={**H,'Content-Type':'application/octet-stream'}) if route=='generic' else intake(c,raw,route=='commit')
  assert r.status_code==422,r.text;assert state(c)==before
  results.append((route,r.status_code,r.json()['code']))
print(json.dumps(results))
