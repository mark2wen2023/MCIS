from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent;d=P/'fixture';files=[*sorted((d/'inputs').rglob('*.dxf')),d/'truth.json',P/'generate.py',P/'extend.py',P/'score.py']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m={str(p.relative_to(P)):sha(p) for p in files};out=P/'s2-freeze.json';assert not out.exists();out.write_text(json.dumps(m,indent=2)+'\n')
for q in files+[out]:q.chmod(0o444)
truth=json.loads((d/'truth.json').read_text());print(sha(out),len(truth),sum(len(c['files']) for c in truth),sum(len(f['cells']) for c in truth for f in c['files']))
