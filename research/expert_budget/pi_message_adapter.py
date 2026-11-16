"""Isolated Pi-shaped message adapter. Synthetic input only; no Pi execution."""
from copy import deepcopy
from research.expert_budget.v2_host_protocol import V2HostProtocol
from research.expert_budget.ledger_v2 import require
from research.expert_budget.message_validation import _assistant
from research.expert_group.packet import _strict, _dump, _digest, _packet, load_packet, PACKET_SHA256, _validate


class SimulatedPiMessages:
    """Single serialized first-round turn. No lifecycle completion or resume API."""
    def __init__(self,path,meeting,issue_operation,role='regulations'):
        self.blocked=True
        self.packet=_packet(load_packet())
        self.context={'packetSha256':PACKET_SHA256,'role':role,'round':1,
                      'previousRoundOpinions':{},'simulationOnly':True}
        self.context_digest=_digest(self.context)
        self.host=V2HostProtocol(path,meeting)
        issued=self.host.handle(issue_operation,{'op':'issue','role':role,'round':1,'contextDigest':self.context_digest})
        self.ticket=issued['recordedResult']['ticketId']
        self.ordinal=0; self.waiting=None; self.pending=[]; self.used=set()
        self.tools=0; self.read=False; self.candidate=None; self.last=None
        self.blocked=False

    def _wire(self,raw):
        require(type(raw) is bytes and len(raw)<=262144 and raw.endswith(b'\n') and raw.count(b'\n')==1,'wire_framing')
        value=_strict(raw.decode('utf-8'))
        require(type(value) is dict,'message_shape')
        return value

    @staticmethod
    def _output(**fields):
        return {**fields,'dispatchAllowed':False,'newDispatchGrant':False,'executionVerified':False}

    def from_runner(self,operation_id,raw):
        try:
            require(not self.blocked and self.waiting is None,'adapter_pending_or_blocked')
            message=self._wire(raw)
            if message=={'op':'model'}:
                require(not self.pending,'pending_tools')
                ordinal=self.ordinal+1
                rid=f'{self.ticket}:model:{ordinal}'
                envelope=self.host.handle(operation_id,{'op':'model','ticketId':self.ticket,'requestId':rid})
                if envelope['duplicate'] or not envelope['simulatedReservationCommitted']:
                    self.blocked=True
                    return self._output(status='stopped',hostResult=envelope)
                self.ordinal=ordinal; self.waiting=rid
                return self._output(status='simulated_response_expected',requestId=rid,ticketId=self.ticket,
                                    operationId=operation_id,contextDigest=self.context_digest)
            if set(message)=={'op','id','name','args'} and message['op']=='tool':
                require(self.pending and message=={'op':'tool',**self.pending[0]},'tool_binding')
                require(self.tools<8,'tool_budget')
                call=self.pending[0]
                if call['name']=='read_packet':
                    require(call['args']=={},'tool_arguments')
                    result={'packet':deepcopy(self.packet),'meetingContext':deepcopy(self.context),
                            'contextDigest':self.context_digest}
                    self.read=True
                else:
                    require(self.read,'context_not_read')
                    reviews=_validate(call['args'],self.packet)
                    require(all(len(v)<=2000 for r in reviews for v in r.values()),'review_budget')
                    self.candidate=_digest({'ticketId':self.ticket,'contextDigest':self.context_digest,'reviews':reviews})
                    result={'candidateId':self.candidate,'status':'validated_unverified','factActivated':False}
                require(len(_dump(result).encode())+1<=262144,'tool_output_budget')
                self.pending.pop(0); self.tools+=1
                return self._output(status='simulated_tool_result',result=result)
            if set(message)=={'op','text'} and message['op']=='done':
                require(not self.pending and self.candidate and self.last and
                        not self.last.get('tool_calls') and message['text']==self.last['content']==
                        'COMPLETED:'+self.candidate,'completion_not_validated')
                self.blocked=True
                # No exited() declaration and no complete_declared ledger call.
                return self._output(status='lifecycle_unverified',accepted=False)
            raise ValueError('message_shape')
        except BaseException:
            self.blocked=True
            self.host.blocked=True
            raise

    def simulated_response(self,operation_id,request_id,raw):
        try:
            require(not self.blocked and self.waiting==request_id,'response_binding')
            message=self._wire(raw)
            clean,pending=_assistant(message)
            ids=[c['id'] for c in pending]
            require(len(ids)==len(set(ids)) and not any(i in self.used for i in ids),'duplicate_tool_id')
            receipt=_digest(message)  # supplied synthetic JSON, canonical UTF-8; not provider proof
            envelope=self.host.handle(operation_id,{'op':'result','ticketId':self.ticket,
                'requestId':request_id,'outcome':'received_unverified','receiptDigest':receipt})
            if envelope['duplicate']:
                self.blocked=True
                return self._output(status='stopped_duplicate',hostResult=envelope)
            self.waiting=None; self.pending=pending; self.used.update(ids); self.last=clean
            return self._output(status='simulated_response_recorded',message=clean,receiptDigest=receipt)
        except BaseException:
            self.blocked=True
            self.host.blocked=True
            raise
