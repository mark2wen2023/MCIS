"""Research ONLY: supplied-SHA metadata registration, no files or production routes.
No verifier implementation: synthetic providers belong to tests, never a default.
"""
import json,re,uuid
from dataclasses import dataclass
from datetime import datetime,timezone
from types import SimpleNamespace
from sqlalchemy import text
from mcis_service.common.context import problem
from mcis_service.common import contracts
from mcis_service.db import WRITE_LOCK,get_doc,put_doc
from mcis_service.cases.service import load_case
from mcis_service.evidence.models import EvidenceRow
from mcis_service.evidence import service
from mcis_service.redaction.gateway import require,get_policy,filter_evidence,level_of

@dataclass(frozen=True)
class Actor:
    issuer:str
    subject:str
    expires_at:datetime

@dataclass(frozen=True)
class Grant:
    issuer:str
    subject:str
    case_id:str
    generation:str
    role:str
    action:str='evidence.register-metadata'

def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)

def install_schema(db):
    """Explicit test setup, not create_app migration."""
    with db.engine.begin() as c:
        c.exec_driver_sql('CREATE TABLE research_registration_receipts (scope TEXT NOT NULL,request_id TEXT NOT NULL,binding TEXT NOT NULL,receipt TEXT NOT NULL,PRIMARY KEY(scope,request_id))')
        for operation in ('UPDATE','DELETE'):
            c.exec_driver_sql(f"CREATE TRIGGER research_receipts_no_{operation.lower()} BEFORE {operation} ON research_registration_receipts BEGIN SELECT RAISE(ABORT,'immutable research receipt'); END")

class Registration:
    def __init__(self,db,*,store_epoch,verifier=None,authorizer=None):
        self.db=db;self.store_epoch=store_epoch;self.verifier=verifier;self.authorizer=authorizer
    def actor(self,credential):
        if not self.verifier or not self.authorizer or not isinstance(self.store_epoch,str) or not self.store_epoch:
            raise problem(503,'TRUST_UNAVAILABLE','可信身份、案件授权与存储代次尚未配置')
        try:a=self.verifier.verify(credential)
        except Exception:raise problem(503,'VERIFIER_UNAVAILABLE','身份验证不可用') from None
        if type(a) is not Actor or not isinstance(a.issuer,str) or not 1<=len(a.issuer)<=256 or not isinstance(a.subject,str) or not 1<=len(a.subject)<=128 or not isinstance(a.expires_at,datetime) or a.expires_at.tzinfo is None or a.expires_at<=datetime.now(timezone.utc):
            raise problem(401,'UNVERIFIED','无有效可信身份')
        return a
    def authorize(self,s,a,case,expected_generation):
        try:g=self.authorizer.authorize(a,case,s)
        except Exception:raise problem(503,'AUTHORIZATION_UNAVAILABLE','案件授权不可用') from None
        if (type(g) is not Grant or g.issuer!=a.issuer or g.subject!=a.subject or g.case_id!=case
            or g.role not in ('Investigator','LeadInvestigator') or g.action!='evidence.register-metadata'):
            raise problem(403,'FORBIDDEN','无案件登记授权')
        if not isinstance(g.generation,str) or not g.generation or g.generation!=expected_generation:raise problem(409,'CASE_EPOCH_CHANGED','案件代次变化，禁止旧请求重放')
        if a.expires_at<=datetime.now(timezone.utc):raise problem(401,'UNVERIFIED','身份已失效')
        load_case(s,case);require(SimpleNamespace(role=g.role),s,case,'evidence_meta',write=True)
        policy=get_policy(s,case)
        if not filter_evidence([{'confidentiality':'Restricted'}],g.role,policy) or level_of(policy,g.role,'testimony') not in ('ReadOnly','ReadWrite'):
            raise problem(403,'FORBIDDEN','无受限登记访问权限')
        return g
    def validate(self,case,key,metadata):
        try:
            if str(uuid.UUID(key))!=key:raise ValueError()
            required={'title','source','extractedBy','extractedUtc','sha256','category','confidentiality','note'}
            if not isinstance(metadata,dict) or set(metadata)!=required or metadata['confidentiality']!='Restricted' or not isinstance(metadata['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',metadata['sha256']):raise ValueError()
        except (ValueError,TypeError,AttributeError):raise problem(422,'METADATA_ONLY','仅接受明确SHA与声明；禁止文件内容或路径') from None
        item={'caseId':case,'evidenceId':'EV-000','relativePath':'',**metadata}
        contracts.validate('evidence-item',item)
        return item
    def lookup(self,s,scope,key,binding,template):
        row=s.execute(text('SELECT binding,receipt FROM research_registration_receipts WHERE scope=:s AND request_id=:k'),{'s':scope,'k':key}).first()
        if row is None:return None
        if row.binding!=binding:raise problem(409,'REQUEST_CONFLICT','幂等标识绑定不同声明，不会覆盖')
        result=json.loads(row.receipt);item=get_doc(s,EvidenceRow,template['caseId'],result['evidenceId'])
        if item is None or {**item,'evidenceId':'EV-000'}!=template:raise problem(409,'RECEIPT_INTEGRITY','存在已提交回执，但当前登记不一致；不能断言未提交')
        events=service.custody_events(s,template['caseId'],result['evidenceId'])
        regs=[e for e in events if e.kind=='Register']
        if len(regs)!=1 or regs[0].sha256!=template['sha256'] or any(e.kind=='Change' for e in events):raise problem(409,'RECEIPT_INTEGRITY','登记保管记录不一致')
        return result
    def run(self,case,generation,key,metadata,credential,*,recover=False,fault=None):
        a=self.actor(credential);template=self.validate(case,key,metadata)
        with WRITE_LOCK,self.db.session() as s:
            if s.get_bind().dialect.name!='sqlite':raise problem(503,'SQLITE_ONLY','隔离研究仅支持SQLite')
            s.connection().exec_driver_sql('BEGIN IMMEDIATE')
            g=self.authorize(s,a,case,generation)
            scope=canonical([self.store_epoch,a.issuer,a.subject,case,g.generation])
            binding=canonical({'operation':'metadata-register-v1','scope':scope,'metadata':template})
            found=self.lookup(s,scope,key,binding,template)
            if found:return found
            if recover:return {'state':'unresolved','automaticRetry':False,'automaticDelete':False}
            if fault:fault('authorized')
            item={**template,'evidenceId':service.next_id(s,case)}
            put_doc(s,EvidenceRow,case,item['evidenceId'],item)
            if fault:fault('evidence_inserted')
            service.append_custody(s,case_id=case,evidence_id=item['evidenceId'],kind='Register',operator=a.subject,role=g.role,sha256=item['sha256'],detail='Synthetic metadata-only idempotency research; no content stored',item=item)
            if fault:fault('audit_inserted')
            result={'state':'committed','requestId':key,'caseId':case,'generation':generation,'evidenceId':item['evidenceId'],'sha256':item['sha256'],'contentStored':False,'prototypeOnly':True}
            s.execute(text('INSERT INTO research_registration_receipts VALUES (:s,:k,:b,:r)'),{'s':scope,'k':key,'b':binding,'r':canonical(result)})
            if fault:fault('before_commit')
        # Any exception here/commit acknowledgement is unknown until reconciliation.
        if fault:fault('after_commit_ack')
        return result
