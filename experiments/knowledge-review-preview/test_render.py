import json
import unittest
from html.parser import HTMLParser
from gate import Source, Invalid
from render_preview import render

class Tags(HTMLParser):
    def __init__(self): super().__init__(); self.tags=[]
    def handle_starttag(self,tag,attrs): self.tags.append((tag,dict(attrs)))

class RenderTests(unittest.TestCase):
    def setUp(self):
        self.source=Source('s','v1','Synthetic','<img src=x onerror=alert(1)>','<script>alert(1)</script>\n证据')
        self.item=dict(kind='Case',title='<iframe src=x>',claim='判断\n不是事实',citations=[dict(sourceId='s',version='v1',textSha256=self.source.text_sha256,start=0,end=len(self.source.content),quote=self.source.content)])
    def body(self,items=None): return json.dumps({'candidates':items if items is not None else [self.item]},ensure_ascii=False).encode()
    def test_content_and_markers(self):
        html=render(self.body(),[self.source]); self.assertIn('含虚构材料',html); self.assertIn('未核实',html); self.assertIn(self.source.text_sha256,html)
    def test_injection_not_markup(self):
        html=render(self.body(),[self.source]); parser=Tags();parser.feed(html)
        self.assertFalse({'script','iframe','img','a','form','button'} & {t for t,a in parser.tags})
        self.assertIn('&lt;script&gt;',html);self.assertIn('&lt;img',html)
    def test_duplicate_visible(self):
        html=render(self.body([self.item,self.item]),[self.source]);self.assertEqual(html.count('<article '),1);self.assertIn('1 条被跳过',html)
    def test_unknown_rejected(self):
        with self.assertRaises(Invalid):render(self.body(),[])
    def test_stale_rejected(self):
        self.item['citations'][0]['version']='v2'
        with self.assertRaises(Invalid):render(self.body(),[self.source])
    def test_empty(self):self.assertIn('没有新增候选',render(self.body([]),[]))
    def test_unicode_newlines_preserved(self):self.assertIn('判断\n不是事实',render(self.body(),[self.source]))
    def test_no_external_resources(self):
        parser=Tags();parser.feed(render(self.body(),[self.source]))
        self.assertFalse(any('src' in a or 'href' in a for t,a in parser.tags))
    def test_csp_and_language(self):
        parser=Tags();parser.feed(render(self.body(),[self.source]));self.assertIn(('html',{'lang':'zh-CN'}),parser.tags)
        self.assertTrue(any(a.get('http-equiv')=='Content-Security-Policy' for t,a in parser.tags))

if __name__=='__main__':unittest.main()
