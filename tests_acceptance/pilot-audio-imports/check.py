"""Actual source functions with hand-written dependencies. No ORM/HTTP/media execution."""
import ast
import asyncio
import builtins
from pathlib import Path
import runpy
import subprocess
from types import SimpleNamespace as NS
import unittest
ROOT=Path(__file__).resolve().parents[2]
PATH='service/mcis_service/audio_review/app.py'
BASE='6b3854e4d2d34212eedfcfb43b3d39ea36c07bc9'
tree=ast.parse((ROOT/PATH).read_text())
old=ast.parse(subprocess.check_output(['git','show',BASE+':'+PATH],cwd=ROOT,text=True))
prior=runpy.run_path(str(ROOT/'tests_acceptance/pilot-factory/check.py'))
class Rejected(Exception):pass
def function(name,scope,source=tree):
    n=next(n for n in source.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)
    n=ast.parse(ast.unparse(n)).body[0];n.decorator_list=[]
    exec(compile(ast.Module(body=[n],type_ignores=[]),'<actual function/fake dependencies>','exec'),scope)
    return scope[name]
class Query:
    def __getattr__(self,n):return self
    def __eq__(self,x):return self
    def where(self,*a):return self
class Guard:
    def __enter__(self):return self
    def __exit__(self,*a):return False

def setup(limited=True,task=False,old_check=False):
    events=[]
    doc={'audioReceipt':'synthetic-audio','draftReceipt':'synthetic-draft','draftBytesSha256':'digest',
         'machineDraft':{'transcript':{'segments':[{'id':'segment'}],'unlocatedSegments':[]},'source':{'durationMs':1000,'currentSha256':'audio'},'artifactSha256':'draft'},'audio':{'sampleRateHz':8000,'frames':8000},'utc':'synthetic'}
    if task:doc['artifactTaskId']='synthetic-task'
    rows=[NS(case_id='SYN-A',run_id='AR-synthetic',revision=0,doc=doc)]
    class Session(Guard):
        def scalars(self,*a):events.append('query');return rows
        def add(self,row):events.append('append');rows.append(row)
        def flush(self):events.append('flush')
    ctx=NS(request=NS(app=NS(state=NS(audio_imports_only=limited))),db=NS(session=Session),operator='synthetic',role='Investigator')
    body={'expectedRevision':0,'segmentId':'segment','text':'synthetic','hearingStatus':'pending','startMs':None,'endMs':None,'reason':'synthetic'}
    async def bounded(*a):events.append('body');return dict(body)
    def importer(name,globals=None,locals=None,fromlist=(),level=0):
        if (name,level,tuple(fromlist))!=('tasks',1,('verify_task_binding',)):raise AssertionError(name)
        events.append('task-import');return NS(verify_task_binding=lambda *a:events.append('task-verify'))
    def source(*a):events.append('source');return {},{}
    def receipt(*a):events.append('receipt');return {},b'synthetic'
    class Revision:
        case_id=run_id=revision=id=Query()
        def __init__(self,**kw):self.__dict__.update(kw)
    scope={'Ctx':object,'CtxDep':None,'Request':object,'problem':Rejected,'WRITE_LOCK':Guard(),
           'authorize':lambda *a,**kw:events.append('authorize'),'begin':lambda *a:events.append('begin'),
           'source':source,'matched_source':lambda *a:True,'receipt':receipt,'sha':lambda *a:'digest',
           'rows':lambda *a:rows,'select':lambda *a:Query(),'Revision':Revision,'body_bounded':bounded,'text':lambda *a,**kw:None,
           'iso':lambda *a:'synthetic','now_utc':lambda:None,'audit':NS(append=lambda *a,**kw:events.append('audit')),
           '__builtins__':{**vars(builtins),'__import__':importer}}
    for name in ['_require_imported_source','check','result','listing','get','revise']:
        if old_check and name=='_require_imported_source':continue
        function(name,scope,old if old_check and name=='check' else tree)
    return NS(scope=scope,ctx=ctx,events=events,rows=rows,body=body,doc=doc)

