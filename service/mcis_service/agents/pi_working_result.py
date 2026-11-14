"""Strict Pi working-history shape and current-source checks. No authority from metadata."""
import copy,json,re
from . import extraction as e
from .pi_extraction_skill import validate_reference
from ..common import contracts
from ..interviews.service import utf16_len
from ..investigation.journal import canonical_id

RESULT_KEYS=set('status proposals citations saved factVerified persistentAudit bindingDigest citationMeaning sourceScope modelCalls toolCalls completionMode providerMode configuredModel modelIdentityVerified humanApprovalVerified inferencePerformed fixture execution'.split())
def keys(v,k):
    if type(v) is not dict or set(v)!=set(k.split()):raise ValueError('Pi shape')
def sha(v):
    if type(v) is not str or not re.fullmatch('[0-9a-f]{64}',v):raise ValueError('Pi hash')
def validate_shape(result,record_id,binding):
    if type(result) is not dict or set(result)!=RESULT_KEYS or len(json.dumps(result,ensure_ascii=False,allow_nan=False).encode())>512*1024:raise ValueError('Pi result')
    if result['status']!='PendingReview' or result['providerMode']!='remote-deepseek' or result['citationMeaning']!='exact_quote_match_only_not_fact_verification':raise ValueError('Pi tags')
    for k in ('saved','factVerified','persistentAudit','modelIdentityVerified','humanApprovalVerified','fixture'):
        if result[k] is not False:raise ValueError('Pi authority')
    if result['inferencePerformed'] is not True:raise ValueError('Pi inference claim')
    sha(binding)
    if result['bindingDigest']!=binding or result['sourceScope'] not in ('interview_document_only','registered_original_bytes') or result['completionMode'] not in ('exact','validated-reference'):raise ValueError('Pi binding')
    model=result['configuredModel']
    if type(model) is not str or not model.strip() or len(model)>200 or any(ord(c)<32 for c in model):raise ValueError('Pi model')
    for k,limit in [('modelCalls',4),('toolCalls',8)]:
        if type(result[k]) is not int or not 1<=result[k]<=limit:raise ValueError('Pi counts')
    x=result['execution']
    profile=x.get('profile') if type(x) is dict else None
    keys(x,'profile runId trace outputDigest traceMeaning runtimeIdentityVerified completionMode'+(' skillRef' if profile=='pi-working-trial-v2' else ''))
    if profile=='pi-working-trial-v2':validate_reference(x['skillRef'])
    if x['profile'] not in ('pi-working-trial-v1','pi-working-trial-v2') or x['traceMeaning']!='trusted_host_protocol_metadata_not_signed_audit' or x['runtimeIdentityVerified'] is not False or x['completionMode']!=result['completionMode']:raise ValueError('Pi trace tags')
    canonical_id(x['runId']);sha(x['outputDigest'])
    if type(x['trace']) is not list or not 1<=len(x['trace'])<=32:raise ValueError('Pi trace')
    state='idle';models=tools=0;read=validated=False;model_completed=False
    for index,event in enumerate(x['trace']):
        if type(event) is not dict:raise ValueError('Pi event')
        op=event.get('op');keys(event,'op tool outcome' if op=='tool' else 'op')
        if op=='model_start' and state=='idle':state='start';models+=1
        elif op=='model_request' and state=='start':state='requested'
        elif op=='model_end' and state=='requested':state='idle';model_completed=True
        elif op=='tool' and state=='idle' and model_completed:
            tools+=1
            if event['tool'] in ('read_transcript_excerpt','find_transcript_passages') and event['outcome']=='read':read=True
            elif event['tool']=='validate_extraction_proposal' and event['outcome'] in ('invalid','validated'):validated=event['outcome']=='validated'
            else:raise ValueError('Pi tool event')
        elif op=='final' and state=='idle' and index==len(x['trace'])-1 and index>0 and x['trace'][index-1]=={'op':'model_end'} and read and validated:state='final'
        else:raise ValueError('Pi trace sequence')
    if state!='final' or models!=result['modelCalls'] or tools!=result['toolCalls']:raise ValueError('Pi trace totals')
    items=result['proposals'];citations=result['citations']
    if type(items) is not list or not 1<=len(items)<=20 or type(citations) is not list:raise ValueError('Pi proposals')
    expected=[];seen=set()
    for st in items:
        keys(st,'kind subject summary claim quote recordId statementId span reviewStatus revision extractedBy');contracts.validate('interview#/$defs/statement',st)
        if st['recordId']!=record_id or st['statementId']!='pending' or st['reviewStatus']!='Draft' or type(st['revision']) is not int or st['revision']!=1 or st['extractedBy']!='Agent':raise ValueError('Pi statement')
        sp=st['span'];keys(sp,'round field start length')
        if type(sp['round']) is not int or sp['round']<1 or sp['field'] not in ('Question','Answer') or type(sp['start']) is not int or sp['start']<0 or type(sp['length']) is not int or sp['length']!=utf16_len(st['quote']) or not st['quote'].strip():raise ValueError('Pi span')
        key=(sp['round'],sp['field'],st['quote'])
        if key in seen:raise ValueError('Pi duplicate quote')
        seen.add(key);expected.append({'recordId':record_id,'round':sp['round'],'quote':st['quote']})
    if citations!=expected:raise ValueError('Pi citations')
    for c in citations:
        keys(c,'recordId round quote')
        if type(c['round']) is not int:raise ValueError('Pi citation round')
    return copy.deepcopy(result)

def validate_current(result,snapshot,record_id):
    binding,record,policy,scope=snapshot
    result=validate_shape(result,record_id,binding)
    items=[{**{k:st[k] for k in ('kind','subject','summary','claim','quote')},'round':st['span']['round'],'field':st['span']['field']} for st in result['proposals']]
    payload=e.parse_output(json.dumps({'statements':items},ensure_ascii=False),record)
    statements,citations=e.checked_statements(payload,record,policy)
    if result['sourceScope']!=scope or statements!=result['proposals'] or citations!=result['citations'] or result['execution']['outputDigest']!=e.digest(payload):raise ValueError('Pi current source')
    return result
