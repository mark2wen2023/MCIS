"""Opt-in trusted Pi-to-working-history bridge. No route, auto grant or fact write."""
import copy
import threading
import uuid
from . import extraction as e, extraction_working_store as w
from .pi_transcript_remote import RemoteTranscriptHost

class PiWorkingHost:
    def __init__(self,db,settings,session_token,case_id,record_id,cfg,*,approved_disclosure_digest):
        self.__lock=threading.RLock()
        self.__args=(db,settings,session_token,case_id,record_id)
        self.__host=RemoteTranscriptHost(*self.__args,cfg,approved_disclosure_digest=approved_disclosure_digest)
        self.__binding=self.__host._binding
        self.__run=str(uuid.uuid4());self.__closed=False;self.__accepted=None;self.__payload=None;self.__trace=[]

    def dispatch(self,envelope):
        with self.__lock:
            if self.__closed or self.__accepted is not None:raise ValueError('Pi working run closed')
            try:
                result=self.__host.dispatch(envelope)
                event={'op':envelope['op']}
                if envelope['op']=='tool':
                    event['tool']=envelope['name']
                    event['outcome']='validated' if result.get('status')=='PendingReview' else 'invalid' if result.get('status')=='invalid' else 'read'
                self.__trace.append(event)
                if len(self.__trace)>32:raise ValueError('Pi trace limit')
                if envelope['op']=='final':
                    self.__payload=envelope['payload']
                    self.__accepted=copy.deepcopy(result)
                return copy.deepcopy(result)
            except Exception:
                self.close();raise

    def __validate(self,result,snapshot,record_id):
        # Called within the existing write transaction after source/auth checks.
        if self.__accepted is None or self.__payload is None or result!=self.__accepted:raise ValueError('No accepted Pi result')
        binding,record,policy,scope=snapshot
        parsed=e.parse_output(self.__payload,record)
        proposals,citations=e.checked_statements(parsed,record,policy)
        if (result['bindingDigest']!=binding or binding!=self.__binding or result['sourceScope']!=scope
                or result['proposals']!=proposals or result['citations']!=citations
                or result['status']!='PendingReview' or result['saved'] is not False
                or result['factVerified'] is not False or result['providerMode']!='remote-deepseek'
                or result['fixture'] is not False or result['inferencePerformed'] is not True):raise ValueError('Pi result mismatch')
        return w._bounded({**result,'execution':{'profile':'pi-working-trial-v1','runId':self.__run,
            'trace':copy.deepcopy(self.__trace),'outputDigest':e.digest(parsed),
            'traceMeaning':'trusted_host_protocol_metadata_not_signed_audit','runtimeIdentityVerified':False}})

    def save(self,operation_id):
        with self.__lock:
            if self.__closed or self.__accepted is None:raise ValueError('No accepted Pi result')
            return w._save_checked(*self.__args,operation_id,self.__binding,self.__accepted,
                'pi-run:'+self.__run,self.__validate)

    def close(self):
        with self.__lock:
            self.__closed=True
            if self.__host is not None:self.__host.close()
            self.__host=None;self.__accepted=None;self.__payload=None;self.__args=None
