"""Opt-in shell structure/default-off check; no browser or business reads."""
from pathlib import Path
from html.parser import HTMLParser
import re
import runpy
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[2]
FIXED='0dc1226364524977a4155e480d96436443cd8967'
class Markup(HTMLParser):
    def __init__(self):super().__init__();self.ids=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:self.ids.append(attrs['id'])
class Shell(unittest.TestCase):
    def test_shared_shell_no_default_adapter_or_sample_data(self):
        build=runpy.run_path(str(ROOT/'tools/replay_evidence_workbench/registered_build.py'))['build']
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'shell.html';html=build(path)
            with self.assertRaises(FileExistsError):build(path)
            m=Markup();m.feed(re.sub(r'<script\b[^>]*>[\s\S]*?</script>','',html))
            self.assertEqual(len(m.ids),len(set(m.ids)))
            for marker in ('registered-case','registered-load','map','timeline','pointer'):self.assertIn(marker,m.ids)
            self.assertNotRegex(html,r'SYN-XREPO|SYN-DEVICE|fetch\(|XMLHttpRequest|localStorage|sessionStorage|location\.|\bsrc=["\']https?://')
            self.assertIn("connect-src 'none'",html)
            self.assertIn('无默认身份、查询或业务接线',html)
            self.assertIn('<script id="data" type="application/json">{}</script>',html)
    def test_original_frozen_entry_unchanged(self):
        for name in ('build.py','workbench.html','workbench.js','style.css'):
            path='tools/replay_evidence_workbench/'+name
            self.assertEqual((ROOT/path).read_bytes(),subprocess.check_output(['git','show',FIXED+':'+path],cwd=ROOT))
if __name__=='__main__':unittest.main(verbosity=2)
