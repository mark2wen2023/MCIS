"""Validate composite local records, never authenticate a provider or expert opinion."""
from copy import deepcopy
from research.expert_meeting.machine import canonical, digest, strict, verify_snapshot
from research.expert_remote.adapter import validate_receipt as validate_provider, SCHEMA2
from research.expert_executor.executor import RUNNER_SHA

MAX_RECEIPT = 8 * 1024 * 1024

class ReceiptError(ValueError):
    pass

def check(value):
    if not value: raise ReceiptError('composite_receipt_invalid')

def count(value, maximum):
    check(type(value) is int and 0 <= value <= maximum)

def chain(events):
    check(type(events) is list and len(events) <= 128)
    previous='0'*64
    for index,event in enumerate(events,1):
        check(type(event) is dict and type(event['seq']) is int and event['seq']==index)
        check(event['previousSha256']==previous and event['sha256']==digest({k:v for k,v in event.items() if k!='sha256'}))
        previous=event['sha256']

def validate_receipt(raw):
    """Accept bytes only. Incomplete records remain incomplete; no facts/identity proof."""
    try:
        check(type(raw) is bytes and len(raw)<=MAX_RECEIPT)
        r=strict(raw)
        check(type(r) is dict and set(r)=={'schemaVersion','kind','authenticityVerified','realDeepSeekExecuted','receiptComplete','stateScope','snapshotStatus','runs','runtimeEvents','bridgeAudit','meetingSnapshot','providerMode','transportMocked','providerReceipt'})
        check(type(r['schemaVersion']) is int and r['schemaVersion']==2 and r['kind']=='actual_pi_provider_protocol_receipt')
        check(r['stateScope']=='remote_protocol_state_plus_local_process_and_transport_observations_not_identity_proof')
        check(r['snapshotStatus']=='volatile_protocol_record_not_capability_acceptance' and r['authenticityVerified'] is False)
        check(r['providerMode'] in ('remote','remote_mock'))
        check(r['transportMocked'] is (r['providerMode']=='remote_mock'))
        for name in ('receiptComplete','realDeepSeekExecuted'):check(type(r[name]) is bool)
        if r['transportMocked']:check(r['realDeepSeekExecuted'] is False)
        verified=verify_snapshot(canonical(r['meetingSnapshot']))
        check(verified['mode']=='remote_protocol_declared')
        state=r['meetingSnapshot']['state']; events=r['meetingSnapshot']['events']
        provider=validate_provider(canonical(r['providerReceipt']))
        check(provider['schema']==SCHEMA2 and provider['transportMode']==r['providerMode'])
        check(provider['meetingId']==state['meetingId'])
        if r['receiptComplete']:
            check(all(not a['worker']['processStarted'] or a['worker']['leaderReaped'] for a in provider['attempts']))
        audit=r['bridgeAudit']
        check(type(audit) is dict and set(audit)=={'mode','realPi','realModel','auditComplete','authenticityVerified','sessions','events'})
        check(audit['mode']=='remote_protocol_declared' and audit['realPi'] is False and audit['realModel'] is False and audit['authenticityVerified'] is False)
        check(type(audit['auditComplete']) is bool)
        if r['receiptComplete']:check(audit['auditComplete'])
        chain(audit['events']);chain(r['runtimeEvents'])
        check(type(audit['sessions']) is list and len(audit['sessions'])<=4)
        # Accepted/active/interrupted tickets carry the same immutable context binding.
        turns={}
        for round_ in state['rounds']:
            for response in round_['responses'].values():turns[response['ticketId']]=response['contextDigest']
        for key in ('activeTurn','interruptedTurn'):
            if state[key]:turns[state[key]['ticketId']]=state[key]['contextDigest']
        sessions={}
        for s in audit['sessions']:
            check(set(s)=={'ticketId','contextDigest','phase','modelAttempts','toolCalls'})
            check(s['ticketId'] not in sessions and turns.get(s['ticketId'])==s['contextDigest'])
            check(s['phase'] in ('ready','awaiting_exit','completed_unverified','not_accepted','unknown'))
            count(s['modelAttempts'],4);count(s['toolCalls'],8);sessions[s['ticketId']]=s
        count(sum(s['modelAttempts'] for s in sessions.values()),16)
        count(sum(s['toolCalls'] for s in sessions.values()),32)
        latest={}; bridge_by_ticket={t:[] for t in sessions}
        for e in audit['events']:
            check(e['ticketId'] in sessions)
            check(e['phase'] in {'issued','remote_model_requested','remote_model_response','tool_completed','done_awaiting_exit','exit_zero_acceptance_attempt','not_accepted'})
            s=sessions[e['ticketId']];check(e['contextDigest']==s['contextDigest'])
            count(e['modelAttempts'],s['modelAttempts']);count(e['toolCalls'],s['toolCalls'])
            prior=latest.get(e['ticketId'],(0,0))
            check(e['modelAttempts']>=prior[0] and e['toolCalls']>=prior[1])
            latest[e['ticketId']]=(e['modelAttempts'],e['toolCalls']);bridge_by_ticket[e['ticketId']].append(e)
        if audit['auditComplete']:
            for t,s in sessions.items():
                check(latest.get(t)==(s['modelAttempts'],s['toolCalls']))
                check(sum(e['phase']=='remote_model_requested' for e in bridge_by_ticket[t])==s['modelAttempts'])
                check(sum(e['phase']=='tool_completed' for e in bridge_by_ticket[t])==s['toolCalls'])
        attempts={t:[] for t in sessions}
        for a in provider['attempts']:
            check(a['ticketId'] in sessions and a['contextDigest']==sessions[a['ticketId']]['contextDigest'])
            check(a['snapshot']['events']==events[:len(a['snapshot']['events'])])
            attempts[a['ticketId']].append(a)
            requested=[e for e in bridge_by_ticket[a['ticketId']] if e['phase']=='remote_model_requested' and e['modelAttempts']==len(attempts[a['ticketId']])]
            check(len(requested)==1 and requested[0]['inputDigest']==a['inputDigest'])
        for t,aa in attempts.items():check(len(aa)<=sessions[t]['modelAttempts'])
        check(type(r['runs']) is list and len(r['runs'])<=4)
        runs={}
        for run in r['runs']:
            check(set(run)=={'ticketId','status','processStarted','exitObserved','groupKillSent','leaderReaped','runnerSha256','runtime','providerMode','realDeepSeekExecuted','receiptComplete'} | ({'pid'} if 'pid' in run else set()) | ({'errorCode'} if 'errorCode' in run else set()))
            t=run['ticketId'];check(t in sessions and t not in runs);runs[t]=run
            check(run['status'] in ('completed_unverified','not_accepted','unknown'))
            check(run['runnerSha256']==RUNNER_SHA and run['runtime']=='Pi1.5.2' and run['providerMode']==r['providerMode'])
            for key in ('processStarted','groupKillSent','leaderReaped','realDeepSeekExecuted','receiptComplete'):check(type(run[key]) is bool)
            check(run['exitObserved'] is None or type(run['exitObserved']) is int)
            if run['processStarted']:check(type(run.get('pid')) is int and run['pid']>0)
            else:check('pid' not in run and run['exitObserved'] is None and not run['leaderReaped'] and not run['groupKillSent'])
            if r['receiptComplete']:check(run['receiptComplete'])
            if run['receiptComplete'] and run['processStarted']:check(run['leaderReaped'] and run['groupKillSent'] and type(run['exitObserved']) is int)
            if r['transportMocked']:check(run['realDeepSeekExecuted'] is False)
            rr=[e for e in r['runtimeEvents'] if e['ticketId']==t]
            received=[e for e in rr if e['phase']=='provider_response_received']
            seen=set()
            for e in received:
                check(e['requestId'] not in seen);seen.add(e['requestId'])
                aa=[a for a in attempts[t] if a['requestId']==e['requestId']]
                check(len(aa)==1 and aa[0]['status']=='received_unverified' and e['responseDigest']==aa[0]['responseDigest'] and e['transportMocked'] is r['transportMocked'])
            if run['status']=='completed_unverified':
                check(run['processStarted'] and run['leaderReaped'] and run['groupKillSent'] and run['exitObserved']==0)
                check('errorCode' not in run and sessions[t]['phase']=='completed_unverified')
                aa=attempts[t];check(len(aa)==sessions[t]['modelAttempts'] and len(aa)>=2 and all(a['status']=='received_unverified' for a in aa))
                check(len(received)==len(aa))
                responses=[x for rd in state['rounds'] for x in rd['responses'].values() if x['ticketId']==t]
                check(len(responses)==1 and responses[0]['source']=='provider_response_declared')
                if r['providerMode']=='remote':check(run['realDeepSeekExecuted'] is True)
                bb=bridge_by_ticket[t]
                done=[e for e in bb if e['phase']=='done_awaiting_exit']
                commits=[e for e in bb if e['phase']=='exit_zero_acceptance_attempt']
                check(len(done)==1 and len(commits)==1 and done[0]['seq']<commits[0]['seq'])
                check(commits[0]['outputDigest']==digest(responses[0]['reviews']))
                starts=[e for e in rr if e['phase']=='process_started']
                spawns=[e for e in rr if e['phase']=='spawn_attempt']
                exits=[e for e in rr if e['phase']=='exit_zero_observed']
                check(len(starts)==len(spawns)==len(exits)==1 and starts[0]['pid']==run['pid'])
                check(spawns[0]['seq']<starts[0]['seq']<exits[0]['seq'])
                check(all(starts[0]['seq']<e['seq']<exits[0]['seq'] for e in received))
                contexts=[e for e in rr if e['phase']=='context_written_to_pipe']
                check(contexts and all(e['contextDigest']==sessions[t]['contextDigest'] for e in contexts))
                check(any(e['phase']=='exit_zero_observed' and type(e['returncode']) is int and e['returncode']==0 for e in rr))
                for i,a in enumerate(aa,1):
                    matches=[e for e in bb if e['phase']=='remote_model_response' and e['modelAttempts']==i]
                    check(len(matches)==1 and matches[0]['outputDigest']==a['responseDigest'])
            else:check(sessions[t]['phase']!='completed_unverified')
            check(run['realDeepSeekExecuted'] is (r['providerMode']=='remote' and any(a['status']=='received_unverified' for a in attempts[t])))
        for e in r['runtimeEvents']:
            check(e['ticketId'] in runs)
            check(e['phase'] in {'spawn_attempt','process_started','provider_response_received','done_received','context_written_to_pipe','exit_zero_observed','not_accepted'})
        for t,aa in attempts.items():
            if aa:check(t in runs)
        check(r['realDeepSeekExecuted'] is any(run['realDeepSeekExecuted'] for run in runs.values()))
        accepted={x['ticketId'] for rd in state['rounds'] for x in rd['responses'].values()}
        check(accepted=={t for t,run in runs.items() if run['status']=='completed_unverified'})
        return deepcopy(r)
    except (ValueError,KeyError,TypeError,AttributeError,RecursionError):
        raise ReceiptError('composite_receipt_invalid') from None
