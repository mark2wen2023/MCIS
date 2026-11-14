"""Independent offline checks. These are not browser or real-model tests."""
import copy
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import pytest
sys.path.insert(0,str(Path(__file__).parent))
import export_review as e
ROOT=Path(__file__).parent

class Tree(HTMLParser):
    def __init__(self): super().__init__();self.tags=[];self.data=[]
    def handle_starttag(self,tag,attrs): self.tags.append((tag,dict(attrs)))
    def handle_data(self,data): self.data.append(data)

def inputs():
    c,cs=e.load(ROOT/'jiangxin9-provisional.json');p,ps=e.load(ROOT/'jiangxin9-real-predictions.json')
    return c,cs,p,ps,e.template(c,cs,p,ps)

def cli(tmp_path,worksheet=None,prediction=None):
    c,cs,p,ps,w=inputs()
    wp=tmp_path/'worksheet.json';wp.write_text(json.dumps(w if worksheet is None else worksheet,ensure_ascii=False),encoding='utf8')
    pp=ROOT/'jiangxin9-real-predictions.json'
    if prediction is not None:
        pp=tmp_path/'predictions.json';pp.write_text(json.dumps(prediction,ensure_ascii=False),encoding='utf8')
    out=tmp_path/'out.html'
    args=[sys.executable,str(ROOT/'export_review.py'),'export','--corpus',str(ROOT/'jiangxin9-provisional.json'),'--predictions',str(pp),'--worksheet',str(wp),'--output',str(out)]
    return args,out,wp

def test_export_is_inert_and_literal():
    c,cs,p,ps,w=inputs();evil='</pre></section><img src="https://example.invalid" onerror="x">\n约  3.4\t海里 & <script>x</script>'
    w['items'][0]['note']=evil;w['items'][0]['timeAssociationNeedsCheck']=True
    raw=e.export(c,cs,p,ps,w,'d'*64).decode();t=Tree();t.feed(raw)
    forbidden={'script','a','img','form','iframe','object','embed','link','svg','math','audio','video','base'}
    assert not any(tag in forbidden for tag,attrs in t.tags)
    assert not any(key.startswith('on') or key in {'href','src','srcdoc','action','formaction','checked','value'} for tag,attrs in t.tags for key in attrs)
    assert evil in ''.join(t.data)
    assert '上方临时控件的修改不会自动进入此快照' in raw
    assert '未标记（不表示核实通过）' in raw

def test_worksheet_reorder_preserves_identity_and_originals():
    c,cs,p,ps,w=inputs();w['items'][0]['note']='note first';w['items'][:]=reversed(w['items'])
    before=copy.deepcopy((c,p,w));raw=e.export(c,cs,p,ps,w,'e'*64).decode()
    assert (c,p,w)==before
    first_id=e.template(c,cs,p,ps)['items'][0]['itemId']
    assert raw.index('备注第 1 项 · '+first_id)<raw.index('note first')<raw.index('备注第 2 项')
    assert all(e.esc(x['rationale']) in raw for x in p['predictions'])

@pytest.mark.parametrize('field', ['factVerified','reviewerId','approved','label'])
def test_no_authority_or_decision_fields(field):
    c,cs,p,ps,w=inputs();w['items'][0][field]=True
    with pytest.raises(ValueError):e.export(c,cs,p,ps,w,'f'*64)

def test_cli_changed_prediction_bytes_reject(tmp_path):
    c,cs,p,ps,w=inputs();p['predictions'][0]['rationale']+=' Additional text.'
    args,out,wp=cli(tmp_path,worksheet=w,prediction=p)
    r=subprocess.run(args,capture_output=True,text=True,timeout=10)
    assert r.returncode==2 and not out.exists()
    assert r.stderr.strip()=='{"ok":false,"errorCode":"RESEARCH_NOTES_EXPORT_REJECTED"}'

def test_cli_duplicate_worksheet_key_reject(tmp_path):
    args,out,wp=cli(tmp_path);wp.write_text('{"secret":"NO_ECHO_SECRET","secret":1}')
    r=subprocess.run(args,capture_output=True,text=True,timeout=10)
    assert r.returncode==2 and not out.exists() and 'NO_ECHO_SECRET' not in r.stdout+r.stderr

def test_cli_network_prohibited_roundtrip(tmp_path):
    c,cs,p,ps,w=inputs();w['items'][0]['note']='人工尚未核实';w['items'][0]['sourceAssociationNeedsCheck']=True
    args,out,wp=cli(tmp_path,worksheet=w)
    script="import socket,runpy,sys;socket.socket=lambda *a,**k:(_ for _ in ()).throw(AssertionError('network'));entry=sys.argv[1];sys.path.insert(0,__import__('os').path.dirname(entry));sys.argv=sys.argv[1:];runpy.run_path(entry,run_name='__main__')"
    r=subprocess.run([sys.executable,'-c',script,*args[1:]],capture_output=True,text=True,timeout=10)
    assert r.returncode==0 and r.stderr==''
    assert json.loads(r.stdout)=={'ok':True,'fileWritten':True,'caseUpdated':False,'reviewerAuthenticated':False,'modelCalled':False}
    assert e.export(c,cs,p,ps,w,hashlib.sha256(wp.read_bytes()).hexdigest())==out.read_bytes()
    assert out.stat().st_mode&0o777==0o600

def test_budget_rejects_before_write(monkeypatch):
    c,cs,p,ps,w=inputs();monkeypatch.setattr(e,'MAX_OUTPUT',8)
    with pytest.raises(ValueError):e.export(c,cs,p,ps,w,'1'*64)
