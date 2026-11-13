"""Run an explicitly synthetic panel. No LLM and no network."""
import json,tempfile
from panel_store import Store,ROLES
with tempfile.TemporaryDirectory() as root:
 s=Store(root+'/demo.db')
 s.create('demo','investigator',{'caseId':'SYNTHETIC','reportVersion':'1','reportText':'Synthetic report used only to test scheduling.','synthetic':True,'sources':{'test':{'version':'1','text':'Synthetic evidence fixture.'}}},budget=2)
 revision=0
 for role in ROLES:
  for op,payload in [('read_source',{'sourceId':'test','version':'1'}),('review',{'text':'Synthetic fixture opinion; not an actual AI output.','refs':[{'sourceId':'test','version':'1'}]})]:
   result=s.command('demo',role,str(revision),revision,op,payload);revision=result['revision']
 s.command('demo','vessel',str(revision),revision,'challenge',{'target':'review:navigation','text':'Synthetic cross-examination fixture.','refs':[]})
 print(json.dumps(s.context('demo','navigation'),ensure_ascii=False,indent=2))
