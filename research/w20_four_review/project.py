"""First-round, source-bound FourChair read-only research projection."""
from copy import deepcopy
from research.expert_group.packet import _digest, _validate, GroupError, PACKET_SHA256
from research.expert_budget.four_chair import ROLES

# Fixed prompts only: no semantic classification, vote or evidence request.
REVIEW_QUESTIONS = {
    'supported': ('这处引文直接支持的是哪一项观察或陈述，是否不足以支持因果解释？',),
    'conflicted': ('冲突双方各自说了什么，各对应哪一处已列出处？',
                   '差异是否涉及时间、对象或适用范围，哪些仍待核对？'),
    'insufficient': ('现有引文缺少哪一项判断依据，为什么仍不能作出结论？',
                     '还需人工核对什么材料；在核对前应保留哪些未知？'),
}

class ProjectionError(ValueError):
    pass

def require(ok, code):
    if not ok:
        raise ProjectionError(code)

def project(receipt, host):
    """host is a test-host capture of issued tickets, never a seat-supplied credential.
    No evidence-unavailability interface exists; this function cannot request a stop.
    Only four accepted, bound first-round opinions are in this candidate's scope.
    """
    try:
        return _project(receipt, host)
    except (KeyError, TypeError, AttributeError, GroupError) as exc:
        raise ProjectionError('malformed_or_invalid_quote') from exc

def _project(r, host):
    fields = {'locatedCitationPlaceCount','sourceCountIsWeight','sourceIndependence',
      'schema','meetingId','chair','phase','opinions','summary','packetSha256',
      'simulationOnly','opinionsPersisted','resumeAllowed','executionAuthorized',
      'modelExecuted','tokenCostBudgetImplemented','hardCancellationImplemented'}
    require(type(r) is dict and set(r)==fields, 'receipt_fields')
    require(r['schema']=='mcis.four-chair-simulation.v1', 'receipt_schema')
    require(r['packetSha256']==PACKET_SHA256 and r['chair']=='海青君（软件主持协议）', 'protocol_identity')
    require(set(host)=={'meetingId','binding','generation','tickets','registry'}, 'host_shape')
    require(r['meetingId']==host['meetingId'], 'meeting_binding')
    require(r['simulationOnly'] is True and all(r[k] is False for k in
      ('opinionsPersisted','resumeAllowed','executionAuthorized','modelExecuted',
       'tokenCostBudgetImplemented','hardCancellationImplemented')), 'unverified_boundary')
    require(r['phase']=='ready' and len(r['opinions'])==4 and len(host['tickets'])==4,
            'first_round_scope')
    require(_digest(host['registry'])==host['binding']['sourceSetDigest'], 'host_source_set')
    require(type(host['generation']) is int and host['generation']>0, 'host_generation')
    rows=[]; labels={}; places=set(); attempts=set()
    for index,(op,ticket) in enumerate(zip(r['opinions'],host['tickets'])):
        require(set(op)=={'role','round','attemptId','contextDigest','reviews','simulated',
          'draftBinding','draftBindingGeneration','locatedReviewSources'}, 'opinion_fields')
        ctx=ticket['context']
        require(ticket['contextDigest']==_digest(ctx), 'host_ticket_digest')
        require(op['attemptId']==ticket['attemptId'] and op['attemptId'] not in attempts
          and op['contextDigest']==ticket['contextDigest'], 'ticket_binding')
        attempts.add(op['attemptId'])
        require(op['role']==ctx['role']==ROLES[index] and type(op['round']) is int
          and op['round']==ctx['round']==1 and op['simulated'] is True, 'seat_round')
        require(op['draftBinding']==ctx['draftBinding']==host['binding']
          and type(op['draftBindingGeneration']) is int
          and op['draftBindingGeneration']==ctx['draftBindingGeneration']==host['generation'],
          'draft_binding')
        selected=op['locatedReviewSources']
        require(selected==ctx['locatedReviewSources'], 'source_binding')
        require(set(selected)=={i['itemId'] for i in ctx['packet']['items']}, 'item_binding')
        for item,src in selected.items():
            require(src['sourceId'] in host['registry'], 'unknown_source')
            require(src=={'sourceId':src['sourceId'],**host['registry'][src['sourceId']]},
                    'source_version_binding')
            places.add((src['sha256'],src['line']))
        _validate({'reviews':op['reviews']},{'items':[
          {'itemId':item,'sourceText':src['excerpt']} for item,src in selected.items()]})
        for review in op['reviews']:
            item=review['itemId'];labels.setdefault(item,{})[op['role']]=review['label']
            rows.append({'role':op['role'],'round':1,'attemptId':op['attemptId'],
              'contextDigest':op['contextDigest'],'draftBinding':deepcopy(op['draftBinding']),
              'draftBindingGeneration':op['draftBindingGeneration'],'itemId':item,
              'declaredLabel':review['label'],'rationale':review['rationale'],
              'uncertainty':review['uncertainty'],'quote':review['quote'],
              'source':deepcopy(selected[item]),'status':'pending_human_review',
              'semanticSupportVerified':False,'factActivated':False,
              'reviewQuestions':list(REVIEW_QUESTIONS[review['label']]),
              'reviewQuestionsOrigin':'fixed_guidance_not_seat_or_human_answer'})
    expected=[]
    for round_ in (1,2):
        for item in host['tickets'][0]['context']['packet']['items']:
            ls=labels[item['itemId']] if round_==1 else {}
            expected.append({'round':round_,'itemId':item['itemId'],'labels':ls,
              'disputedLabels':len(set(ls.values()))>1,
              'missingRoles':[role for role in ROLES if role not in ls],'factVerified':False})
    require(r['summary']==expected, 'summary_mismatch')
    require(type(r['locatedCitationPlaceCount']) is int and
      r['locatedCitationPlaceCount']==len(places) and r['sourceCountIsWeight'] is False
      and r['sourceIndependence']=='NOT_ASSESSED', 'source_count_boundary')
    return {'kind':'research_four_seat_pending_projection','meetingId':r['meetingId'],
      'caseId':host['binding']['caseId'],'round':1,'phase':r['phase'],
      'status':'pending_human_review','rows':rows,'comparison':deepcopy(expected[:len(labels)]),
      'locatedCitationPlaceCount':len(places),'sourceIndependence':'NOT_ASSESSED',
      'sourceCountIsWeight':False,'consensusComputed':False,'factActivated':False,
      'identityAuthenticated':False,'modelExecutionVerified':False,'stopRequested':False,
      'hostEvidenceAvailability':'BLOCKED_NO_INTERFACE',
      'notice':'四席声明并列待人工复核；缺少可信宿主证据不可用接口，不生成停止信号。'}
