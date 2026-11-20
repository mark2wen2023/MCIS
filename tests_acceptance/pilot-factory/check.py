"""AST-extracted real factory/handlers, fake FastAPI/DB only. No service imports."""
import ast
import asyncio
import runpy
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
ROOT=Path(__file__).resolve().parents[2]
prior=runpy.run_path(str(ROOT/'tests_acceptance/local-review-pilot/check.py'))
Store,Session,Denied=prior['Store'],prior['Session'],prior['Denied']
class Strip(ast.NodeTransformer):
    def visit_ImportFrom(self,node):return None
    def visit_Import(self,node):return None

def setup(extra=False, init_fail=False):
    events=[];scope=dict(prior['scope']);clock=[10.0]
    sessions=Store({prior['DIGEST']:Session('synthetic','Investigator',20.0,frozenset({('SYN-A','case.read')}))},clock=lambda:clock[0])
    class Guard:
        def __enter__(self):events.append('no_autoflush');return self
        def __exit__(self,*args):return False
    class FakeSession:
        no_autoflush=Guard()
        def __enter__(self):events.append('session');return self
        def __exit__(self,*args):return False
    db=NS(session=FakeSession)
    class App:
        def __init__(self,**kw):
            events.append('app');self.options=kw;self.routes=[];self.state=NS();self.dependency_overrides={}
            if extra:self.routes.append(NS(methods={'GET'},path='/unexpected'))
        def include_router(self, router):
            self.routes.extend(router.routes)
        def get(self,path,**kw):
            def register(fn):
                events.append(path);self.routes.append(NS(methods={'GET'},path=path,endpoint=fn,options=kw));return fn
            return register
    def init(target):
        if target is not db:raise AssertionError('wrong storage')
        events.append('initialize')
        if init_fail:raise RuntimeError('synthetic initialize failure')
    class FakePath:
        def __init__(self,value):pass
        def is_absolute(self):return True
        def with_name(self,name):
            if name!='workbench.html':raise AssertionError('unexpected source')
            return self
        def read_text(self,**kw):events.append('html');return '<p>synthetic shell</p>'
    def load_case(session,case_id):events.append(('read',case_id));return {'caseId':case_id,'title':'synthetic title'}
    scope.update(workbench_page=lambda html,**kw:html,SimpleNamespace=NS,FastAPI=App,Depends=lambda f:f,Response=object,Request=object,HTMLResponse=lambda html,headers:NS(html=html,headers=headers),Path=FakePath,__file__='synthetic/factory.py',load_case=load_case,_initialize_pilot_core_storage=init)
    for file in ['common/pilot_case_discovery.py','local_review_pilot/factory.py']:
        tree=ast.parse((ROOT/'service/mcis_service'/file).read_text())
        if file.endswith('factory.py'):
            imports={n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}
            if imports != {'pathlib','urllib.parse','common.local_review_pilot','fastapi','fastapi.responses','common.context','common.pilot_case_discovery','common.pilot_core_storage','cases.service','types','image_review.app','evidence_intake.router','reports.access','pages','audio_review.app'}:raise AssertionError(imports)
        exec(compile(ast.fix_missing_locations(Strip().visit(tree)),'<production AST fake dependencies>','exec'),scope)
    def construct(**changes):
        kw=dict(enabled=True,db=db,sessions=sessions,origin='https://127.0.0.1:8766');kw.update(changes)
        return scope['create_local_review_pilot'](**kw)
    return NS(events=events,scope=scope,db=db,sessions=sessions,clock=clock,construct=construct)

def req(app,case='SYN-A',path='/api/v1/cases/{case_id}'):
    r=prior['request'](case=case,path=path,changes={'host':['127.0.0.1:8766']});r.app=app;return r

def endpoint(app,path):return next(r.endpoint for r in app.routes if r.path==path)
class Checks(unittest.TestCase):
    def test_disabled_or_incomplete_before_construction(self):
        for changes in [dict(enabled=False),dict(sessions=None),dict(db=None),dict(origin='http://127.0.0.1:8766'),dict(origin='https://other.invalid')]:
            s=setup()
            with self.assertRaises(ValueError):s.construct(**changes)
            self.assertEqual(s.events,[])
        s=setup()
        with self.assertRaises(ValueError):s.scope['create_local_review_pilot']()
        self.assertEqual(s.events,[])

    def test_three_route_surface_then_initialization(self):
        s=setup();app=s.construct()
        self.assertEqual(s.events,['html','app','/api/v1/pilot/cases','/api/v1/cases/{case_id}','/pilot','initialize'])
        self.assertEqual(app.options,dict(title='MCIS synthetic case pilot',docs_url=None,redoc_url=None,openapi_url=None,redirect_slashes=False))
        self.assertEqual(len(app.dependency_overrides),1)
        page=endpoint(app,'/pilot')();self.assertEqual(page.headers['Cache-Control'],'no-store')

    def test_surface_drift_stops_before_storage_and_init_failure_propagates(self):
        s=setup(extra=True)
        with self.assertRaisesRegex(RuntimeError,'surface'):s.construct()
        self.assertNotIn('initialize',s.events)
        s=setup(init_fail=True)
        with self.assertRaisesRegex(RuntimeError,'initialize failure'):s.construct()

    def test_discovery_and_detail_share_verified_session(self):
        s=setup();app=s.construct();s.events.clear()
        discover=endpoint(app,'/api/v1/pilot/cases')
        self.assertEqual(asyncio.run(discover(req(app,path='/api/v1/pilot/cases'),NS(headers={}))),[{'caseId':'SYN-A','title':'synthetic title'}])
        detail=endpoint(app,'/api/v1/cases/{case_id}');dependency=detail.__defaults__[0]
        ctx=asyncio.run(dependency(req(app)));ctx.db=s.db
        response=NS(headers={})
        self.assertEqual(detail('SYN-A',response,ctx)['caseId'],'SYN-A')
        self.assertEqual(response.headers,{'Cache-Control':'no-store'})
        self.assertEqual([e for e in s.events if isinstance(e,tuple)],[('read','SYN-A'),('read','SYN-A')])

    def test_denied_session_never_dispatches_detail(self):
        for mode in ['other-case','expired','revoked','missing','cross-site']:
            s=setup();app=s.construct();s.events.clear();r=req(app,case='SYN-B' if mode=='other-case' else 'SYN-A')
            if mode=='expired':s.clock[0]=20
            if mode=='revoked':s.sessions.revoke(prior['DIGEST'])
            if mode=='missing':r.headers.values['cookie']=[]
            if mode=='cross-site':r.headers.values['sec-fetch-site']=['cross-site']
            detail=endpoint(app,'/api/v1/cases/{case_id}')
            async def dispatch():
                ctx=await detail.__defaults__[0](r);ctx.db=s.db
                return detail(r.path_params['case_id'],NS(headers={}),ctx)
            with self.assertRaises(Denied):asyncio.run(dispatch())
            self.assertEqual(s.events,[])

if __name__=='__main__':unittest.main()
