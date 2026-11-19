"""Only fixed-source AST and handwritten fakes; no application/ORM imports."""
import ast
import copy
from pathlib import Path
import subprocess
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[2]
BASE='f891c89ad4eb8453682f393c5c3a0210ee856245'
SERVICE='service/mcis_service/working_records_archive/service.py'
INTAKE='service/mcis_service/evidence_intake/router.py'
NARROW='service/mcis_service/working_records_archive/history_lookup.py'
def read(path,old=False):
 return ast.parse(subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT,text=True) if old else (ROOT/path).read_text())
def dump(n):return ast.dump(n,include_attributes=False)
def check(ok,why):
 if not ok:raise AssertionError(why)
def fn(tree,name):return next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
o,n,h=read(SERVICE,True),read(SERVICE),read(NARROW)
names=('archived_evidence','historical_only')
for name in names:check(dump(fn(o,name))==dump(fn(h,name)),'function unchanged '+name)
expanded=copy.deepcopy(n)
check(isinstance(expanded.body[-1],ast.ImportFrom) and expanded.body[-1].module=='history_lookup','compatibility re-export')
check([a.name for a in expanded.body[-1].names]==list(names),'old symbols preserved')
expanded.body[-1:]=[copy.deepcopy(fn(h,name)) for name in names]
check(dump(expanded)==dump(o),'entire service remainder unchanged')
oi,ni=read(INTAKE,True),read(INTAKE)
restored=copy.deepcopy(ni);count=0
for node in ast.walk(restored):
 if isinstance(node,ast.ImportFrom) and node.module=='working_records_archive.history_lookup':
  check(node.level==2 and [a.name for a in node.names]==list(names),'intake import names')
  node.module='working_records_archive.service';count+=1
check(count==2 and dump(restored)==dump(oi),'only two intake imports changed')
check([(x.level,x.module,[a.name for a in x.names]) for x in h.body if isinstance(x,ast.ImportFrom)]==[(0,'sqlalchemy',['select']),(2,'common.context',['problem']),(1,'models',['ArchiveImportHistoryRow'])],'narrow imports')
check(all(isinstance(x,(ast.Expr,ast.ImportFrom,ast.FunctionDef)) for x in h.body),'no module execution beyond declarations/imports')

class Signal(Exception):pass
class Field:
 def __init__(self,name):self.name=name
 def __eq__(self,value):return (self.name,value)
Row=SimpleNamespace(**{k:Field(k) for k in ('case_id','kind','evidence_id','key')})
def scenario(tree,eid=None,digest=None,mode='miss',caller=None):
 events=[];sentinel=object();failure=Signal('handmade permission marker');query_failure=Signal('handmade query marker')
 class Query:
  def where(self,*conditions):events.append(('where',conditions));return self
 def select(model):
  check(model is Row,'exact model');events.append(('select',));return Query()
 class Session:
  def __enter__(self):events.append(('enter',));return self
  def __exit__(self,*args):events.append(('exit',));return False
  def scalars(self,q):events.append(('scalars',));return self
  def first(self):
   events.append(('first',))
   if mode=='query-error':raise query_failure
   return None if mode=='miss' else sentinel
 s=Session()
 def problem(*args):events.append(('problem',args));return Signal(args)
 ns={'select':select,'ArchiveImportHistoryRow':Row,'problem':problem}
 exec(compile(ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(fn(tree,name)) for name in names],type_ignores=[])),'<pure-functions>','exec'),ns)
 if caller is None:
  result=ns['archived_evidence'](s,'SYN-CASE',evidence_id=eid,digest=digest)
  check(result is (None if mode=='miss' else sentinel),'query return identity');return events
 def require_content(session,cid,role):
  check(session is s and cid=='SYN-CASE' and role=='synthetic-role','permission args')
  events.append(('permission',))
  if mode=='denied':raise failure
 def importer(name,*args,**kwargs):
  if name in ('working_records_archive.service','working_records_archive.history_lookup'):
   return SimpleNamespace(**{k:ns[k] for k in names})
  if name=='reports.access':return SimpleNamespace(require_content=require_content)
  raise AssertionError('unexpected import '+name)
 target=copy.deepcopy(fn(oi if tree is o else ni,caller));target.decorator_list=[];target.returns=None
 for a in target.args.args:a.annotation=None
 target.args.defaults=[]
 # Execute only original historical guard prefix; remainder is replaced by an
 # explicit continuation marker, never any file read or downstream business code.
 if caller=='load_receipt':target.body=target.body[:2]+[ast.Return(ast.Constant('CONTINUE'))]
 else:
  block=target.body[0];check(isinstance(block,ast.With),'session block')
  block.body=block.body[:3]+[ast.Return(ast.Constant('CONTINUE'))];target.body=[block]
 ns.update(__builtins__={'__import__':importer},authorize=lambda *args:events.append(('authorize',)))
 exec(compile(ast.fix_missing_locations(ast.Module(body=[target],type_ignores=[])),'<guard-prefix>','exec'),ns)
 ctx=SimpleNamespace(role='synthetic-role',db=SimpleNamespace(session=lambda:s))
 try:
  result=ns[caller](ctx,s,'SYN-CASE','SYN-DIGEST') if caller=='load_receipt' else ns[caller]('SYN-CASE','SYN-EVIDENCE',ctx)
  check(mode=='miss' and result=='CONTINUE','ordinary branch preserved')
 except Signal as exc:
  if mode=='denied':check(exc is failure,'permission marker identity')
  elif mode=='query-error':check(exc is query_failure,'query marker identity')
  else:check(exc.args==((409,'ARCHIVE_HISTORY_ONLY','这是只读历史记录，不作为本次成功请求或活跃凭证'),),'unchanged 409')
 if mode=='miss':check(not any(e[0] in ('permission','problem') for e in events),'no historical permission on miss')
 if mode=='denied':check(events.count(('permission',))==1 and not any(e[0]=='problem' for e in events),'denied before history error; no details')
 if mode=='hit':check([e[0] for e in events].index('permission')<[e[0] for e in events].index('problem'),'permission before historical 409')
 if mode=='query-error':check(not any(e[0] in ('permission','problem') for e in events),'query exception propagates')
 return events
for eid,digest in [(None,None),('SYN-E',None),(None,'SYN-D'),('SYN-E','SYN-D'),('','')]:
 old=scenario(o,eid,digest);new=scenario(h,eid,digest)
 check(old==new,'query order')
 expected=[('select',),('where',(('case_id','SYN-CASE'),('kind','evidence-intake')))]
 if eid is not None:expected.append(('where',(('evidence_id',eid),)))
 if digest is not None:expected.append(('where',(('key',digest),)))
 expected.extend([('scalars',),('first',)])
 check(new==expected,'exact predicates/order, no writes')
for caller in ('load_receipt','receipt_evidence'):
 for mode in ('miss','hit','denied','query-error'):
  check(scenario(o,mode=mode,caller=caller)==scenario(h,mode=mode,caller=caller),'guard equivalence')
  print('PASS handwritten guard',caller,mode)
print('PASS full AST equivalence, imports/re-exports, five query forms and eight fake guard sequences; no ORM/real permissions executed')
