"""Synthetic wire-to-revision-4 adapter. No provider, process, resume or dispatch."""
from research.expert_budget.ledger_v2 import canonical, digest, inspect_v2, require
from research.expert_budget.single_seat_transcript import SingleSeatTranscriptLedger
from research.expert_budget.message_validation import _assistant
from research.expert_group.packet import _strict, PACKET_SHA256


def wire(raw):
    require(type(raw) is bytes and len(raw) <= 262144 and raw.endswith(b'\n')
            and raw.count(b'\n') == 1, 'wire_framing')
    message = _strict(raw.decode('utf-8'))
    require(type(message) is dict, 'message_shape')
    return message


def envelope(action):
    require(len(canonical(action)) <= 4096, 'action_size')
    return action


class SingleSeatMessages:
    def __init__(self, path, meeting, issue_operation):
        self.blocked = True
        self.path, self.meeting = path, meeting
        self.ledger = SingleSeatTranscriptLedger(path, meeting)
        context = {'packetSha256': PACKET_SHA256, 'role': 'regulations', 'round': 1,
                   'previousRoundOpinions': {}, 'simulationOnly': True}
        self.ledger.apply(issue_operation, envelope({'type': 'context', 'context': context}))
        self.blocked = False

    @staticmethod
    def output(**fields):
        return {**fields, 'contractRevision': 4, 'dispatchAllowed': False,
                'newDispatchGrant': False, 'executionVerified': False}

    def inspect(self):
        return {**inspect_v2(self.path, self.meeting), 'ownerBlocked': self.blocked}

    def _state(self):
        require(not self.blocked, 'owner_blocked')
        view = self.inspect()
        require(view.get('contractRevision') == 4 and 'state' in view, 'snapshot_unknown')
        state = view['state']
        require(len(state['turns']) == 1, 'single_seat')
        return state

    def _commit(self, operation, action):
        result = self.ledger.apply(operation, envelope(action))
        if result['duplicate']:
            self.blocked = True
            return None
        recorded = result['recordedResult']
        if recorded.get('status') in ('existing_no_redispatch', 'partial_budget_exhausted',
                                      'stopped_declared', 'stopped_unknown', 'unknown'):
            self.blocked = True
        return recorded

    def from_runner(self, operation, raw):
        try:
            state = self._state(); message = wire(raw)
            turn = state['turns'][0]; ticket = turn['ticketId']
            if message == {'op': 'model'}:
                action = {'type': 'request', 'ticketId': ticket, 'ordinal': len(turn['requests']) + 1}
                result = self._commit(operation, action)
                if result is None:
                    return self.output(status='duplicate_historical_only')
                return self.output(status='simulated_response_expected' if result.get('newReservation')
                                   else 'stopped', recordedResult=result)
            if set(message) == {'op', 'id', 'name', 'args'} and message['op'] == 'tool':
                responses = state['transcript']['responses']
                require(responses, 'response_missing')
                result = self._commit(operation, {'type': 'tool', 'ticketId': ticket,
                    'requestId': responses[-1]['requestId'],
                    'call': {k: message[k] for k in ('id', 'name', 'args')}})
                if result is None:
                    return self.output(status='duplicate_historical_only')
                return self.output(status='simulated_tool_result', result=result['toolResult'])
            if set(message) == {'op', 'text'} and message['op'] == 'done':
                self.blocked = True
                return self.output(status='lifecycle_unverified', accepted=False)
            raise ValueError('message_shape')
        except BaseException:
            self.blocked = True
            raise

    def simulated_response(self, operation, request_id, raw):
        try:
            state = self._state()
            message, _ = _assistant(wire(raw))
            result = self._commit(operation, {'type': 'response', 'ticketId': state['turns'][0]['ticketId'],
                                               'requestId': request_id, 'message': message})
            if result is None:
                return self.output(status='duplicate_historical_only')
            # Read only what the transaction recorded; any post-commit read error blocks.
            saved = self._state()['transcript']['responses'][-1]
            require(saved['requestId'] == request_id and saved['receiptDigest'] == digest(saved['message']),
                    'recorded_response_binding')
            return self.output(status='simulated_response_recorded', message=saved['message'],
                               receiptDigest=saved['receiptDigest'])
        except BaseException:
            self.blocked = True
            raise
