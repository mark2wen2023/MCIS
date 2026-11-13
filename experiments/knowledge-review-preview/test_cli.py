import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from gate import Source
from review_cli import main

class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.c = self.root/'c.json'; self.s = self.root/'s.json'; self.o = self.root/'out.html'
        source = Source('s', 'v1', 'Synthetic', '演示', '虚构证据')
        self.s.write_text(json.dumps({'sources':[dict(sourceId='s', version='v1', sourceType='Synthetic', locator='演示', content=source.content)]}), encoding='utf-8')
        self.body={'candidates':[dict(kind='Case', title='演示', claim='待核实', citations=[dict(sourceId='s',version='v1',textSha256=source.text_sha256,start=0,end=4,quote='虚构证据')])]}
        self.save()
    def save(self): self.c.write_text(json.dumps(self.body),encoding='utf-8')
    def run_cli(self):
        out=io.StringIO();err=io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            result=main(['--candidates',str(self.c),'--sources',str(self.s),'--output',str(self.o)])
        self.assertEqual(out.getvalue(),'');return result,err.getvalue()
    def test_happy(self):
        self.assertEqual(self.run_cli()[0],0);self.assertIn('虚构材料',self.o.read_text());self.assertTrue(self.c.exists())
    def test_no_overwrite(self):
        self.o.write_bytes(b'keep');self.assertEqual(self.run_cli()[0],3);self.assertEqual(self.o.read_bytes(),b'keep')
    def test_stale_no_output(self):
        self.body['candidates'][0]['citations'][0]['version']='v2';self.save();self.assertEqual(self.run_cli()[0],4);self.assertFalse(self.o.exists())
    def test_bad_manifest_no_output(self):
        self.s.write_text('{"sources":[],"sources":[]}');self.assertEqual(self.run_cli()[0],4);self.assertFalse(self.o.exists())
    def test_budget(self):
        self.c.write_bytes(b' '*65537);self.assertEqual(self.run_cli()[0],4);self.assertFalse(self.o.exists())
    def test_missing_safe_error(self):
        self.s.unlink();code,error=self.run_cli();self.assertEqual(code,3);self.assertNotIn(str(self.root),error);self.assertFalse(self.o.exists())
    def test_symlink_output(self):
        self.o.symlink_to(self.s);before=self.s.read_bytes();self.assertEqual(self.run_cli()[0],3);self.assertEqual(before,self.s.read_bytes())
    def test_fifo_rejected(self):
        self.c.unlink();os.mkfifo(self.c);self.assertEqual(self.run_cli()[0],4);self.assertFalse(self.o.exists())
    def test_unknown_manifest_field(self):
        body=json.loads(self.s.read_text());body['path']='/etc/passwd';self.s.write_text(json.dumps(body));self.assertEqual(self.run_cli()[0],4);self.assertFalse(self.o.exists())

if __name__=='__main__': unittest.main()
