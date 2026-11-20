"""Production AST + hand-written route/query/transaction substitutes only."""
import ast
import asyncio
import builtins
from pathlib import Path
import runpy
import subprocess
from types import SimpleNamespace as NS
import unittest
ROOT=Path(__file__).resolve().parents[2]
BASE='159a3dda557b3998c5b2c2d23c243cb81641ca13'
PATH='service/mcis_service/image_review/app.py'
tree=ast.parse((ROOT/PATH).read_text())
old=ast.parse(subprocess.check_output(['git','show',BASE+':'+PATH],cwd=ROOT,text=True))
prior=runpy.run_path(str(ROOT/'tests_acceptance/pilot-factory/check.py'))
Denied=prior['Denied']
class Query:
    def __getattr__(self,n):return self
    def __eq__(self,o):return True
    def __call__(self,*a,**kw):return self
    def where(self,*a):return self
    def order_by(self,*a):return self

def setup(limited=True, task=False):
    events=[]
    initial={'mode':'imported-existing-output','bindings':{},'candidate':{'text_lines':[{}]},'utc':'synthetic'}
    if task:initial['artifactTaskId']='SYN-TASK'
    rows=[NS(case_id='SYN-A',run_id='OCR-synthetic',revision=0,doc=initial)]
    class Guard:
        def __enter__(self):return self
        def __exit__(self,*a):return False
    class Session(Guard):
        def scalars(self,q):events.append('query');return NS(all=lambda:rows)
        def add(self,row):events.append('append')
        def flush(self):events.append('flush')
    state=NS(image_imports_only=limited)
    ctx=NS(request=NS(app=NS(state=state)),db=NS(session=Session),operator='synthetic',role='Investigator')
    body={'expectedRevision':0,'lineIndex':0,'text':'synthetic','decision':'pending','reason':'synthetic'}
    async def bounded(request):events.append('body');return dict(body)
    def records(s,case,run):events.append('records');return rows
    def receipts(*args):events.append('receipts');return {}
    def importer(name,globals=None,locals=None,fromlist=(),level=0):
        if (name,level,tuple(fromlist))!=('tasks',1,('verify_task_binding',)):raise AssertionError(name)
        events.append('task-import');return NS(verify_task_binding=lambda *a:events.append('task-verify'))
    class Record:
        case_id=revision=id=Query()
        def __init__(self,**kw):self.__dict__.update(kw)
    scope={'Ctx':object,'CtxDep':None,'Request':object,'problem':Denied,'WRITE_LOCK':Guard(),
           'authorize':lambda *a,**kw:events.append('authorize'),'begin':lambda s:events.append('begin'),
           'body_bounded':bounded,'text':lambda *a,**kw:None,'records':records,'receipts':receipts,
           'select':lambda *a:Query(),'Record':Record,'iso':lambda x:'synthetic','now_utc':lambda:None,
           'audit':NS(append=lambda *a,**kw:events.append('audit')),
           '__builtins__':{**vars(builtins),'__import__':importer}}
    for name in ['_require_imported_source','list_runs','read','review','result']:
        node=next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)
        node=ast.parse(ast.unparse(node)).body[0];node.decorator_list=[]
        exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'<production functions>','exec'),scope)
    return NS(scope=scope,ctx=ctx,events=events,rows=rows,body=body)

