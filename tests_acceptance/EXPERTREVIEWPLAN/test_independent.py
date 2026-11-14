import json,hashlib,socket
from html.parser import HTMLParser
import pytest
from research.expert_meeting.machine import Meeting,MeetingError
from research.expert_meeting.review_plan import review_plan
from research.expert_meeting.citation_html import render
from research.expert_group.packet import ROLES,_packet,load_packet
@pytest.fixture(autouse=True)
def deny(monkeypatch):monkeypatch.setattr(socket.socket,'connect',lambda *a,**k:pytest.fail('network'))
def add(m,role,label='supported'):
 t=m.act({'type':'issue_turn','roleId':role})['activeTurn']
 m.act(dict(type='submit_simulated',ticketId=t['ticketId'],contextDigest=t['contextDigest'],reviews=[dict(itemId=i['itemId'],quote='约',label=label,rationale='</pre><img src=x onerror=alert(1)>',uncertainty='SYNTHETIC <script>bad</script>') for i in _packet(load_packet())['items']]))
def second():
 m=Meeting();m.act({'type':'start_round'});add(m,ROLES[0]);add(m,ROLES[1]);m.act({'type':'start_round'});return m
@pytest.mark.parametrize('count',[0,1,2])
def test_current_round_not_backfilled_and_all_pending(count):
 m=second()
 for role in ROLES[:count]:add(m,role)
 raw=m.export();v=review_plan(raw)
 assert v['currentRound']==2 and v['status']=='pending_human_review'
 for task in v['tasks']:
  assert task['round']==2 and len(task['opinions'])==count and task['missingRoles']==list(ROLES[count:])
  assert task['status']=='pending_human_review' and 'human_review_required' in task['reasonCodes']
  assert task['taskId']==hashlib.sha256(raw).hexdigest()+':'+task['itemId']
  assert task['factActivated'] is False and task['semanticSupportVerified'] is False
 assert not v['identityAuthenticated'] and not v['modelExecutionVerified'] and not v['consensusComputed']
 assert m.export()==raw
@pytest.mark.parametrize('outcome',['failed','unknown','stop','timeout'])
def test_terminal_does_not_close_tasks(outcome):
 m=second();t=m.act({'type':'issue_turn','roleId':ROLES[0]})['activeTurn']
 if outcome=='stop':m.act({'type':'stop'})
 elif outcome=='timeout':m._clock=lambda:m._started+600;m.act({'type':'tick'})
 else:m.act({'type':'fail_turn','ticketId':t['ticketId'],'outcome':outcome})
 p=review_plan(m.export());assert p['phase']==m.snapshot()['phase']
 assert all(t['status']=='pending_human_review' and t['opinions']==[] and 'no_current_opinion' in t['reasonCodes'] for t in p['tasks'])
def test_byte_binding_changes_and_copy_isolation():
 m=second();raw=m.export();p=review_plan(raw);other=review_plan(json.dumps(json.loads(raw),indent=2).encode())
 assert p['tasks'][0]['taskId']!=other['tasks'][0]['taskId']
 p['tasks'][0]['sourceLocator']['url']='changed';assert review_plan(raw)['tasks'][0]['sourceLocator']['url']!='changed'
 data=json.loads(raw);data['state']['packetSha256']='0'*64
 with pytest.raises(MeetingError):review_plan(json.dumps(data).encode())
def test_ready_zero_round_and_difference_reasons():
 p=review_plan(Meeting().export());assert p['currentRound']==0 and all(t['missingRoles']==list(ROLES) for t in p['tasks'])
 m=Meeting();m.act({'type':'start_round'});add(m,ROLES[0]);add(m,ROLES[1],'insufficient')
 p=review_plan(m.export());assert all('different_labels' in t['reasonCodes'] and 'declared_insufficient' in t['reasonCodes'] for t in p['tasks'])
def test_readonly_html_no_active_elements():
 class Parser(HTMLParser):
  def __init__(self):super().__init__();self.tags=[];self.text=[]
  def handle_starttag(self,t,a):self.tags.append((t,dict(a)))
  def handle_data(self,d):self.text.append(d)
 m=second();add(m,ROLES[0]);p=Parser();p.feed(render(m.export()));text=''.join(p.text)
 assert '人工复核问题清单（全部待复核）' in text and '仅列当前轮次待办' in text
 assert '不认证审查人' in text and '</pre><img src=x onerror=alert(1)>' in text
 assert not ({t for t,a in p.tags}&{'input','button','script','img','a','iframe','form'})
 assert not any(k.startswith('on') or k in {'src','href','action'} for t,a in p.tags for k in a)
