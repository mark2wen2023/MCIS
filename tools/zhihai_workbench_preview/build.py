"""Static synthetic snapshots of actual pilot HTML/shapers. Never runs browser JS."""
import argparse
import ast
import hashlib
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import runpy
import zipfile

ROOT = Path(__file__).resolve().parents[2]
VOID = {'meta','link','input','br','hr','img','source','area','base','embed','param','track','wbr'}
class Node:
    def __init__(self, tag, attrs=(), parent=None):
        self.tag=tag; self.attrs=dict(attrs); self.children=[]; self.parent=parent
    def text(self,value):self.children=[value]
    def render(self):
        if self.tag=='root':return ''.join(render(c) for c in self.children)
        attrs=''.join(' '+k+('="'+escape(v,quote=True)+'"' if v is not None else '') for k,v in self.attrs.items())
        return '<'+self.tag+attrs+'>'+('' if self.tag in VOID else ''.join(render(c,self.tag=='style') for c in self.children)+'</'+self.tag+'>')
def render(value,raw=False):return value.render() if isinstance(value,Node) else value if raw else escape(value)
class DOM(HTMLParser):
    def __init__(self,html):
        super().__init__(convert_charrefs=True); self.root=Node('root');self.stack=[self.root];self.ids={};self.feed(html);self.close()
    def handle_starttag(self,tag,attrs):
        node=Node(tag,attrs,self.stack[-1]);self.stack[-1].children.append(node)
        if 'id' in node.attrs:
            if node.attrs['id'] in self.ids:raise ValueError('duplicate DOM id')
            self.ids[node.attrs['id']]=node
        if tag not in VOID:self.stack.append(node)
    def handle_endtag(self,tag):
        if len(self.stack)<2 or self.stack[-1].tag!=tag:raise ValueError('unbalanced static markup: '+tag)
        self.stack.pop()
    def handle_data(self,data):self.stack[-1].children.append(data)

def shapes():
    folder=ROOT/'service/mcis_service'
    skin=runpy.run_path(str(folder/'local_review_pilot/workbench_skin.py'))
    scope={'CSS':skin['CSS'],'image_shell':skin['image_shell']}
    for p,names in [(folder/'_review_page.py',{'_review_page'}),(folder/'local_review_pilot/pages.py',{'workbench_page','image_page'})]:
        nodes=[n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef) and n.name in names]
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'<pure page shapers>', 'exec'),scope)
    return (scope['workbench_page']((folder/'local_review_pilot/workbench.html').read_text(),images=True),
            scope['image_page']((folder/'image_review/review.html').read_text()))

def static(html):
    # Strip scripts before parsing; neither reference JS nor production JS is run.
    import re
    html=re.sub(r'<script\b[^>]*>[\s\S]*?</script>','',html)
    dom=DOM(html)
    def lock(n):
        if not isinstance(n,Node):return
        n.attrs={k:v for k,v in n.attrs.items() if not k.startswith('on') and k not in ('href','src')}
        if n.tag in ('button','input','textarea','select'):n.attrs['disabled']=None
        for c in n.children:lock(c)
    lock(dom.root)
    return dom

def text(dom,id,value):dom.ids[id].text(value)
def node(tag,text_value,attrs=()):
    n=Node(tag,attrs);n.text(text_value);return n

def snapshots():
    workbench,image=shapes();empty=static(workbench);selected=static(workbench);review=static(image)
    for dom in (empty,selected,review):
        # Persistent visible disclaimer, without extra application interaction.
        def mark(n):
            if not isinstance(n,Node):return
            if n.attrs.get('class')=='tag' and n.parent and n.parent.attrs.get('class')=='hdr':n.text('纯合成静态预览 · 所有操作禁用')
            for c in n.children:mark(c)
        mark(dom.root)
    for id,value in {'context':'当前案号：SYN-PREVIEW-A','case-title':'合成案 A · 样式评审','list-status':'合成静态状态：授权清单含两案，已明确选择 A。','detail-status':'合成页面状态；未执行真实案件读取。证据数量与完成情况未评估。','stage':'取证','next':'进入本案图片核对；这是静态预览，入口不可操作。'}.items():text(selected,id,value)
    for id in ('SYN-PREVIEW-A','SYN-PREVIEW-B'):
        selected.ids['cases'].children.append(node('button',id+' · 全合成样式样例',{'disabled':None,'aria-pressed':str(id.endswith('A')).lower()}.items()))
    selected.ids['image-entry'].children=[node('a','进入本案图片文字核对（静态预览，不可操作）')]
    for id,value in {'loaded-context':'已载入案件 SYN-PREVIEW-A / 运行 OCR-合成预览 / 修订 1。仅手造页面状态，不是实际保存回执。','status':'已载入合成逐行内容；所有编辑及保存操作已禁用。','source':'来源声明（纯合成）\nPDF物理页：1\n页图关系：人工声明\n摘要：未设置，不构成原件核验','reopen-context':'静态预览不读取记录，不更新地址。','runs':'两份全合成核对记录（未查询真实列表）'}.items():text(review,id,value)
    review.ids['source'].children=[node('pre','来源声明（纯合成）\nPDF物理页：1\n页图关系：人工声明\n摘要：未设置，不构成原件核验')]
    review.ids['case'].attrs['value']='SYN-PREVIEW-A';review.ids['run'].attrs['value']='OCR-合成预览'
    for label in ('合成记录 A · 当前核对','合成记录 B · 尚未载入'):
        review.ids['run-options'].children.append(node('button',label,{'disabled':None}.items()))
    for i,value in enumerate(['合成文字：观察时间尚待独立材料核对。','合成文字：来源说明仅用于界面排版。'],1):
        article=Node('article');article.children=[node('p','第 '+str(i)+' 行 · 候选原文（全合成）'),node('textarea',value,{'disabled':None,'aria-label':'合成核对文字'}.items()),node('p','修订依据：全合成样式对照，不是调查结论。'),node('button','追加本行核对记录',{'disabled':None}.items()),node('pre','修订 1 · 静态样例；未发生保存或原件读取。')];review.ids['lines'].children.append(article)
    csp='<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'">'
    return {name:'<!doctype html>'+d.root.render().replace('<meta charset="utf-8">','<meta charset="utf-8">'+csp,1) for name,d in [('01-workbench-empty.html',empty),('02-workbench-selected.html',selected),('03-image-review.html',review)]}

def build(target):
    target=Path(target)
    target.mkdir(parents=False,exist_ok=False)
    files=snapshots()
    files['README.txt']='粤海探析 · 静态样式对照\n建议以 1440×900 查看，亦需手动检查窄屏。\n源自实际候选页面与纯页面塑形；三个状态均人工合成，脚本全部移除，所有操作禁用。\n不是实际浏览器/HTTP/权限/保存验收，无原图、语音、AI或真实案件内容。\n参考：用户11月19日 index.html；233421字节；SHA256 9abd7427923ec3eae5aa231b252c589d3c8778d01896fec8c7ede44adb6fefef。原文件未包含在制品中。\n'
    for name,value in files.items():(target/name).write_text(value)
    sums=''.join(hashlib.sha256((target/name).read_bytes()).hexdigest()+'  '+name+'\n' for name in files)
    (target/'SHA256SUMS').write_text(sums)
    with zipfile.ZipFile(target/'zhihai-evidence-preview.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
        for name in [*files,'SHA256SUMS']:z.write(target/name,name)
    return target/'zhihai-evidence-preview.zip'
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    print(build(parser.parse_args().output))
