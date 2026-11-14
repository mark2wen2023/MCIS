import copy, hashlib, json, os, subprocess, sys
from pathlib import Path
from html.parser import HTMLParser
import pytest
sys.path.insert(0, str(Path(__file__).parent))
import export_review as e
ROOT=Path(__file__).parent

def inputs():
 c,cs=e.load(ROOT/'jiangxin9-provisional.json');p,ps=e.load(ROOT/'jiangxin9-real-predictions.json')
 w=e.template(c,cs,p,ps)
 return c,cs,p,ps,w

def test_blank_template_and_export():
 c,cs,p,ps,w=inputs();before=copy.deepcopy((c,p,w))
 assert len(w['items'])==8
 assert all(not x[f] for x in w['items'] for f in e.FLAGS)
 raw=e.export(c,cs,p,ps,w,'a'*64).decode()
 assert '未标记（不表示核实通过）' in raw and '案件事实' in raw
 assert cs in raw and ps in raw
 assert (c,p,w)==before
 for row in p['predictions']:assert e.esc(row['rationale']) in raw

def test_note_literal_no_script_or_auto_judgment():
 c,cs,p,ps,w=inputs();w['items'][0]['note']='</pre><script>alert(1)</script>\n约 3.4  \n海里';w['items'][0][e.FLAGS[0]]=True
 raw=e.export(c,cs,p,ps,w,'b'*64).decode()
 assert '<script>' not in raw and e.esc(w['items'][0]['note']) in raw
 assert '标记待核实' in raw

@pytest.mark.parametrize('mutation',[
 lambda w:w.update(schemaVersion=True),lambda w:w.update(corpusSha256='0'*64),
 lambda w:w.update(predictionsSha256='0'*64),lambda w:w.update(status='approved'),
 lambda w:w['items'].pop(),lambda w:w['items'].append(w['items'][0]),
 lambda w:w['items'][0].update(itemId='foreign'),lambda w:w['items'][0].update(note='x'*4001),
 lambda w:w['items'][0].update(note=1),lambda w:w['items'][0].update(timeAssociationNeedsCheck=1),
 lambda w:w['items'][0].update(timeAssociationNeedsCheck=True),lambda w:w.update(author='someone')])
def test_reject_invalid(mutation):
 c,cs,p,ps,w=inputs();mutation(w)
 with pytest.raises(ValueError):e.export(c,cs,p,ps,w,'c'*64)

def test_cli_roundtrip_and_no_overwrite(tmp_path):
 worksheet=tmp_path/'notes.json';out=tmp_path/'notes.html'
 base=[sys.executable,str(ROOT/'export_review.py')]
 args=['--corpus',str(ROOT/'jiangxin9-provisional.json'),'--predictions',str(ROOT/'jiangxin9-real-predictions.json')]
 first=subprocess.run(base+['template',*args,'--output',str(worksheet)],capture_output=True,text=True)
 assert first.returncode==0 and os.stat(worksheet).st_mode&0o777==0o600
 w=json.loads(worksheet.read_text());w['items'][0]['note']='需要核对原页';w['items'][0]['sourceAssociationNeedsCheck']=True
 worksheet.write_text(json.dumps(w,ensure_ascii=False))
 second=subprocess.run(base+['export',*args,'--worksheet',str(worksheet),'--output',str(out)],capture_output=True,text=True)
 assert second.returncode==0 and '需要核对原页' in out.read_text()
 assert json.loads(second.stdout)['caseUpdated'] is False
 content=out.read_bytes()
 third=subprocess.run(base+['export',*args,'--worksheet',str(worksheet),'--output',str(out)],capture_output=True,text=True)
 assert third.returncode==2 and out.read_bytes()==content

def test_symlink_not_overwritten(tmp_path):
 target=tmp_path/'target';target.write_text('keep');link=tmp_path/'link';link.symlink_to(target)
 with pytest.raises(FileExistsError):e.write_new(link,b'change')
 assert target.read_text()=='keep'
