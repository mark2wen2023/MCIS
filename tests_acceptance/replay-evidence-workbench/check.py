"""Fixed-query equality + standalone artifact structure, not rendered visual QA."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib
import json
import re
import runpy
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
B=runpy.run_path(str(ROOT/'tools/replay_evidence_workbench/build.py'))
Q=runpy.run_path(str(ROOT/'tools/replay_evidence_clock/query.py'))
class Markup(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.stack=[]
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs)
  if 'id' in attrs:self.ids.append(attrs['id'])
  if tag not in ['meta','input','br','hr','link']:self.stack.append(tag)
 def handle_endtag(self,tag):
  if not self.stack or self.stack.pop()!=tag:raise ValueError('unbalanced '+tag)
class Checks(unittest.TestCase):
 def test_actual_generated_artifact_and_interactions(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'workbench.html';html=B['build'](p)
   with self.assertRaises(FileExistsError):B['build'](p)
   data=json.loads(html.split('<script id="data" type="application/json">')[1].split('</script>')[0])
   tracks,device=Q['load_inputs']()
   for f in data['frames']:self.assertEqual(f,Q['query'](tracks,device,f['relativeSeconds']))
   m=Markup();m.feed(re.sub(r'<script\b[^>]*>[\s\S]*?</script>','',html));self.assertEqual(m.stack,[]);self.assertEqual(len(m.ids),len(set(m.ids)))
   for marker in ['grid-template-columns:214px minmax(0,1fr)','minmax(0,1fr) 340px','@media(max-width:800px)','flex-direction:column','connect-src \'none\'','三维回放 · 未接入','未核实时间 · 不入同步']:self.assertIn(marker,html)
   self.assertNotRegex(html,r'\b(?:src|href)=["\']https?://|fetch\(|XMLHttpRequest|localStorage')
   subprocess.run(['node',str(ROOT/'tests_acceptance/replay-evidence-workbench/panel.cjs'),str(p)],check=True)
 def test_old_product_contract_fixtures_and_browser_hash_unchanged(self):
  paths=['tools/replay_evidence_clock/query.py','tools/replay_evidence_clock/preview.py','tests_acceptance/replay-evidence-clock/browser/check.cjs','contracts/schemas/shared-trajectory-v1.schema.json']
  paths += ['tests_acceptance/shared-trajectory-cross-repo-expanded/'+p for p in ['vessel-a.json','vessel-b.json','vessel-mismatch.json','SHA256SUMS']]
  for p in paths:self.assertEqual((ROOT/p).read_bytes(),subprocess.check_output(['git','show','3ad89e46cfd34f3bf25dcb01c22598f3e670f4aa:'+p],cwd=ROOT))
if __name__=='__main__':unittest.main()
