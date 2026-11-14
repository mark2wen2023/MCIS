"""Explicit durable working-history host. Not compatible with ephemeral UI RPC."""
import threading
import uuid
from . import host_extraction as h,extraction,extraction_working_store as store

PROFILE='mcis-extraction-review-persistent-trial-v1'
class PersistentExtractionReviewHost:
    def __init__(self,*,db,settings,session_token,case_id,record_id,provider=None):
        if provider is not None and type(provider) not in (h.FixtureProvider,h.LocalProvider):raise ValueError()
        self.__args=(db,settings,session_token,case_id,record_id)
        self.__binding=h.describe(*self.__args)['bindingDigest'];self.__provider=provider
        self.__context=str(uuid.uuid4());self.__case=case_id;self.__record=record_id
        self.__closed=False;self.__busy=False;self.__lock=threading.RLock()
    @property
    def scope(self):return {'profile':PROFILE,'contextId':self.__context,'caseId':self.__case,'recordId':self.__record,'productionLogin':False}
    def close(self):
        with self.__lock:self.__closed=True;self.__args=None;self.__provider=None
    def __enter__(self):
        if self.__closed:raise ValueError('closed')
        return self
    def __exit__(self,*args):self.close()
    def _check(self):
        if self.__closed:raise ValueError('closed')
        if h.describe(*self.__args)['bindingDigest']!=self.__binding:raise ValueError('current source binding changed')
    def generate(self,operation_id):
        with self.__lock:
            self._check()
            if self.__busy:raise ValueError('busy')
            self.__busy=True;args=self.__args;provider=self.__provider
        try:
            key=extraction.digest({'mode':'none'} if provider is None else {'mode':'fixture','content':provider.content} if type(provider) is h.FixtureProvider else {'mode':'local','url':provider.config.base_url,'model':provider.config.model})
            found=store.find_generated(*args,operation_id,self.__binding,key)
            if found:
                with self.__lock:self._check();return found
            result=h.run(*args,self.__binding,provider)
            with self.__lock:
                self._check()
                if result['status']=='not_connected':return result
                return store._save_generated(*args,operation_id,self.__binding,result,provider_key=key)
        finally:
            with self.__lock:self.__busy=False
    def read(self,proposal_id):
        with self.__lock:
            self._check();db,settings,token,case,record=self.__args
            result=store.read(db,settings,token,case,proposal_id)
            if result['recordId']!=record:raise ValueError('record scope mismatch')
            return result
    def review(self,proposal_id,operation_id,expected_revision,decisions):
        with self.__lock:
            self._check();db,settings,token,case,record=self.__args
            if store.read(db,settings,token,case,proposal_id)['recordId']!=record:raise ValueError('record scope mismatch')
            return store.append_review(db,settings,token,case,proposal_id,operation_id,expected_revision,decisions)
    def list(self):
        with self.__lock:
            self._check();db,settings,token,case,record=self.__args
            result=store.list_records(db,settings,token,case)
            result['items']=[x for x in result['items'] if x['recordId']==record]
            return result
