"""Offline dependency failure tests; no semantic or permission claim."""
import importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('dep',ROOT/'dependencies.py');d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
if __name__=='__main__':
    specs=json.loads((ROOT/'DEPENDENCIES.json').read_text())
    count=0
    with d.dependencies() as paths:
        for spec in specs:
            raw=paths[spec['key']].read_bytes();d.verify(raw,spec)
            try:d.verify(raw+b' ',spec)
            except ValueError as e:assert str(e).startswith('DEPENDENCY_BLOB:');count+=1
            else:raise AssertionError('changed dependency accepted')
            if 'sha256' in spec:
                altered=dict(spec,sha256='0'*64)
                try:d.verify(raw,altered)
                except ValueError as e:assert str(e).startswith('ORIGINAL_SHA256:');count+=1
                else:raise AssertionError('wrong raw SHA accepted')
    print(json.dumps({'dependency_checks_pass':True,'changed_or_wrong_hash_rejected':count}))
