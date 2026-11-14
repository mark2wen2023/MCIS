"""Offline independent HTML structure/content checks; not browser rendering."""
import sys,json,hashlib,subprocess,copy
from pathlib import Path
from html.parser import HTMLParser
import pytest
sys.path.insert(0,str(Path(__file__).parent))
import render_review as r
ROOT=Path(__file__).parent
class Parser(HTMLParser):
 def __init__(self):super().__init__();self.tags=[];self.text=[]
 def handle_starttag(self,t,a):self.tags.append((t,dict(a)))
 def handle_data(self,d):self.text.append(d)
def inputs():
 c,s=r.load(ROOT/'jiangxin9-provisional.json');p,_=r.load(ROOT/'jiangxin9-real-predictions.json');return c,s,p

def test_artifact_exact_regeneration_and_safe_structure():
 c,s,p=inputs();raw=r.render(c,s,p);assert raw==(ROOT/'jiangxin9-research-review.html').read_bytes()
 tree=Parser();tree.feed(raw.decode());assert len([x for x in tree.tags if x[0]=='input'])==24
 forbidden={'script','form','iframe','object','embed','img','svg','math','a','link','audio','video','base'}
 assert not any(t in forbidden for t,a in tree.tags)
 assert not any(k.lower().startswith('on') or k in {'src','href','srcdoc','action','formaction','checked','value'} for t,a in tree.tags for k in a)
 assert '未保存' in raw.decode() and '无真人身份认证' in raw.decode() and '不激活事实' in raw.decode()

@pytest.mark.parametrize('field',['rationale','claim','quote','source','locator'])
def test_all_untrusted_content_is_literal(field):
 c,s,p=inputs();evil='</pre></textarea><svg onload="alert(1)"></svg><script>x</script>&\"'
 if field=='rationale':p['predictions'][0]['rationale']=evil
 elif field=='claim':c['items'][0]['claim']=evil
 elif field=='quote':c['items'][0]['citation']['quote']=evil
 elif field=='locator':c['items'][0]['sourceLocator']['section']=evil
 else:c['items'][0]['sourceText']=evil;c['items'][0]['sourceSha256']=hashlib.sha256(evil.encode()).hexdigest()
 raw=r.render(c,s,p).decode();tree=Parser();tree.feed(raw)
 assert not any(t in {'script','svg'} or 'onload' in a for t,a in tree.tags)
 assert evil in ''.join(tree.text)

def test_suggestions_not_rendered_and_inputs_not_changed():
 c,s,p=inputs();c['items'][0]['rationale']='SUGGESTION_RATIONALE_HIDDEN';original=copy.deepcopy((c,s,p))
 raw=r.render(c,s,p).decode();assert 'SUGGESTION_RATIONALE_HIDDEN' not in raw and 'suggestedLabel' not in raw
 assert (c,s,p)==original
 for row in p['predictions']:assert r.esc(row['rationale']) in raw

def test_cli_under_network_prohibition(tmp_path):
 script="import socket,runpy,sys;socket.socket=lambda *a,**k:(_ for _ in ()).throw(AssertionError('network'));entry=sys.argv[1];sys.path.insert(0,__import__('os').path.dirname(entry));sys.argv=sys.argv[1:];runpy.run_path(entry,run_name='__main__')"
 target=tmp_path/'r.html';cmd=[sys.executable,'-c',script,str(ROOT/'render_review.py'),'--corpus',str(ROOT/'jiangxin9-provisional.json'),'--predictions',str(ROOT/'jiangxin9-real-predictions.json'),'--output',str(target)]
 result=subprocess.run(cmd,capture_output=True,text=True,timeout=10);assert result.returncode==0 and result.stderr==''
 meta=json.loads(result.stdout);assert meta['persistentReview'] is False and meta['modelCalled'] is False and meta['factActivated'] is False
 assert target.read_bytes()==(ROOT/'jiangxin9-research-review.html').read_bytes()

def test_bad_input_creates_no_output_and_hides_details(tmp_path):
 source=tmp_path/'bad';source.write_text('{"secret":"NO_ECHO_SENTINEL","secret":1}');out=tmp_path/'out'
 result=subprocess.run([sys.executable,str(ROOT/'render_review.py'),'--corpus',str(source),'--predictions',str(source),'--output',str(out)],text=True,capture_output=True,timeout=10)
 assert result.returncode==2 and not out.exists() and 'SENTINEL' not in result.stdout+result.stderr
 assert json.loads(result.stderr)['errorCode']=='RESEARCH_REVIEW_REJECTED'
