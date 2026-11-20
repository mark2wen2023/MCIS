"""Actual endpoint definitions, fake route/session/point loader; never FastAPI or ORM."""
import ast
import asyncio
import builtins
from pathlib import Path
import runpy
from types import SimpleNamespace
import unittest
ROOT=Path(__file__).resolve().parents[2]
prior=runpy.run_path(str(ROOT/'tests_acceptance/local-review-pilot/check.py'))
Store,Session,Denied=prior['Store'],prior['Session'],prior['Denied']
TOKEN,DIGEST,ORIGIN=prior['TOKEN'],prior['DIGEST'],prior['ORIGIN']
tree=ast.parse((ROOT/'service/mcis_service/common/pilot_case_discovery.py').read_text())
assert [(n.module,n.level) for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]==[('fastapi',0),('context',1),('local_review_pilot',1),('cases.service',2)]
assert not any(isinstance(n,ast.Attribute) and n.attr in ('list_cases','list_docs','create_all') for n in ast.walk(tree))
class App:
    def __init__(self):self.routes=[]
    def get(self,path,**metadata):
        assert path=='/api/v1/pilot/cases';assert metadata=={'response_model':list[dict[str,str]]}
        def register(fn):self.routes.append(SimpleNamespace(path=path,endpoint=fn));return fn
        return register

def setup(grants=None,enabled=True,mode='normal'):
    events=[];clock=[10.0]
    store=Store({DIGEST:Session('pilot-subject','Investigator',20,frozenset(grants if grants is not None else {('SYN-A','case.read'),('SYN-B','audio.list')}))},clock=lambda:clock[0])
    class Guard:
        def __enter__(self):events.append('no_autoflush');return self
        def __exit__(self,*exc):return False
    class FakeSession:
        no_autoflush=Guard()
        def __enter__(self):events.append('session');return self
        def __exit__(self,*exc):events.append('rollback' if exc[0] else 'read-session-end');return False
    def load_case(session,case):
        events.append(('load_case',case))
        if mode=='error':raise RuntimeError('synthetic loader failure')
        if mode=='revoke':store.revoke(DIGEST)
        return {'caseId':'SYN-WRONG' if mode=='mismatch' else case,'title':'synthetic '+case,'extra':'not exposed'}
    def importer(name,globals=None,locals=None,fromlist=(),level=0):
        assert (name,tuple(fromlist),level)==('cases.service',('load_case',),2)
        events.append('point-loader-import');return SimpleNamespace(load_case=load_case)
    scope={'Request':object,'Response':object,'problem':Denied,'PilotSessions':Store,'_cookie_reader':prior['scope']['_cookie_reader'],'__builtins__':{**vars(builtins),'__import__':importer}}
    exec(compile(ast.Module(body=[n for n in tree.body if not isinstance(n,ast.ImportFrom)],type_ignores=[]),'<real registration fake dependencies>','exec'),scope)
    app=App();fn=scope['_register_pilot_case_discovery'](app,enabled=enabled,sessions=store,origin=ORIGIN)
    req=prior['request'](path='/api/v1/pilot/cases');req.app=SimpleNamespace(state=SimpleNamespace(db=SimpleNamespace(session=FakeSession)))
    response=SimpleNamespace(headers={})
    return SimpleNamespace(events=events,store=store,clock=clock,app=app,req=req,response=response,fn=fn,register=scope['_register_pilot_case_discovery'])
class Checks(unittest.TestCase):
    def test_permitted_ids_only_no_full_scan_or_extra_fields(self):
        s=setup({('SYN-B','case.read'),('SYN-A','case.read'),('SYN-C','audio.list')})
        self.assertEqual(asyncio.run(s.fn(s.req,s.response)),[{'caseId':'SYN-A','title':'synthetic SYN-A'},{'caseId':'SYN-B','title':'synthetic SYN-B'}])
        self.assertEqual(s.events,['point-loader-import','session','no_autoflush',('load_case','SYN-A'),('load_case','SYN-B'),'read-session-end'])
        self.assertEqual(s.response.headers,{'Cache-Control':'no-store'});self.assertEqual(len(s.app.routes),1)
    def test_default_expired_revoked_no_cookie_no_storage(self):
        for kind in ['disabled','expired','revoked','missing','cross-site']:
            s=setup(enabled=kind!='disabled')
            if kind=='expired':s.clock[0]=20
            if kind=='revoked':s.store.revoke(DIGEST)
            if kind=='missing':s.req.headers.values['cookie']=[]
            if kind=='cross-site':s.req.headers.values['sec-fetch-site']=['cross-site']
            with self.assertRaises(Denied):asyncio.run(s.fn(s.req,s.response))
            self.assertEqual(s.events,[])
    def test_empty_authorized_set_no_storage(self):
        s=setup(set());self.assertEqual(asyncio.run(s.fn(s.req,s.response)),[]);self.assertEqual(s.events,[])
    def test_mismatch_loader_error_and_midread_revoke_no_partial_result(self):
        for mode,exception in [('mismatch',Denied),('error',RuntimeError),('revoke',Denied)]:
            s=setup(mode=mode)
            with self.assertRaises(exception):asyncio.run(s.fn(s.req,s.response))
            self.assertEqual(s.events[-1],'rollback')
    def test_no_duplicate_registration(self):
        s=setup()
        with self.assertRaises(ValueError):s.register(s.app)
        self.assertEqual(len(s.app.routes),1)
if __name__=='__main__':unittest.main()
