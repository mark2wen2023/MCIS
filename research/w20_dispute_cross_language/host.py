"""Actual pinned simulated FourChair/project -> two predeclared UI rows."""
import copy,hashlib,json,sys
from pathlib import Path
from unittest.mock import Mock,patch
root=Path(sys.argv[1]).resolve()
pins={'research/w20_four_review/project.py':'bc0c9b5d02cea3ea1b91968030b939756712b1b2','research/expert_budget/four_chair.py':'b428bff809cabf7d8eec700bd2e499d86da1c553','research/expert_budget/ledger.py':'cd25595ac5d04055008282ecb26a937035ab4581','research/expert_group/packet.py':'ff2018dad2d58e9fe158f503ecd71a004c20e226'}
for name,pin in pins.items():
 b=(root/name).read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==pin
sys.path.insert(0,str(root))
from research.expert_budget import four_chair as chair
from research.expert_group import packet
from research.w20_four_review.project import project
raw_fixture=Path(__file__).with_name('fixture.json').read_bytes()
assert hashlib.sha256(raw_fixture).hexdigest()=='4c6adf9de4d7cf1eabae9cf845d98b977622b6d37dfb31a6179eefc8eb9c1dac'
f=json.loads(raw_fixture)
registry={}
for s in f['sources']:
 raw=('\n'.join(s['lines'])+'\n').encode('utf-8')
 registry[s['id']]={'sha256':hashlib.sha256(raw).hexdigest(),'line':2,'locator':s['id']+'.txt#L2','excerpt':s['lines'][1]}
for i in f['items']:
 assert registry[i['sourceId']]['excerpt']==i['quote']
synthetic={'items':[{'itemId':i['id'],'sourceText':registry[i['sourceId']]['excerpt'],'citation':{'quote':i['quote']}} for i in f['items']]}
ledger=Mock()
# Existing published synthetic constructor seam; no ledger file/public packet.
with patch.object(chair,'load_packet',return_value=b'synthetic-only'),patch.object(chair,'_packet',return_value=copy.deepcopy(synthetic)),patch.object(chair,'Ledger',return_value=ledger),patch.object(chair.os,'open',return_value=101),patch.object(chair.os,'close'):
 gate=chair.FourChair('never-created',clock=lambda:0)
binding={'caseId':f['caseId'],'version':f['revision'],'draftDigest':packet._digest({'question':f['question'],'items':f['items']}),'sourceSetDigest':packet._digest(registry)}
gate.bind_draft_simulated(binding)
gate._select_review_sources_simulated(registry,{i['id']:i['sourceId'] for i in f['items']})
tickets=[]
for n,role in enumerate(chair.ROLES):
 t=gate.issue();tickets.append(copy.deepcopy(t))
 gate.submit_simulated(t['attemptId'],t['contextDigest'],[{'itemId':i['id'],'label':['supported','conflicted','insufficient','conflicted'][n],'quote':i['quote'],'rationale':i['claim'],'uncertainty':'不同合成陈述尚待核实；不判定事实或因果'} for i in f['items']])
receipt=gate.receipt()
projection=project(receipt,{'meetingId':receipt['meetingId'],'binding':binding,'generation':1,'tickets':tickets,'registry':registry})
assert len(projection['rows'])==8 and ledger.settle.call_count==4
assert projection['status']=='pending_human_review' and not projection['consensusComputed'] and not projection['factActivated']
assert all(c['disputedLabels'] for c in projection['comparison'])
ui=[]
for expected in f['items']:
 row=next(r for r in projection['rows'] if r['itemId']==expected['id'] and r['role']==expected['seat'])
 assert row['draftBinding']==binding and row['source']['sha256']==registry[expected['sourceId']]['sha256']
 ui.append({'id':row['itemId'],'seat':row['role'],'claim':row['rationale'],'sourceId':row['source']['sourceId'],'sourceSha256':row['source']['sha256'],'start':row['source']['line'],'end':row['source']['line'],'quote':row['quote']})
control={k:f[k] for k in ('caseId','revision','question','items')}
control['items']=[{**i,'sourceSha256':registry[i['sourceId']]['sha256']} for i in f['items']]
control['sources']=[{**s,'caseId':f['caseId'],'revision':f['revision'],'sha256':registry[s['id']]['sha256']} for s in f['sources']]
input_={'kind':'developer_synthetic_dispute','caseId':projection['caseId'],'revision':binding['version'],'question':f['question'],'items':ui}
print(json.dumps({'projection':projection,'input':input_,'control':control,'mocks':['constructor packet loader','ledger and constructor file open/close'],'modelExecuted':False},ensure_ascii=False))
