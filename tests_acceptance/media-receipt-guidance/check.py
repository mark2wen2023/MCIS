"""Read only named source; parse HTML, shape with import-free helper; no app import."""
import ast
import json
import subprocess
from pathlib import Path
from html.parser import HTMLParser
BASE='79614d26ae36837006b40371261c51b967037e81'
class Page(HTMLParser):
    def __init__(self):
        super().__init__();self.inputs={};self.labels={};self.label=None;self.text='';self.guide=False;self.guidance=''
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='label':self.label=True;self.text=''
        if tag=='p' and a.get('id')=='receipt-guidance':self.guide=True
        if tag=='input':
            self.inputs[a.get('id')]=a
            if self.label:self.labels[a.get('id')]=self.text
    def handle_endtag(self,tag):
        if tag=='label':self.label=None
        if tag=='p':self.guide=False
    def handle_data(self,data):
        if self.label:self.text+=data
        if self.guide:self.guidance+=data
scope={}
tree=ast.parse(Path('service/mcis_service/_review_page.py').read_text())
assert not any(isinstance(n,(ast.Import,ast.ImportFrom)) for n in ast.walk(tree))
exec(compile(tree,'<pure HTML helper>','exec'),scope)
pages={}
for media,fields in [('image',{'pdf':'PDF','image':'页图 PNG','raw':'原始 OCR 输出 JSON','candidate':'候选 JSON'}),('audio',{'audio-digest':'原音 WAV','draft-digest':'机器草稿 JSON'})]:
    path=f'service/mcis_service/{media}_review/review.html'
    source=Path(path).read_text();old=subprocess.check_output(['git','show',BASE+':'+path],text=True)
    assert source.split('<script>')[1]==old.split('<script>')[1], 'all executable JS including request bodies must be byte-identical'
    for enabled in [True,False]:
        html=scope['_review_page'](source,task_routes=enabled);p=Page();p.feed(html)
        for id,name in fields.items():
            assert p.labels[id]==name+' · 请求摘要'
            assert p.inputs[id]['aria-describedby']=='receipt-guidance'
        for words in ['同案','已核对登记回执','请求摘要','requestDigest','不要复制','原件 SHA-256','sourceSha256','尚未确认','不能凭格式判断']:
            assert words in p.guidance
        assert '归档' in html
        pages[media+('-full' if enabled else '-limited')]=html
print('HTML labels/descriptions and complete JS byte identity: PASS',flush=True)
subprocess.run(['node','tests_acceptance/media-receipt-guidance/page.cjs'],input=json.dumps(pages),text=True,check=True)
