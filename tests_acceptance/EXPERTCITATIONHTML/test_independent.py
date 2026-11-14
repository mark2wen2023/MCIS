import io,json,hashlib,socket
from html.parser import HTMLParser
import pytest
from research.expert_meeting import citation_html as h
from research.expert_meeting.machine import Meeting,MAX_SNAPSHOT
from research.expert_group.packet import ROLES,_packet,load_packet
BAD='</pre><script>alert(1)</script><img src="https://invalid.example/" onerror="x"> & " \' 🚢'
class Page(HTMLParser):
    def __init__(self,s):super().__init__();self.tags=[];self.text=[];self.feed(s)
    def handle_starttag(self,t,a):self.tags.append((t,dict(a)))
    def handle_data(self,d):self.text.append(d)
@pytest.fixture(autouse=True)
def block(monkeypatch):monkeypatch.setattr(socket.socket,'connect',lambda *a,**k:pytest.fail('network'))
def accepted(m,role,label='supported'):
    t=m.act({'type':'issue_turn','roleId':role})['activeTurn']
    m.act(dict(type='submit_provider_response',ticketId=t['ticketId'],contextDigest=t['contextDigest'],reviews=[dict(itemId=i['itemId'],label=label,quote='约',rationale=BAD,uncertainty=BAD) for i in _packet(load_packet())['items']]))
def partial():
    m=Meeting(provider_mode='remote');m.act({'type':'start_round'});accepted(m,ROLES[0]);return m

def test_complete_is_unverified_with_both_rounds_and_escaped_content():
    m=partial();accepted(m,ROLES[1],'conflicted');m.act({'type':'start_round'});accepted(m,ROLES[0]);accepted(m,ROLES[1]);raw=m.export();html=h.render(raw);p=Page(html);text=''.join(p.text)
    assert len([t for t,a in p.tags if t=='article'])==12
    assert '协议轮次已完成，意见仍未核实' in text and '标签相同，但不是共识' in text and '标签不同，分歧未解决' in text
    assert '远端协议声明（不证明调用）' in text and '人工编写测试主张（含反例）' in text
    assert BAD in text and hashlib.sha256(raw).hexdigest() in text
    assert not ({t for t,a in p.tags}&{'script','img','iframe','form','a','link','base','object','embed'})
    assert not any(k.lower().startswith('on') or k in {'href','src','action','srcset'} for t,a in p.tags for k in a)
    csp=next(a['content'] for t,a in p.tags if a.get('http-equiv')=='Content-Security-Policy')
    assert "default-src 'none'" in csp and "form-action 'none'" in csp and "base-uri 'none'" in csp
    assert m.export()==raw

@pytest.mark.parametrize('phase',['failed','unknown','stop','timeout'])
def test_partial_phase_and_no_missing_role_invention(phase):
    m=partial();t=m.act({'type':'issue_turn','roleId':ROLES[1]})['activeTurn']
    if phase=='stop':m.act({'type':'stop'})
    elif phase=='timeout':m._clock=lambda:m._started+600;m.act({'type':'tick'})
    else:m.act({'type':'fail_turn','ticketId':t['ticketId'],'outcome':phase})
    p=Page(h.render(m.export()));text=''.join(p.text)
    assert len([t for t,a in p.tags if t=='article'])==3
    assert {'failed':'因失败停止','unknown':'因结果未知停止','stop':'人工停止','timeout':'已超时'}[phase] in text
    assert '不推断缺席方意见' in text and '审读者声明标签（不是事实裁定）' in text
    assert 'ambiguous_exact_matches' in text and 'UTF-16' in text

@pytest.mark.parametrize('raw',[b'{}',b'\xff',b'x'*(MAX_SNAPSHOT+1)])
def test_cli_invalid_emits_no_html_and_bounded_read(monkeypatch,raw):
    class Reader:
        def read(self,n):assert n==MAX_SNAPSHOT+1;return raw
    class Input:buffer=Reader()
    class Output:buffer=io.BytesIO()
    monkeypatch.setattr(h.sys,'stdin',Input());out=Output();monkeypatch.setattr(h.sys,'stdout',out)
    assert h.main(['--render-stdin'])==2 and out.buffer.getvalue()==b''

def test_ready_empty_and_cli_success(monkeypatch):
    raw=Meeting().export()
    class Stream:
        def __init__(self,b=b''):self.buffer=io.BytesIO(b)
    out=Stream();monkeypatch.setattr(h.sys,'stdin',Stream(raw));monkeypatch.setattr(h.sys,'stdout',out)
    assert h.main(['--render-stdin'])==0
    p=Page(out.buffer.getvalue().decode());assert '没有已接受的意见；未生成替代回答。' in ''.join(p.text)
    assert not any(t=='article' for t,a in p.tags)

def test_cli_flag_required_and_projection_cannot_replace_snapshot():
    with pytest.raises(SystemExit) as e:h.main([])
    assert e.value.code==2
    with pytest.raises(Exception):h.render(json.dumps({'kind':'offline_meeting_citation_projection','rows':[],'authenticityVerified':True}).encode())
