"""Independent synthetic fixtures; real localhost server lifecycle from W82 harness."""
import importlib.util, pathlib
p=pathlib.Path(__file__).resolve().parents[1]/'W82/harness.py'
s=importlib.util.spec_from_file_location('w82_harness_for_w5',p); h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
servers,request,payload=h.servers,h.request,h.payload
DEMO='CASE-2026-DEMO-LILY-MARY'
def case(base,cid,fictional=False):
    body=payload(cid);body.update(title='独立 W5 '+cid,isFictionalDemo=fictional)
    status,data=request(base,'/cases',body);assert status==201,(status,data)
    return body

def document(cid,rid='IR-01'):
    answer=f'SYNTHETIC-PRIVATE-{cid}-{rid}'
    sts=[];checks=[]
    for sid in ['S-confirm','S-reject','S-revise','S-recheck','S-late']:
        sts.append(dict(statementId=sid,recordId=rid,kind='Observation',subject='synthetic',summary=f'{cid}-{rid}-{sid}',claim={'valueType':'Occurrence','occurred':True},span={'round':1,'field':'Answer','start':0,'length':len(answer)},quote=answer,reviewStatus='Draft',revision=1,extractedBy='Agent'))
        if sid!='S-recheck': checks.append(dict(statementId=sid,recordId=rid,outcome='Consistent',claimedText='synthetic',observedText='synthetic observation',sourceLabel='independent test',state='PendingConfirmation',statementVersion=1))
    return dict(caseId=cid,recordId=rid,interviewee={'intervieweeId':'PERSON-1','name':'虚构测试人','role':'测试岗位','affiliation':cid+'-'+rid},startUtc='2026-11-12T09:15:00Z',turns=[{'round':1,'question':'synthetic question','answer':answer,'sensitiveFragments':[answer]}],statements=sts,crossChecks=checks)

def record(base,cid,rid='IR-01'):
    status,data=request(base,f'/cases/{cid}/interviews',document(cid,rid));assert status==201,(status,data)
    return data

def getdoc(base,cid,rid='IR-01'):
    status,data=request(base,f'/cases/{cid}/interviews/{rid}');assert status==200,(status,data)
    return data
