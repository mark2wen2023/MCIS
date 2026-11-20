"""Standard library, extracted adapter AST and handwritten dependencies only."""
import ast
import asyncio
from dataclasses import dataclass
import math
from pathlib import Path
import runpy
import time
from types import SimpleNamespace as NS
import unittest
ROOT=Path(__file__).resolve().parents[2]
fixture=runpy.run_path(str(ROOT/'tools/pilot_image_acceptance/fixtures.py'))
class Stopped(Exception):pass
def checked(ok,message):
    if not ok:raise Stopped(message)
class Strip(ast.NodeTransformer):
    def visit_ImportFrom(self,node):return None
    def visit_Import(self,node):return None

def setup():
    import json
    events=[];clock=[10.0]
    async def original(body,ctx):
        events.append(('original-handler',body['caseId'],ctx.operator,ctx.role))
        return 201,body
    def bind(*,context_for_creation):
        async def invoke(body):
            ctx=await context_for_creation(body['caseId'],'case.create')
            return await original(body,ctx)
        return invoke
    scope=dict(dataclass=dataclass,math=math,time=time,json=json,cases=fixture['cases'],encoded=fixture['encoded'],sha=fixture['sha'],checked=checked,bind_existing_case_creator=bind)
    tree=Strip().visit(ast.parse((ROOT/'tools/pilot_image_acceptance/authority.py').read_text()))
    exec(compile(ast.fix_missing_locations(tree),'<real authority fake handler>','exec'),scope)
    grants=frozenset((d['caseId'],'case.create',fixture['sha'](fixture['encoded'](d))) for d in fixture['cases']())
    cfg=scope['CreationConfig']('server-subject','LeadInvestigator',30.0,grants)
    auth=scope['CreationAuthority'](cfg,clock=lambda:clock[0]);auth.claim()
    adapter=scope['CreationAdapter'](auth,NS(state=NS()),lambda **kw:NS(**kw),lambda scope:NS(scope=scope))
    return NS(scope=scope,auth=auth,adapter=adapter,config=cfg,clock=clock,events=events)

