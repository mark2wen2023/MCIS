"""Compare final pytest summary node sets, not historical small-suite counts."""
import json,re
from pathlib import Path
root=Path(__file__).resolve().parents[2]
paths={'parent':Path(__file__).with_name('parent-full-tests.txt'),'candidate':root/'server-idempotency'/'full-review-tests.txt'}
parsed={}
for name,path in paths.items():
 raw=path.read_text();nodes={}
 for line in raw.splitlines():
  match=re.match(r'^(FAILED|ERROR) (.+?)(?: - |$)',line)
  if match:nodes.setdefault(match[2],set()).add(match[1])
 summary=[line for line in raw.splitlines() if re.search(r'\d+ (?:failed|passed).* in [\d.]+s',line)]
 parsed[name]={'path':str(path),'summary':summary[-1] if summary else None,'nodes':{node:sorted(kinds) for node,kinds in sorted(nodes.items())}}
if not all(p['summary'] for p in parsed.values()):raise SystemExit('Both completed summaries required')
a=set(parsed['parent']['nodes']);b=set(parsed['candidate']['nodes'])
result={'runs':parsed,'inherited_failure_or_error_nodes':sorted(a&b),'candidate_only_nodes':sorted(b-a),'parent_only_nodes':sorted(a-b),'status_changed_nodes':sorted(n for n in a&b if parsed['parent']['nodes'][n]!=parsed['candidate']['nodes'][n])}
Path(__file__).with_name('comparison.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='runs'},indent=2))
