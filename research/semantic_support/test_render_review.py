import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from html.parser import HTMLParser
import render_review as r
HERE=Path(__file__).resolve().parent
class Tags(HTMLParser):
    def __init__(self):super().__init__();self.tags=[]
    def handle_starttag(self,tag,attrs):self.tags.append((tag,dict(attrs)))
class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.c,self.sha=r.load(HERE/'jiangxin9-provisional.json');self.p,_=r.load(HERE/'jiangxin9-real-predictions.json')
    def test_static_controls_and_complete_values(self):
        out=r.render(self.c,self.sha,self.p).decode();tree=Tags();tree.feed(out)
        self.assertEqual(sum(t=='article' for t,a in tree.tags),8)
        self.assertEqual(sum(t=='input' for t,a in tree.tags),24)
        self.assertEqual(sum(t=='textarea' for t,a in tree.tags),8)
        self.assertFalse(any(t in ('script','a','form','iframe','img','link') for t,a in tree.tags))
        self.assertFalse(any(('name' in a and t in ('input','textarea')) or 'src' in a or 'href' in a for t,a in tree.tags))
        for p in self.p['predictions']:self.assertIn(r.esc(p['rationale']),out)
        for c in self.c['items']:self.assertIn(r.esc(c['citation']['quote']),out)
        self.assertFalse(any('checked' in a for t,a in tree.tags));self.assertIn('标签一致不等于解释有依据',out);self.assertIn('未保存',out)
        self.assertIn('white-space:pre-wrap',out);self.assertIn(r.esc(r.CSP),out)
    def test_injection_literal(self):
        self.p['predictions'][0]['rationale']='</pre><script>bad()</script><img src="x"> & "'
        self.c['items'][0]['sourceLocator']['url']='https://example.test/\"><script>bad()</script>'
        out=r.render(self.c,self.sha,self.p).decode();tree=Tags();tree.feed(out)
        self.assertFalse(any(t in ('script','img') for t,a in tree.tags));self.assertIn('&lt;script&gt;',out)
    def test_reject_bad_prediction(self):
        self.p['predictions'][0]['label']='certain'
        with self.assertRaises(ValueError):r.render(self.c,self.sha,self.p)
    def test_reject_digest_mismatch(self):
        with self.assertRaises(ValueError):r.render(self.c,'a'*64,self.p)
    def test_budget(self):
        old=r.MAX_OUTPUT_BYTES;r.MAX_OUTPUT_BYTES=1
        try:
            with self.assertRaises(ValueError):r.render(self.c,self.sha,self.p)
        finally:r.MAX_OUTPUT_BYTES=old
    def test_cli_exclusive_and_permissions(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'review.html';cmd=[sys.executable,str(HERE/'render_review.py'),'--corpus',str(HERE/'jiangxin9-provisional.json'),'--predictions',str(HERE/'jiangxin9-real-predictions.json'),'--output',str(path)]
            first=subprocess.run(cmd,capture_output=True);self.assertEqual(first.returncode,0);self.assertEqual(path.stat().st_mode&0o777,0o600);before=path.read_bytes()
            second=subprocess.run(cmd,capture_output=True);self.assertEqual(second.returncode,2);self.assertEqual(path.read_bytes(),before)
    def test_duplicate_input_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'x.json';path.write_text('{"a":1,"a":2}')
            with self.assertRaises(ValueError):r.load(path)
if __name__=='__main__':unittest.main()
