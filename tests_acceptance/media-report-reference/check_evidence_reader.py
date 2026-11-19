"""Fixed non-seed AST functions and synthetic read-only session; no app/ORM imports."""
import ast
import copy
from pathlib import Path
import re
from types import SimpleNamespace as NS
ROOT=Path(__file__).resolve().parents[2]

def nodes(path,names):
    tree=ast.parse((ROOT/path).read_text())
    selected=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
    assert {n.name for n in selected}==set(names)
    return selected

def execute(selected,env):
    prefix=ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[prefix,*selected],type_ignores=[])),'<fixed non-seed AST>','exec'),env)

class Field:
    def __init__(self,name):self.name=name
    def __eq__(self,value):return (self.name,value)
class Evidence:
    case_id=Field('case_id');key=Field('key')
class Custody:
    case_id=Field('case_id');evidence_id=Field('evidence_id');seq=Field('seq')
class Query:
    def __init__(self,model):self.model=model;self.conditions=[];self.order=None
    def where(self,*args):self.conditions.extend(args);return self
    def order_by(self,field):self.order=field.name;return self
class Guard:
    def __init__(self,s):self.s=s
    def __enter__(self):self.s.depth+=1
    def __exit__(self,*args):self.s.depth-=1
class Session:
    def __init__(self):
        self.depth=0;self.queries=[];self.no_autoflush=Guard(self);self.failure=False
        self.item=NS(case_id='C',key='E',doc={'caseId':'C','evidenceId':'E','sha256':'a'*64,'title':'DO NOT RETURN','relativePath':'synthetic-private'})
        self.events=[NS(case_id='C',evidence_id='E',seq=2,kind='Change',sha256='c'*64),NS(case_id='C',evidence_id='E',seq=1,kind='Change',sha256='b'*64)]
    def scalars(self,q):
        assert self.depth>0
        self.queries.append((q.model,q.conditions[:],q.order))
        if self.failure:raise RuntimeError('SYNTHETIC INTERNAL DETAIL MUST NOT ESCAPE')
        if q.model is Evidence:
            assert q.conditions==[('case_id','C'),('key','E')]
            return NS(first=lambda:self.item)
        assert q.model is Custody and q.conditions==[('case_id','C'),('evidence_id','E')] and q.order=='seq'
        return iter(sorted(self.events,key=lambda r:r.seq))
env=dict(re=re,select=Query,EvidenceRow=Evidence,CustodyEventRow=Custody)
execute(nodes('service/mcis_service/db.py',['get_row','get_doc']),env)
execute(nodes('service/mcis_service/evidence/service.py',['custody_events','derive','EvidenceSourceReadError','report_source_snapshot']),env)
read=env['report_source_snapshot'];Error=env['EvidenceSourceReadError']
s=Session();before=copy.deepcopy(s.item.doc);out=read(s,'C','E')
assert out=={'caseId':'C','evidenceId':'E','currentSha256':'c'*64} and s.item.doc==before
assert len(s.queries)==2 and s.depth==0
assert 'title' not in out and 'relativePath' not in out
print('PASS exact registration then filtered ordered custody -> actual derive; minimal output')
s=Session();s.item=None;assert read(s,'C','E') is None and len(s.queries)==1
s=Session();s.failure=True
try:read(s,'C','E')
except Error as e:
    assert e.code=='evidence_read_failed' and 'INTERNAL' not in str(e) and e.__suppress_context__
else:raise AssertionError('read failure was not distinguished')
for change in ('item','event'):
    s=Session()
    if change=='item':s.item.doc['caseId']='OTHER'
    else:s.events[0].case_id='OTHER'
    try:read(s,'C','E')
    except Error as e:assert e.code=='evidence_scope_mismatch'
    else:raise AssertionError('wrong case accepted')
    if change=='item':assert len(s.queries)==1
s=Session()
try:read(s,'C','')
except Error as e:assert e.code=='evidence_scope_invalid' and not s.queries
else:raise AssertionError('empty scope could remove custody filter')
print('PASS missing != sanitized read failure; wrong-case and empty scope checks; no write methods')

# Execute actual default reader method, replacing its single lazy import with the
# above extracted functions. No fake sys.modules or real service imports.
reader=nodes('service/mcis_service/reports/media_reference_reader.py',['ScopedMediaReader'])[0]
method=next(n for n in reader.body if isinstance(n,ast.FunctionDef) and n.name=='read_evidence')
imports=[n for n in ast.walk(method) if isinstance(n,ast.ImportFrom)]
assert len(imports)==1 and imports[0].module=='evidence.service'
class RemoveLocalImport(ast.NodeTransformer):
    def visit_ImportFrom(self,n):return None
method=RemoveLocalImport().visit(method)
class ProjectionError(ValueError):
    def __init__(self,code):self.code=code;super().__init__(code)
renv=dict(report_source_snapshot=read,EvidenceSourceReadError=Error,ProjectionUnavailable=ProjectionError,deepcopy=copy.deepcopy)
execute([method],renv)
s=Session();bound=NS(_session=s,case_id='C',_evidence_reader=None)
assert renv['read_evidence'](bound,'E')==out
s.failure=True
try:renv['read_evidence'](bound,'E')
except ProjectionError as e:assert str(e)=='evidence_read_failed' and e.__suppress_context__
else:raise AssertionError('default composition must block failure')
print('PASS actual default read_evidence composition (lazy import substituted, not executed)')
print('COMPLETE: pure AST/stub only, not SQLAlchemy, real permissions, HTTP or database acceptance')
