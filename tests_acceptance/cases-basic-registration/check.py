"""AST plus hand-written registration fakes. No real framework/app imports."""
import ast
import copy
from pathlib import Path
import subprocess
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2]
BASE='a8c6f3036336f8b6a408f3a731de40532aa54433'
PATH='service/mcis_service/cases/router.py'
BASIC='service/mcis_service/cases/basic_registration.py'
def check(ok,why):
 if not ok:raise AssertionError(why)
def dump(n):return ast.dump(n,include_attributes=False)
old=ast.parse(subprocess.check_output(['git','show',BASE+':'+PATH],cwd=ROOT,text=True))
new=ast.parse((ROOT/PATH).read_text());basic=ast.parse((ROOT/BASIC).read_text())
helper=next(n for n in basic.body if isinstance(n,ast.FunctionDef))
names=['list_cases','create_case','get_case']
original=[n for n in old.body if isinstance(n,ast.FunctionDef) and n.name in names]
check([dump(n) for n in helper.body[:-1]]==[dump(n) for n in original],'unaltered functions incl signatures/decorators/body')
check(dump(helper.body[-1])==dump(ast.parse('return list_cases, create_case, get_case').body[0]),'return endpoint objects')
expanded=copy.deepcopy(new)
pos=next(i for i,n in enumerate(expanded.body) if isinstance(n,ast.ImportFrom) and n.module=='basic_registration')
check(dump(expanded.body[pos+1])==dump(ast.parse('list_cases, create_case, get_case = _register_basic_cases(router)').body[0]),'old exported aliases')
expanded.body[pos:pos+2]=copy.deepcopy(original)
check(dump(expanded)==dump(old),'full router unchanged except extraction')
imports=[(n.level,n.module,tuple(a.name for a in n.names)) for n in basic.body if isinstance(n,ast.ImportFrom)]
check(imports==[(0,'__future__',('annotations',)),(0,'typing',('Any',)),(0,'fastapi',('Body',)),(2,'audit',('service',)),(2,'common',('contracts',)),(2,'common.context',('Ctx','CtxDep','problem')),(2,'db',('put_doc',)),(1,None,('service',)),(1,'models',('CaseRow',))],'basic direct import allowlist')
check(not any(isinstance(n,ast.Import) for n in ast.walk(basic)),'no hidden import')
class Marker(Exception):pass
DEP=object()

def run(tree,only_basic=False,fail=None):
 events=[];dep=DEP;marker=Marker('synthetic registration marker')
 class Router:
  def __init__(self,**kwargs):self.metadata=kwargs;self.routes=[];events.append(('router',kwargs))
  def route(self,method,path,**kwargs):
   events.append(('decorator',method,path,kwargs))
   def register(endpoint):
    events.append(('register',method,path,endpoint.__name__))
    if fail==(method,path):raise marker
    self.routes.append((method,path,kwargs,endpoint));return endpoint
   return register
  def get(self,path,**kwargs):return self.route('GET',path,**kwargs)
  def post(self,path,**kwargs):return self.route('POST',path,**kwargs)
 def Body(*args,**kwargs):
  events.append(('Body',args,kwargs))
  if fail=='definition':raise marker
  return 'synthetic-body'
 def Query(*args,**kwargs):events.append(('Query',args,kwargs));return 'synthetic-query'
 ns={'APIRouter':Router,'Body':Body,'Query':Query,'CtxDep':dep}
 # Compile only declarations, router creation and registration with fake globals.
 # Future annotations prevent evaluating ORM/type references. No imports execute.
 future=ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0)
 nodes=[future,copy.deepcopy(helper)]
 if only_basic:
  nodes+=ast.parse("router=APIRouter(prefix='/api/v1',tags=['cases'])\nlist_cases,create_case,get_case=_register_basic_cases(router)").body
 else:
  nodes += [copy.deepcopy(n) for n in tree.body if not isinstance(n,(ast.ImportFrom,ast.Import))]
 try:exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),'<fake-router>','exec'),ns)
 except Marker as exc:check(exc is marker,'same exception propagation')
 else:check(fail is None,'expected marker missing')
 router=ns['router']
 for method,path,kw,endpoint in router.routes:
  # Future FastAPI route generation sees same name/path/method, signature and
  # response annotations. Actual FastAPI operation ID generation is NOT run.
  check(endpoint.__name__ in names or not only_basic,'only basic endpoints')
  if fail is None:check(ns[endpoint.__name__] is endpoint,'exported object is registered endpoint')
  check(endpoint.__defaults__[-1] is dep or endpoint.__name__=='get_tracks','same context default object')
 signatures=[(m,p,k,f.__name__,f.__annotations__,f.__defaults__[:-1]) for m,p,k,f in router.routes]
 return events,signatures
for fail in [None,'definition',('GET','/cases'),('POST','/cases'),('GET','/cases/{case_id}')]:
 a=run(old,fail=fail);b=run(new,fail=fail);c=run(new,only_basic=True,fail=fail)
 check(a==b,'default event/signature sequence')
 if fail is None:
  check(c[1]==b[1][:3] and len(c[1])==3,'basic-only routes')
  # Full path continues with overview, vessels, tracks in unchanged order.
  check([x[3] for x in b[1]]==names+['overview','get_vessels','create_vessel','get_tracks'],'full route order')
 else:check(c==b,'early failure before business registrations')
 print('PASS normal/definition/registration marker',fail)

# Execute basic module definitions against an exact handmade importer. No
# dependency source executes; unexpected imports fail rather than falling back.
seen=[]
expected={(level,module):members for level,module,members in imports}
def fake_import(name,globals=None,locals=None,fromlist=(),level=0):
 key=(level,name or None)
 check(key in expected and tuple(fromlist)==expected[key], 'unexpected basic dependency')
 seen.append(key)
 return SimpleNamespace(**{member:object() for member in fromlist})
namespace={'__builtins__':{'__import__':fake_import}}
exec(compile(basic,'<basic-module-with-only-fakes>','exec'),namespace)
check(seen==list(expected),'exact basic imports, no full cases router/overview dependencies')
check(callable(namespace['_register_basic_cases']),'basic registration defined')

print('PASS full AST, metadata, direct import allowlist, object identity, defaults and fake registration order; no actual FastAPI/HTTP')