def route_scope():
    class Router:
        def __init__(self,**kw):self.routes=[]
        def add_api_route(self,path,fn,methods,**kw):self.routes.append(NS(path=path,methods=set(methods),endpoint=fn,metadata=kw))
    scope={'APIRouter':Router};router=Router();scope['router']=router
    for name in ['source_context','attach','listing','get','revise']:
        scope[name]=object()
        n=next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)
        d=n.decorator_list[0]
        router.add_api_route('/api/v1/cases/{case_id}/audio-reviews'+ast.literal_eval(d.args[0]),scope[name],[d.func.attr.upper()],**{k.arg:ast.literal_eval(k.value) for k in d.keywords})
    function('_mount_audio_imports_only',scope)
    return scope

class Checks(unittest.TestCase):
    def test_old_counterexample_and_limited_task_refusal_before_bytes(self):
        old_s=setup(task=True,old_check=True);old_s.scope['check'](old_s.ctx,None,'SYN-A',old_s.doc)
        self.assertEqual(old_s.events,['source','task-import','task-verify'])
        s=setup(task=True)
        with self.assertRaises(Rejected):s.scope['check'](s.ctx,None,'SYN-A',s.doc)
        self.assertEqual(s.events,[])
    def test_real_read_list_revision_paths_refuse_task_after_authorization(self):
        for name in ['listing','get','revise']:
            s=setup(task=True)
            with self.assertRaises(Rejected):
                if name=='listing':s.scope[name]('SYN-A',s.ctx)
                elif name=='get':s.scope[name]('SYN-A','AR-synthetic',s.ctx)
                else:asyncio.run(s.scope[name]('SYN-A','AR-synthetic',None,s.ctx))
            self.assertIn('authorize',s.events)
            self.assertFalse(set(s.events)&{'source','receipt','task-import','append','audit'})
    def test_normal_imported_read_revision_and_conflict_preserved(self):
        s=setup();out=s.scope['get']('SYN-A','AR-synthetic',s.ctx);self.assertEqual(out['revision'],0)
        self.assertEqual(s.events,['begin','authorize','source','receipt'])
        out=asyncio.run(s.scope['revise']('SYN-A','AR-synthetic',None,s.ctx));self.assertEqual(out['revision'],1)
        self.assertEqual(s.events[-3:],['append','flush','audit'])
        count=s.events.count('append')
        with self.assertRaises(Rejected) as c:asyncio.run(s.scope['revise']('SYN-A','AR-synthetic',None,s.ctx))
        self.assertEqual(c.exception.args[0],412);self.assertEqual(s.events.count('append'),count)
    def test_legacy_task_binding_still_runs_and_failure_propagates(self):
        s=setup(limited=False,task=True);s.scope['check'](s.ctx,None,'SYN-A',s.doc)
        self.assertEqual(s.events,['source','task-import','task-verify'])
        def fail(*a):raise RuntimeError('synthetic source failure')
        s.scope['source']=fail
        with self.assertRaisesRegex(RuntimeError,'synthetic source failure'):s.scope['check'](s.ctx,None,'SYN-A',s.doc)
    def test_unchanged_business_handlers_and_trigger_sql(self):
        names=['receipt','source','sample_source','matched_source','validate','inspect_draft','rows','result','strict','source_context','attach','get','revise','_mount_audio_review_routes','register_audio_review','_register_audio_review_only','create_audio_review_app']
        for name in names:
            a=next(n for n in old.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)
            b=next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)
            self.assertEqual(ast.dump(a),ast.dump(b),name)
        a=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name=='_initialize_audio_review_storage')
        b=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==a.name)
        self.assertEqual(ast.dump(a.body[1]),ast.dump(b.body[1]))
    def test_mount_reuses_route_objects_and_excludes_source_task_html(self):
        s=route_scope();received=[];app=NS(state=NS(),include_router=lambda r:received.extend(r.routes))
        s['_mount_audio_imports_only'](app)
        self.assertEqual(received,s['router'].routes[1:]);self.assertEqual(len(received),4)
        self.assertEqual(received[0].metadata,{'status_code':201});self.assertTrue(app.state.audio_imports_only)
        with self.assertRaises(ValueError):s['_mount_audio_imports_only'](app)
        s=route_scope();s['router'].routes.append(s['router'].routes[1]);app=NS(state=NS(),include_router=lambda r:self.fail('must not register'))
        with self.assertRaises(RuntimeError):s['_mount_audio_imports_only'](app)
    def test_real_table_and_sql_and_early_failure(self):
        events=[];table=object()
        class Engine:
            def begin(self):events.append('begin');return self
            def __enter__(self):return self
            def __exit__(self,*a):return False
            def execute(self,sql):events.append(sql)
        sc={'Storage':NS(metadata=NS(create_all=lambda e,**kw:events.append(kw))),'Revision':NS(__table__=table),'sql':lambda s:s}
        fn=function('_initialize_audio_review_storage',sc);app=NS(state=NS(db=NS(engine=Engine())))
        fn(app,imported_only=True);self.assertEqual(events[0],{'tables':[table]});limited=events[1:];events.clear();fn(app)
        self.assertEqual(events[0],{});self.assertEqual(events[1:],limited)
        def fail(*a,**kw):raise RuntimeError('synthetic init failure')
        sc['Storage'].metadata.create_all=fail;events.clear()
        with self.assertRaises(RuntimeError):fn(app,imported_only=True)
        self.assertEqual(events,[])
    def test_factory_cookie_boundary_requires_exact_audio_grant(self):
        s=prior['setup']();routes=route_scope()
        s.scope.update(APIRouter=routes['APIRouter'],NoStoreRoute=object,receipt_input=object(),
                       _mount_audio_imports_only=routes['_mount_audio_imports_only'],_initialize_audio_review_storage=lambda *a,**kw:None)
        fixtures=prior['prior']
        sessions=prior['Store']({fixtures['DIGEST']:prior['Session']('synthetic','Investigator',20.0,
            frozenset({('SYN-A','audio.list')}))},clock=lambda:10.0)
        app=s.construct(audio_imports=True,audio_blob_dir=s.scope['Path']('/synthetic'),sessions=sessions)
        dependency=next(iter(app.dependency_overrides.values()))
        req=prior['req'](app,path='/api/v1/cases/{case_id}/audio-reviews')
        grant=asyncio.run(dependency(req));self.assertEqual(grant.operator,'synthetic')
        req.path_params['case_id']='SYN-B'
        with self.assertRaises(prior['Denied']):asyncio.run(dependency(req))
        req.path_params['case_id']='SYN-A';req.method='POST'  # audio.import not granted
        with self.assertRaises(prior['Denied']):asyncio.run(dependency(req))
        req.method='GET';req.headers.values['cookie']=[]
        with self.assertRaises(prior['Denied']):asyncio.run(dependency(req))

    def test_factory_opt_in_route_whitelist_and_real_mount(self):
        s=prior['setup']();routes=route_scope();calls=[]
        s.scope.update(APIRouter=routes['APIRouter'],NoStoreRoute=object,receipt_input=object(),preview_input=object(),commit_input=object(),
                       _mount_audio_imports_only=routes['_mount_audio_imports_only'],_initialize_audio_review_storage=lambda app,**kw:calls.append(kw))
        app=s.construct(audio_imports=True,audio_blob_dir=s.scope['Path']('/synthetic'))
        self.assertEqual({(m,r.path) for r in app.routes for m in r.methods},s.scope['ROUTES']|s.scope['AUDIO_ROUTES'])
        self.assertEqual(calls,[{'imported_only':True}]);self.assertTrue(app.state.audio_imports_only)
        self.assertTrue(app.dependency_overrides)
        normal=prior['setup']();app=normal.construct();self.assertFalse(hasattr(app.state,'audio_imports_only'))
        with self.assertRaises(ValueError):normal.construct(audio_imports=True)
        with self.assertRaises(ValueError):normal.construct(audio_imports='true')
if __name__=='__main__':unittest.main()
