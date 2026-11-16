"""Isolated synthetic host: SQLite owns requests; memory owns declared turn progress.
No transport, process, credentials, recovery or execution authorization.
"""
from copy import deepcopy
import re
from research.expert_budget.stable_protocol import ROLES, _ticket, initial
from research.expert_budget.request_budget import RequestBudget, require
from research.expert_budget.host_protocol import HostModelProtocol
from research.expert_group.packet import PACKET_SHA256


class DurableHost:
    def __init__(self, path, meeting_id):
        initial(meeting_id)  # canonical UUID validation only
        # No resume: never rebuild progress around an existing ledger.
        with open(path, 'xb'):
            pass
        self.budget = RequestBudget(path)
        self.meeting = meeting_id
        self.budget.create(meeting_id, PACKET_SHA256)
        self.turns = []
        self.blocked = False
        self.consistency_unresolved = False

    def _fail(self):
        self.blocked = True
        # Do not attempt further writes after an uncertain DB operation.
        self.consistency_unresolved = True

    def issue(self, role, number, context):
        require(not self.blocked, 'host_stopped')
        require(role in ROLES and type(number) is int and number in (1,2), 'role_round')
        require(type(context) is str and re.fullmatch('[a-f0-9]{64}',context) is not None, 'context')
        ticket = _ticket(self.meeting,role,number)
        existing = [t for t in self.turns if t['ticketId']==ticket]
        if existing:
            require(existing[0]['contextDigest']==context, 'context_changed')
            return ticket
        require(len(self.turns)==(number-1)*4+ROLES.index(role) and
                all(t['status']=='completed_declared' for t in self.turns), 'chair_order')
        try:
            protocol = HostModelProtocol(self.budget,self.meeting,ticket,role,number,context)
        except Exception:
            self._fail()
            raise
        self.turns.append({'ticketId':ticket,'role':role,'round':number,
                           'contextDigest':context,'status':'active','protocol':protocol})
        return ticket

    def _turn(self,ticket):
        rows = [t for t in self.turns if t['ticketId']==ticket]
        require(len(rows)==1,'unknown_ticket')
        return rows[0]

    def request(self,ticket,ordinal):
        require(not self.blocked,'host_stopped')
        turn = self._turn(ticket)
        require(turn['status']=='active','turn_closed')
        require(type(ordinal) is int and 1 <= ordinal <= 999,'ordinal')
        try:
            result = turn['protocol'].request({'op':'model','requestId':f'{ticket}:model:{ordinal}'})
        except Exception:
            self._fail()
            raise
        if not result['newReservation']:
            self.blocked = True
            turn['status'] = ('incomplete_budget' if result['status']=='partial_budget_exhausted'
                              else 'incomplete_duplicate')
            if result['status'] != 'partial_budget_exhausted':
                try: turn['protocol'].unknown()
                except Exception:
                    self._fail()
                    raise
        # Only the existing fixed fixture's host may consume this marker, after
        # its own stop/deadline/ownership checks. No execution authority is added.
        return {**result, 'fixtureGrantReady': result['newReservation'],
                'executionVerified':False}

    def received(self,ticket,request_id,digest):
        require(not self.blocked,'host_stopped')
        turn=self._turn(ticket)
        try: return turn['protocol'].received(request_id,digest)
        except Exception:
            self._fail()
            raise

    def unknown(self,ticket):
        require(not self.blocked,'host_stopped')
        turn=self._turn(ticket)
        self.blocked=True
        turn['status']='incomplete_unknown'
        try: turn['protocol'].unknown()
        except Exception:
            self._fail()
            raise

    def complete_declared(self,ticket):
        require(not self.blocked,'host_stopped')
        turn=self._turn(ticket)
        require(turn['status']=='active','turn_closed')
        try: rows=self.budget.snapshot(self.meeting)['requests']
        except Exception:
            self._fail()
            raise
        own=[r for r in rows if r['ticket']==ticket]
        require(own and all(r['outcome']=='received_unverified' for r in own),'responses_incomplete')
        turn['status']='completed_declared'

    def summary(self):
        # Counts/outcomes come only from SQLite, never from pure-protocol copies.
        snapshot=self.budget.snapshot(self.meeting)
        seats=[]
        for number in (1,2):
            for role in ROLES:
                matches=[t for t in self.turns if t['role']==role and t['round']==number]
                status=matches[0]['status'] if matches else 'not_started'
                if matches and status=='active' and self.blocked: status='incomplete_unknown'
                seats.append({'role':role,'round':number,'status':status})
        return deepcopy({'ledger':snapshot,'seats':seats,'hostStopped':self.blocked,
                         'consistencyUnresolved':self.consistency_unresolved,
                         'executionVerified':False,'persistentMeetingRecovery':False})
