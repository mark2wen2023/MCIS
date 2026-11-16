"""First-round synthetic wire adapter; no runner, provider or dispatch."""
from research.expert_budget.single_seat_messages import SingleSeatMessages, wire
from research.expert_budget.four_seat_transcript import FourSeatTranscriptLedger, context_for
from research.expert_budget.ledger_v2 import require, digest
from research.expert_budget.message_validation import _assistant


class FourSeatMessages(SingleSeatMessages):
    def __init__(self, path, meeting):
        self.blocked = True
        self.path, self.meeting = path, meeting
        self.ledger = FourSeatTranscriptLedger(path, meeting)
        self.blocked = False

    @staticmethod
    def output(**fields):
        return {**fields, 'contractRevision': 5, 'dispatchAllowed': False,
                'newDispatchGrant': False, 'executionVerified': False}

    def _state(self):
        require(not self.blocked, 'owner_blocked')
        view = self.inspect()
        require(view.get('contractRevision') == 5 and 'state' in view, 'snapshot_unknown')
        return view['state']

    def _active(self, ticket):
        state = self._state()
        require(state['status'] == 'open' and state['turns'] and
                state['turns'][-1]['ticketId'] == ticket and
                state['turns'][-1]['status'] == 'active', 'active_ticket')
        return state, state['turns'][-1], state['transcripts'][ticket]

    def issue_simulated(self, operation, role):
        try:
            self._state()
            result = self._commit(operation, {'type': 'context', 'context': context_for(role)})
            return self.output(status='duplicate_historical_only' if result is None else 'simulated_ticket_recorded',
                               recordedResult=result)
        except BaseException:
            self.blocked = True
            raise

    def seal_simulated(self, operation, ticket, candidate_digest):
        try:
            self._active(ticket)
            result = self._commit(operation, {'type': 'seal', 'ticketId': ticket,
                                              'candidateDigest': candidate_digest})
            view = self.inspect()
            require('state' in view, 'snapshot_unknown')
            if view['state']['status'] != 'open':
                self.blocked = True
            return self.output(status='duplicate_historical_only' if result is None else 'sealed_simulated_unverified',
                               expertCompleted=False, recordedResult=result)
        except BaseException:
            self.blocked = True
            raise

    def from_runner(self, operation, ticket, request_id, raw):
        try:
            _, turn, transcript = self._active(ticket)
            message = wire(raw)
            if message == {'op': 'model'}:
                ordinal = len(turn['requests']) + 1
                require(request_id == f'{ticket}:model:{ordinal}', 'request_binding')
                result = self._commit(operation, {'type': 'request', 'ticketId': ticket, 'ordinal': ordinal})
                return self.output(status='duplicate_historical_only' if result is None else
                                   ('simulated_response_expected' if result.get('newReservation') else 'stopped'),
                                   recordedResult=result)
            if set(message) == {'op', 'id', 'name', 'args'} and message['op'] == 'tool':
                require(transcript['responses'] and transcript['responses'][-1]['requestId'] == request_id,
                        'request_binding')
                result = self._commit(operation, {'type': 'tool', 'ticketId': ticket, 'requestId': request_id,
                    'call': {k: message[k] for k in ('id', 'name', 'args')}})
                if result is None:
                    return self.output(status='duplicate_historical_only')
                return self.output(status='simulated_tool_result', result=result['toolResult'])
            if set(message) == {'op', 'text'} and message['op'] == 'done':
                require(any(r['requestId'] == request_id for r in turn['requests']), 'request_binding')
                self.blocked = True
                return self.output(status='lifecycle_unverified', accepted=False)
            raise ValueError('message_shape')
        except BaseException:
            self.blocked = True
            raise

    def simulated_response(self, operation, ticket, request_id, raw):
        try:
            self._active(ticket)
            message, _ = _assistant(wire(raw))
            result = self._commit(operation, {'type': 'response', 'ticketId': ticket,
                                               'requestId': request_id, 'message': message})
            if result is None:
                return self.output(status='duplicate_historical_only')
            saved = self._state()['transcripts'][ticket]['responses'][-1]
            require(saved['requestId'] == request_id and saved['receiptDigest'] == digest(saved['message']),
                    'recorded_response_binding')
            return self.output(status='simulated_response_recorded', message=saved['message'],
                               receiptDigest=saved['receiptDigest'])
        except BaseException:
            self.blocked = True
            raise