class Checks(unittest.TestCase):
    def test_existing_logic_unchanged_except_three_explicit_guards(self):
        before={n.name:n for n in old.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        after={n.name:n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
        class RemoveGuard(ast.NodeTransformer):
            def visit_Expr(self,node):
                if isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='_require_imported_source':return None
                return self.generic_visit(node)
            def visit_For(self,node):
                if any(isinstance(n,ast.Name) and n.id=='_require_imported_source' for n in ast.walk(node)):return None
                return self.generic_visit(node)
        for name in before:
            if name=='_initialize_image_review_storage':continue
            candidate=RemoveGuard().visit(ast.parse(ast.unparse(after[name])).body[0])
            self.assertEqual(ast.dump(candidate,include_attributes=False),ast.dump(before[name],include_attributes=False),name)

    def test_old_head_list_admits_task_marker(self):
        s=setup(task=True)
        node=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name=='list_runs')
        node=ast.parse(ast.unparse(node)).body[0];node.decorator_list=[]
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<old head fake dependencies>','exec'),s.scope)
        self.assertEqual(s.scope['list_runs']('SYN-A',s.ctx)[0]['runId'],'OCR-synthetic')
        # New handler must refuse before returning even the task-backed list entry.

    def test_task_records_refused_before_bytes_dynamic_import_or_write(self):
        for name in ['list_runs','read','review']:
            s=setup(task=True)
            with self.assertRaises(Denied) as error:
                if name=='list_runs':s.scope[name]('SYN-A',s.ctx)
                elif name=='read':s.scope[name]('SYN-A','OCR-synthetic',s.ctx)
                else:asyncio.run(s.scope[name]('SYN-A','OCR-synthetic',None,s.ctx))
            self.assertEqual(error.exception.code,'OCR_IMPORTED_SOURCE_ONLY')
            self.assertIn('authorize',s.events)
            for blocked in ['receipts','task-import','append','audit']:self.assertNotIn(blocked,s.events)

    def test_manual_records_keep_receipts_and_conflict_guard(self):
        s=setup();self.assertEqual(s.scope['read']('SYN-A','OCR-synthetic',s.ctx)['revision'],0)
        self.assertIn('receipts',s.events);self.assertNotIn('task-import',s.events)
        s=setup();s.body['expectedRevision']=1
        with self.assertRaises(Denied) as error:asyncio.run(s.scope['review']('SYN-A','OCR-synthetic',None,s.ctx))
        self.assertEqual(error.exception.code,'OCR_REVISION');self.assertIn('receipts',s.events);self.assertNotIn('append',s.events)
        s=setup();asyncio.run(s.scope['review']('SYN-A','OCR-synthetic',None,s.ctx))
        self.assertLess(s.events.index('receipts'),s.events.index('append'));self.assertIn('audit',s.events)

    def test_normal_mode_keeps_task_verification_and_unknown_source_fails_closed(self):
        s=setup(limited=False,task=True);s.scope['read']('SYN-A','OCR-synthetic',s.ctx)
        self.assertLess(s.events.index('receipts'),s.events.index('task-verify'))
        for initial in [{},None,{'mode':'other'},{'mode':'imported-existing-output','artifactTaskId':None}]:
            s=setup()
            with self.assertRaises(Denied):s.scope['_require_imported_source'](s.ctx,initial)

    def test_real_storage_initializer_uses_only_record_and_preserves_sql(self):
        calls=[];record=object()
        class Engine:
            def begin(self):return self
            def __enter__(self):return self
            def __exit__(self,*a):return False
            def execute(self,sql):calls.append(sql)
        scope={'Storage':NS(metadata=NS(create_all=lambda engine,**kw:calls.append(kw))),
               'Record':NS(__table__=record),'sql':lambda x:x}
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_initialize_image_review_storage')
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<fake storage>','exec'),scope)
        app=NS(state=NS(db=NS(engine=Engine())))
        scope[node.name](app,imported_only=True);self.assertEqual(calls[0],{'tables':[record]})
        restricted_sql=calls[1:];calls.clear();scope[node.name](app)
        self.assertEqual(calls[0],{});self.assertEqual(calls[1:],restricted_sql);self.assertEqual(len(restricted_sql),2)
        def failed(*args,**kwargs):raise RuntimeError('synthetic DDL failure')
        scope['Storage'].metadata.create_all=failed
        with self.assertRaisesRegex(RuntimeError,'DDL failure'):scope[node.name](app,imported_only=True)

    def test_factory_wires_exact_image_and_receipt_surface(self):
        s=prior['setup']();sc=s.scope;calls=[]
        class Router:
            def __init__(self,**kw):self.routes=[]
            def add_api_route(self,path,fn,methods):self.routes.append(NS(path=path,methods=set(methods),endpoint=fn))
        router=Router()
        for node in tree.body:
            if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
            for decorator in node.decorator_list:
                if isinstance(decorator,ast.Call) and isinstance(decorator.func,ast.Attribute) and isinstance(decorator.func.value,ast.Name) and decorator.func.value.id=='router':
                    router.add_api_route('/api/v1/cases/{case_id}/image-reviews'+ast.literal_eval(decorator.args[0]),node.name,[decorator.func.attr.upper()])
        mount=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_mount_image_imports_only')
        ns={'router':router};exec(compile(ast.Module(body=[mount],type_ignores=[]),'<real mount fake router>','exec'),ns)
        def init(app,**kw):calls.append(kw);self.assertTrue(app.state.image_imports_only)
        sc.update(APIRouter=Router,NoStoreRoute=object,receipt_input=object(),_mount_image_imports_only=ns[mount.name],_initialize_image_review_storage=init)
        app=s.construct(image_imports=True,image_blob_dir=sc['Path']('/synthetic'))
        actual={(m,r.path) for r in app.routes for m in r.methods}
        self.assertEqual(actual,sc['ROUTES']|sc['IMAGE_ROUTES']);self.assertEqual(len(actual),8)
        self.assertEqual(calls,[{'imported_only':True}]);self.assertIsNone(app.state.image_ocr_runtime)
        self.assertFalse(any('download' in p or 'tasks' in p for m,p in actual))
        with self.assertRaises(ValueError):ns[mount.name](app)
        s=prior['setup']()
        with self.assertRaises(ValueError):s.construct(image_imports=True)
        self.assertEqual(s.events,[])

if __name__=='__main__':unittest.main()
