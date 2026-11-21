"""Local research projection only; no ECFC/product schema, write or model."""
from copy import deepcopy
CASE='SYN-XREPO-001'
def pending(seat_note, trajectory_context, resolved):
    if seat_note['status']!='proposed_note_pending_human_review' or seat_note['saved'] or seat_note['factActivated']:
        raise ValueError('SEAT_NOT_PENDING')
    if any(r['timeReview']!='pending' or r['timeRelation']!='undetermined' for r in seat_note['summaries']):
        raise ValueError('TIME_NOT_PENDING')
    event=[];link=[];seen=set()
    for entry in resolved:
        if entry['traceability']!='LOCATED':raise ValueError('SOURCE_UNRESOLVED')
        s=entry['statement']
        if s['caseId']!=CASE or s['vesselId']!='SYN-VESSEL-A':raise ValueError('SOURCE_CONTEXT')
        if entry['recordId'] in seen:raise ValueError('DUPLICATE_SOURCE')
        seen.add(entry['recordId'])
        ref={'recordId':entry['recordId'],'file':entry['file'],'locator':entry['locator'],
             'quote':s['text'],'sourceAssertedStance':s['assertedStance'],'traceability':'LOCATED',
             'interpretation':'source assertion, not verified support or refutation'}
        if s['target']=='EV-1' and s['assertedStance']=='observation':event.append(ref)
        elif s['target']=='LINK-1' and s['assertedStance'] in ('supports','refutes'):link.append(ref)
        else:raise ValueError('SOURCE_TARGET')
    if not event:raise ValueError('EVENT_SOURCE_REQUIRED')
    polarities={r['sourceAssertedStance'] for r in link}
    review='opposed_source_assertions_pending' if polarities=={'supports','refutes'} else 'insufficient_evidence_pending'
    def item(identity,claim,sources,status):
        return {'id':identity,'claim':claim,'sources':sources,'reviewStatus':status,
                'humanSignature':None,'causalConclusion':None,'jumpAnchor':None}
    return {'scope':'synthetic research pending handoff','caseId':CASE,
        'event':item('EV-1','记录记载推力指示下降；未认定事故原因',event,'observation_pending'),
        'candidateLink':item('LINK-1','候选：供电中断→推力指示下降',link,review),
        'trajectoryContext':deepcopy(trajectory_context),
        'gaps':['来源真实性与检查方法未复核','时钟对应与事件时间关系未确认',('相反陈述未裁定' if len(polarities)>1 else '原因来源不足，不能区分机制'),'无人工签认；无确定因果或跳转锚点'],
        'saved':False,'factActivated':False}
