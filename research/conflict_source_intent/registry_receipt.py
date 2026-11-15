"""Isolated registry-only contract; not imported by any product route."""
import copy, hashlib, math, re, time, uuid
from types import SimpleNamespace
from mcis_service.common.context import problem
from mcis_service.reports.access import begin
from mcis_service.interviews.access import source
from mcis_service.redaction.gateway import require
from mcis_service.evidence.service import custody_events, derive
from mcis_service.timeline.revisions import digest


class RegistryReceipts:
    def __init__(self, *, clock=time.monotonic):
        self.clock=clock; self.last=None; self.saved={}

    def now(self):
        value=self.clock()
        if type(value) not in (int,float) or not math.isfinite(value) or self.last is not None and value<self.last:
            self.saved.clear(); raise problem(409,'RECEIPT_CLOCK','时间不可确认')
        self.last=value; return value

    @staticmethod
    def observe(s,case,role,ids,write=False):
        if s.get_bind().dialect.name!='sqlite':raise problem(503,'UNAVAILABLE','仅隔离SQLite合同')
        begin(s); require(SimpleNamespace(role=role),s,case,'timeline',write=write)
        if type(ids) is not list or not 1<=len(ids)<=8 or any(type(k) is not str or not k or len(k)>64 for k in ids) or len(set(ids))!=len(ids):
            raise problem(422,'SOURCE_SET','来源集合无效')
        docs={k:source(s,case,role,k) for k in ids}
        result={}
        for k,d in docs.items():
            events=custody_events(s,case,k)
            current=derive(d,events).get('currentSha256') if isinstance(d.get('sha256'),str) else None
            if d.get('caseId')!=case or not isinstance(current,str) or not re.fullmatch('[a-f0-9]{64}',current):
                raise problem(409,'SOURCE_UNKNOWN','登记版本未知，不补造')
            result[k]={'sha256':current,'registryDocSha256':digest(d),'custodyHeadSeq':events[-1].seq if events else None,
                       'custodyHeadSha256':hashlib.sha256(events[-1].line.encode()).hexdigest() if events else None,'bytesVerified':False}
        return result

    def issue(self,s,case,role,ids):
        now=self.now(); values=self.observe(s,case,role,ids)
        self.saved={k:v for k,v in self.saved.items() if now<v['expires']}
        if len(self.saved)>=64:raise problem(409,'CAPACITY','隔离回执容量已满')
        token=str(uuid.uuid4()); self.saved[token]={'case':case,'role':role,'values':copy.deepcopy(values),'expires':now+600}
        return {'receiptId':token,'kind':'registry-observation-only','sources':copy.deepcopy(values),'bytesVerified':False,'humanReadVerified':False,'identityVerified':False,'expiresAfterSeconds':600}

    def compare(self,s,case,role,ids,token):
        now=self.now(); current=self.observe(s,case,role,ids,write=True)
        if token is None:raise problem(428,'SOURCE_RECEIPT_REQUIRED','客户端需升级并取得登记视图，未保存')
        if type(token) is not str or token not in self.saved:raise problem(409,'RECEIPT_UNAVAILABLE','回执未知或失效，未保存')
        previous=self.saved[token]
        if now>=previous['expires'] or previous['case']!=case or previous['role']!=role or set(previous['values'])!=set(ids):
            raise problem(409,'RECEIPT_UNAVAILABLE','回执不适用或失效，未保存')
        if previous['values']!=current:raise problem(412,'SOURCE_CHANGED','来源登记已变化；保留草稿并重新查看比对，未保存')
        return {'registryVersionsMatch':True,'writePerformed':False,'receiptConsumed':False,'bytesVerified':False,'humanReadVerified':False}
