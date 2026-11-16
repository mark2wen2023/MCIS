"""Host-bound model request protocol. Reservation is NOT execution authorization.

Used by the fixed local fixture host; no Pi/provider transport is installed here.
The caller retains its exclusive reaper, deadline and stop checks before GRANT.
"""
from research.expert_budget.request_budget import require


class HostModelProtocol:
    def __init__(self, budget, meeting, ticket, role, round_number, context):
        self.budget = budget
        self.meeting, self.ticket, self.context = meeting, ticket, context
        self.pending = None
        self.blocked = False
        budget.bind_ticket(meeting, ticket, role, round_number, context)

    def request(self, message):
        require(type(message) is dict and set(message) == {'op', 'requestId'}, 'model_message')
        require(message['op'] == 'model', 'model_operation')
        require(not self.blocked, 'host_blocked')
        try:
            result = self.budget.reserve(self.meeting, self.ticket, self.context, message['requestId'])
        except Exception:
            self.blocked = True
            raise
        if result['newReservation']:
            self.pending = result['requestId']
        else:
            # Includes duplicates: never replay a response or issue another grant.
            self.blocked = True
        return result

    def received(self, request_id, digest):
        require(not self.blocked and self.pending == request_id, 'response_binding')
        try:
            result = self.budget.settle(self.meeting, self.ticket, self.context,
                                       request_id, 'received_unverified', digest)
        except Exception:
            self.blocked = True
            raise
        self.pending = None
        return result

    def unknown(self):
        self.blocked = True
        # stop() conservatively marks all pending reservations unknown. If commit
        # fails, do not claim the state is durable and do not retry this operation.
        self.budget.stop(self.meeting)
        self.pending = None