class Checks(unittest.TestCase):
    def test_exact_two_cases_only_once_server_identity(self):
        s=setup()
        for doc in fixture['cases']():
            status,result=asyncio.run(s.adapter.create_case(doc));self.assertEqual(status,201);self.assertEqual(result,doc)
            with self.assertRaises(Stopped):asyncio.run(s.adapter.create_case(doc))
        self.assertEqual(s.events,[('original-handler',cid,'server-subject','LeadInvestigator') for cid in fixture['CASE_IDS']])
        with self.assertRaises(Stopped):s.auth.claim()

    def test_no_default_role_wrong_body_expiry_closed_scope(self):
        s=setup();doc=fixture['cases']()[0];doc['title']='changed'
        with self.assertRaises(Stopped):asyncio.run(s.adapter.create_case(doc))
        s.clock[0]=30
        with self.assertRaises(Stopped):asyncio.run(s.adapter.create_case(fixture['cases']()[0]))
        self.assertEqual(s.events,[])
        s=setup();s.adapter.close()
        with self.assertRaises(Stopped):asyncio.run(s.adapter.create_case(fixture['cases']()[0]))
        with self.assertRaises(Stopped):s.scope['CreationAuthority'](None)
        cfg=s.scope['CreationConfig']('subject','',30,s.config.grants)
        with self.assertRaises(Stopped):s.scope['CreationAuthority'](cfg,clock=lambda:10)
        cfg=s.scope['CreationConfig']('subject','Investigator',1000,s.config.grants)
        with self.assertRaises(Stopped):s.scope['CreationAuthority'](cfg,clock=lambda:10)

    def test_failure_consumes_scope_and_no_auto_retry(self):
        s=setup()
        async def failure(body):raise RuntimeError('synthetic unknown result')
        s.adapter._create=failure
        with self.assertRaises(RuntimeError):asyncio.run(s.adapter.create_case(fixture['cases']()[0]))
        with self.assertRaises(Stopped):asyncio.run(s.adapter.create_case(fixture['cases']()[1]))
        self.assertFalse(s.adapter._open)

    def test_creation_context_not_available_outside_active_request(self):
        s=setup()
        with self.assertRaises(Stopped):asyncio.run(s.adapter._context('SYN-PILOT-A','case.create'))
        self.assertEqual(s.events,[])

    def test_owned_scope_with_only_handwritten_resources(self):
        from contextlib import contextmanager
        for mode in ('normal','nonempty','factory-error','continuation-error','missing-host'):
            s=setup();events=[]
            authority=s.scope['CreationAuthority'](s.config,clock=lambda:10)
            class FakePath:
                def __init__(self,value):self.value=str(value)
                def __truediv__(self,value):return FakePath(self.value+'/'+value)
                def __str__(self):return self.value
                def is_absolute(self):return True
                def exists(self):events.append('exists');return False
                def mkdir(self):events.append('mkdir')
            @contextmanager
            def isolated():
                events.append('host-enter')
                try:yield FakePath('/fabricated')
                finally:events.append('host-exit')
            @contextmanager
            def temporary(**kwargs):
                events.append('temp-enter')
                try:yield '/fabricated/new'
                finally:events.append('temp-cleanup')
            class Connection:
                def __enter__(self):events.append('connect');return self
                def __exit__(self,*args):events.append('disconnect')
                def execute(self,sql):
                    events.append(sql)
                    return NS(scalar_one=lambda:1 if mode=='nonempty' else 0)
            engine=NS(connect=lambda:Connection(),dispose=lambda:events.append('dispose'))
            def database(url):events.append('database');return NS(engine=engine)
            def factory(**kwargs):
                events.append('factory')
                if mode=='factory-error':raise RuntimeError('fabricated failure')
                return NS(state=NS(db=kwargs['db']))
            tables={'cases','evidence_items','custody_events','audit_events','access_policies','archive_import_history','image_ocr_review_records'}
            class Adapter:
                def __init__(self,*args):events.append('adapter')
                def close(self):events.append('close')
            tree=ast.parse((ROOT/'tools/pilot_image_acceptance/host_adapter.py').read_text())
            fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='owned_creation_scope')
            fn=Strip().visit(fn)
            env=dict(contextmanager=contextmanager,CreationAuthority=s.scope['CreationAuthority'],checked=checked,
                     Path=FakePath,TemporaryDirectory=temporary,Database=database,create_local_review_pilot=factory,
                     Ctx=object,Request=object,inspect=lambda e:NS(get_table_names=lambda:tables),text=lambda x:x,CreationAdapter=Adapter)
            exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'<owned scope fake resources>','exec'),env)
            try:
                with env['owned_creation_scope'](authority=authority,approved_host=None if mode=='missing-host' else NS(isolated_workspace=isolated)):
                    events.append('yielded')
                    if mode=='continuation-error':raise RuntimeError('fabricated continuation failure')
            except (RuntimeError,Stopped):
                self.assertNotEqual(mode,'normal')
            else:self.assertEqual(mode,'normal')
            if mode=='missing-host':self.assertEqual(events,[]);continue
            self.assertEqual(events[-3:],['dispose','temp-cleanup','host-exit'])
            self.assertLess(events.index('host-enter'),events.index('database'))
            if mode in ('normal','continuation-error'):
                self.assertEqual(events.count('close'),1)
                self.assertEqual(sum(isinstance(x,str) and x.startswith('SELECT COUNT(*)') for x in events),7)
            else:self.assertNotIn('yielded',events)
            with self.assertRaises(Stopped):authority.claim()

    def test_host_resource_order_static_no_runtime_execution(self):
        tree=ast.parse((ROOT/'tools/pilot_image_acceptance/host_adapter.py').read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='owned_creation_scope')
        source=ast.unparse(fn)
        markers=['approved_host is not None','authority.claim()', 'approved_host.isolated_workspace()', 'TemporaryDirectory(', "not db_path.exists()",'db = Database(', 'create_local_review_pilot(', 'inspect(db.engine)', 'SELECT COUNT(*)', 'CreationAdapter(', 'yield ', 'adapter.close()', 'db.engine.dispose()']
        pos=[source.index(m) for m in markers];self.assertEqual(pos,sorted(pos))
        self.assertTrue(any(isinstance(n,ast.Try) and n.finalbody for n in ast.walk(fn)))
        self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ('unlink','rmtree','launch','run','serve') for n in ast.walk(fn)))
        self.assertNotIn('main',source);self.assertNotIn('models_registry',source)
        self.assertIn('image_imports=True',source);self.assertIn('evidence_registration=True',source)
        # This does NOT execute DB construction, host checks, filesystem or cleanup.

if __name__=='__main__':unittest.main()
