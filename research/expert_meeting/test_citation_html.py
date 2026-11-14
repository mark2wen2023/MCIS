from html.parser import HTMLParser
import json
import subprocess
import sys
import pytest
from research.expert_group.packet import _packet,load_packet,ROLES
from research.expert_meeting.machine import Meeting,MeetingError
from research.expert_meeting.citation_html import render


class Parsed(HTMLParser):
    def __init__(self,html):
        super().__init__();self.tags=[];self.attrs=[];self.text=[];self.feed(html)
    def handle_starttag(self,tag,attrs):self.tags.append(tag);self.attrs.extend(attrs)
    def handle_data(self,data):self.text.append(data)


def sample(outcome=None):
    m=Meeting(provider_mode='remote');m.act({'type':'start_round'})
    for index,role in enumerate(ROLES):
        t=m.act({'type':'issue_turn','roleId':role})['activeTurn']
        if index and outcome:
            m.act({'type':'fail_turn','ticketId':t['ticketId'],'outcome':outcome});break
        reviews=[dict(itemId=i['itemId'],label='supported' if index==0 else 'insufficient',quote='约',rationale='<script>alert("x")</script><img src="https://invalid.test/">',uncertainty='合成未核实 & "quoted"') for i in _packet(load_packet())['items']]
        m.act(dict(type='submit_provider_response',ticketId=t['ticketId'],contextDigest=t['contextDigest'],reviews=reviews))
    return m.export()


def test_untrusted_text_not_active_markup_and_no_external_resources():
    raw=sample();html=render(raw);p=Parsed(html)
    assert not set(p.tags)&{'script','img','iframe','form','a','link','object','embed','input'}
    assert not any(k in {'src','href','action','srcdoc'} or k.startswith('on') for k,v in p.attrs)
    assert '<script>alert' in ''.join(p.text) and '&lt;script&gt;' in html
    assert 'default-src' in html and "form-action" in html
    assert '人工编写测试主张（含反例）' in html
    assert '固定报告引文' in html and '审读者选取引文' in html
    assert '标签不同，分歧未解决' in html and '不证明真实模型执行' in html
    assert render(raw)==html


@pytest.mark.parametrize('outcome,label',[('failed','因失败停止'),('unknown','因结果未知停止')])
def test_partial_failure_is_not_complete(outcome,label):
    html=render(sample(outcome))
    assert label in html and html.count('<article>')==3
    assert '尚无完整一轮可供对照' in html
    assert '协议轮次已完成' not in html


def test_empty_and_stop():
    m=Meeting();assert '没有已接受的意见' in render(m.export())
    m.act({'type':'stop'});assert '人工停止' in render(m.export())


def test_tampered_snapshot_no_output():
    data=json.loads(sample());data['state']['phase']='completed_unverified'
    with pytest.raises(MeetingError):render(json.dumps(data).encode())
    run=subprocess.run([sys.executable,'-m','research.expert_meeting.citation_html','--render-stdin'],input=b'{}',capture_output=True)
    assert run.returncode==2 and not run.stdout


def test_explicit_cli():
    cmd=[sys.executable,'-m','research.expert_meeting.citation_html']
    assert subprocess.run(cmd,capture_output=True).returncode!=0
    raw=sample()
    result=subprocess.run(cmd+['--render-stdin'],input=raw,capture_output=True,check=True)
    assert result.stdout.decode()==render(raw)
