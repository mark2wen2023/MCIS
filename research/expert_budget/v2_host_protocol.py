"""Serialized simulated host using only revision-3 ledger. No dispatch or resume."""
import re
from research.expert_budget.ledger_v2 import NewMeetingLedger, inspect_v2, require


class V2HostProtocol:
    def __init__(self, path, meeting_id):
        self.blocked = True
        self.ledger = NewMeetingLedger(path, meeting_id)
        self.path, self.meeting = path, meeting_id
        self.blocked = False

    def handle(self, operation_id, message):
        """Caller retains operation IDs; never manufacture a retry ID on errors."""
        try:
            require(not self.blocked, 'host_blocked')
            require(type(message) is dict, 'message')
            op = message.get('op')
            if op == 'issue':
                require(set(message)=={'op','role','round','contextDigest'}, 'issue_shape')
                action={'type':'issue', **{k:v for k,v in message.items() if k!='op'}}
            elif op == 'model':
                require(set(message)=={'op','ticketId','requestId'}, 'model_shape')
                ticket=message['ticketId']; request=message['requestId']
                require(type(ticket) is str and type(request) is str, 'request_type')
                match=re.fullmatch(re.escape(ticket)+r':model:([1-9][0-9]{0,2})',request)
                require(match is not None, 'request_id')
                action={'type':'request','ticketId':ticket,'ordinal':int(match.group(1))}
            elif op == 'result':
                require(set(message)=={'op','ticketId','requestId','outcome','receiptDigest'}, 'result_shape')
                action={'type':'result', **{k:v for k,v in message.items() if k!='op'}}
            elif op == 'complete_declared':
                require(set(message)=={'op','ticketId'}, 'completion_shape')
                action={'type':'complete','ticketId':message['ticketId']}
            elif op == 'stop':
                require(set(message)=={'op','reason'}, 'stop_shape')
                action={'type':'stop','reason':message['reason']}
            else:
                raise ValueError('operation')
            envelope=self.ledger.apply(operation_id,action)
            # Check outer duplicate BEFORE looking at historical newReservation.
            if envelope['duplicate']:
                self.blocked=True
                return {'status':'duplicate_historical_only','duplicate':True,
                        'recordedResult':envelope['recordedResult'],
                        'simulatedReservationCommitted':False,'dispatchAllowed':False,
                        'newDispatchGrant':False,'executionVerified':False}
            result=envelope['recordedResult']
            if (result.get('status') in ('existing_no_redispatch','partial_budget_exhausted',
                                        'stopped_declared','stopped_unknown','unknown') or op=='stop'):
                self.blocked=True
            return {'status':'recorded_only','duplicate':False,'recordedResult':result,
                    'simulatedReservationCommitted':op=='model' and result.get('newReservation') is True,
                    'dispatchAllowed':False,'newDispatchGrant':False,'executionVerified':False}
        except BaseException:
            self.blocked=True
            # Includes parsing, connect, commit and interrupted-call exceptions.
            # No compensation write: a prior commit may have succeeded.
            raise

    def inspect(self):
        try:
            view=inspect_v2(self.path,self.meeting)
            if view['classification']=='blocked_unverified': self.blocked=True
            return {**view,'hostBlocked':self.blocked}
        except BaseException:
            self.blocked=True
            raise
