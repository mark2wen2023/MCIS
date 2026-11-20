"""Only standard library, AST and handwritten executors: no container/app/HTTP."""
import ast
import asyncio
from contextlib import asynccontextmanager,contextmanager,AsyncExitStack
import hashlib
from pathlib import Path,PurePosixPath
import subprocess
from types import SimpleNamespace as NS
import unittest
import json
import re
import time
ROOT=Path(__file__).resolve().parents[2]
class Stop(RuntimeError):pass
def checked(ok,msg):
    if not ok:raise Stop(msg)
class Strip(ast.NodeTransformer):
    def visit_Import(self,node):return None
    def visit_ImportFrom(self,node):return None

def extracted(path,env):
    tree=Strip().visit(ast.parse((ROOT/path).read_text()))
    tree.body=[n for n in tree.body if not isinstance(n,ast.If)]
    exec(compile(ast.fix_missing_locations(tree),'<production source with handwritten imports>','exec'),env)
    return env

class RuntimeChecks(unittest.TestCase):
    def test_runtime_lifetime_real_control_flow_fake_resources(self):
        async def scenario(mode):
            events=[];opaque='fabricated-not-a-credential';captured=[]
            def preflight():
                events.append('preflight')
                if mode=='preflight-fail':raise Stop('synthetic preflight rejection')
            @contextmanager
            def temporary(**kw):
                events.append('temp-open')
                try:yield '/fabricated'
                finally:events.append('temp-close')
            @contextmanager
            def owned(**kw):
                events.append('owned-open')
                try:yield NS(create_case=None),object(),PurePosixPath('/fabricated/db')
                finally:events.append('owned-close')
            @asynccontextmanager
            async def serve(*args):
                events.append('server-start')
                try:yield
                finally:events.append('server-stop')
            class Page:
                url='https://127.0.0.1:8766/pilot'
                def set_default_timeout(self,t):pass
                async def goto(self,url):
                    events.append('health')
                    if mode=='health-fail':raise Stop('synthetic health error')
                    return NS(status=200)
            class Context:
                async def add_cookies(self,cookies):captured.extend(cookies);events.append('cookie')
                async def new_page(self):return Page()
                async def close(self):events.append('context-close')
            class Browser:
                async def new_context(self,**kw):
                    selftest.assertEqual(kw,{'ignore_https_errors':False,'service_workers':'block'})
                    return Context()
                async def close(self):events.append('browser-close')
            async def launch(**kw):
                selftest.assertTrue(kw['chromium_sandbox']);events.append('browser-open');return Browser()
            @asynccontextmanager
            async def playwright():
                events.append('pw-open')
                try:yield NS(chromium=NS(launch=launch))
                finally:events.append('pw-close')
            class Sessions:
                def __init__(self,entries):events.append('session-issued')
                def revoke(self,digest):events.append('revoke')
            env=dict(asynccontextmanager=asynccontextmanager,contextmanager=contextmanager,AsyncExitStack=AsyncExitStack,
                     asyncio=asyncio,Path=PurePosixPath,checked=checked,time=time,hashlib=hashlib,re=re,
                     secrets=NS(token_urlsafe=lambda n:opaque),tempfile=NS(TemporaryDirectory=temporary),
                     PilotSessions=Sessions,PilotSession=lambda *a:a,COOKIE_NAME='__Host-MCIS-Pilot',
                     CreationConfig=lambda *a:a,CreationAuthority=lambda c:c,owned_creation_scope=owned,
                     async_playwright=playwright,CASE_IDS=('SYN-PILOT-A','SYN-PILOT-B'),
                     cases=lambda:[{'caseId':'SYN-PILOT-A'},{'caseId':'SYN-PILOT-B'}],encoded=lambda x:b'fabricated',sha=lambda x:'a'*64)
            extracted('tools/pilot_image_acceptance/runtime_host.py',env)
            env.update(preflight=preflight,tls_files=lambda root:('key','cert',PurePosixPath('/fabricated/home')),serving=serve)
            progress=NS(mark=lambda stage:events.append('stage:'+stage),cleaned=lambda:events.append('inner-cleanup-confirmed'))
            host=env['RuntimeHost']('SYN-PILOT-reviewer','LeadInvestigator',progress)
            try:
                async with host.approved_scope():
                    events.append('workflow')
                    if mode=='workflow-fail':raise Stop('synthetic workflow error')
                    if mode=='cancel':raise asyncio.CancelledError()
            except (Stop,asyncio.CancelledError):selftest.assertNotEqual(mode,'ok')
            else:selftest.assertEqual(mode,'ok')
            if mode=='preflight-fail':selftest.assertEqual(events,['preflight']);return
            selftest.assertLess(events.index('preflight'),events.index('session-issued'))
            for a,b in zip(('context-close','browser-close','pw-close','server-stop','owned-close','temp-close'),('browser-close','pw-close','server-stop','owned-close','temp-close','revoke')):
                selftest.assertLess(events.index(a),len(events)-1 if b=='revoke' else events.index(b))
            selftest.assertIn('stage:preflight',events);selftest.assertIn('inner-cleanup-confirmed',events)
            if mode!='health-fail':selftest.assertIn('stage:https_ready',events)
            selftest.assertIn('revoke',events);selftest.assertIsNone(host.page);selftest.assertIsNone(host.creator)
            selftest.assertTrue(captured[0]['secure'] and captured[0]['httpOnly']);selftest.assertEqual(captured[0]['sameSite'],'Strict')
            with selftest.assertRaises(Stop):
                async with host.approved_scope():pass
        selftest=self
        for mode in ('ok','preflight-fail','health-fail','workflow-fail','cancel'):asyncio.run(scenario(mode))

    def test_server_startup_and_shutdown_with_fake_uvicorn(self):
        fn=next(n for n in ast.parse((ROOT/'tools/pilot_image_acceptance/runtime_host.py').read_text()).body
                if isinstance(n,ast.AsyncFunctionDef) and n.name=='serving')
        fn=Strip().visit(fn)
        async def scenario(mode):
            events=[]
            class Server:
                def __init__(self,config):self.started=False;self.should_exit=False;self.force_exit=False
                async def serve(self):
                    events.append('start')
                    if mode=='early-exit':return
                    self.started=True
                    try:
                        while not self.should_exit:await asyncio.sleep(0)
                    finally:events.append('stopped')
            def config(app,**kw):
                self.assertEqual((kw['host'],kw['port']),('127.0.0.1',8766))
                self.assertFalse(kw['access_log']);return kw
            async def shutdown_timeout(awaitable,timeout):raise TimeoutError('synthetic shutdown deadline')
            api=NS(**{name:getattr(asyncio,name) for name in ('create_task','timeout','sleep','shield','gather','CancelledError','wait_for')})
            if mode=='shutdown-timeout':api.wait_for=shutdown_timeout
            env=dict(asynccontextmanager=asynccontextmanager,asyncio=api,uvicorn=NS(Server=Server,Config=config))
            exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'<fake server only>','exec'),env)
            try:
                async with env['serving'](object(),'fake-key','fake-cert'):
                    events.append('yielded')
                    if mode=='body-error':raise Stop('synthetic failure')
            except RuntimeError:self.assertNotEqual(mode,'ok')
            else:self.assertEqual(mode,'ok')
            if mode=='early-exit':self.assertNotIn('yielded',events)
            else:self.assertEqual(events[-1],'stopped')
        for mode in ('ok','early-exit','body-error','shutdown-timeout'):asyncio.run(scenario(mode))

    def test_preflight_uses_observed_facts_not_boolean(self):
        source=ast.parse((ROOT/'tools/pilot_image_acceptance/runtime_host.py').read_text())
        fn=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='preflight')
        for mode in ('ok','root-user','env','network','rw-root','disk-workspace','nonempty','socket','source'):
            class FakePath:
                def __init__(self,value):self.value=value
                def iterdir(self):
                    if self.value=='/sys/class/net':return [NS(name=n) for n in (('lo','eth0') if mode=='network' else ('lo',))]
                    return [object()] if mode=='nonempty' else []
                def read_text(self):
                    return '1 0 0:1 / / '+('rw' if mode=='rw-root' else 'ro')+' - overlay overlay ro\n2 1 0:2 / /run/pilot rw - '+('ext4' if mode=='disk-workspace' else 'tmpfs')+' tmpfs rw'
                def exists(self):return mode=='socket'
                def resolve(self):return self
                def is_relative_to(self,path):return mode!='source'
            env=dict(checked=checked,os=NS(geteuid=lambda:0 if mode=='root-user' else 65532,
                     environ={'UNEXPECTED':'not-read'} if mode=='env' else {'PATH':'not-read'}),Path=FakePath,__file__='fake')
            exec(compile(ast.Module(body=[fn],type_ignores=[]),'<preflight fake filesystem>','exec'),env)
            if mode=='ok':env['preflight']()
            else:
                with self.assertRaises(Stop):env['preflight']()

    def test_source_boundaries(self):
        root=ROOT/'tools/pilot_image_acceptance'
        runtime=(root/'runtime_host.py').read_text();controller=(root/'container_runner.py').read_text()
        self.assertNotIn('no-sandbox',runtime);self.assertNotIn('ignore_https_errors=True',runtime)
        self.assertNotIn('X-MCIS',runtime);self.assertNotIn('models_registry',runtime)
        self.assertIn('prepare_registered_case_a(host=RuntimeHost',runtime)
        self.assertIn('await review_in_same_origin_page(self.page,prepared,mark=self.mark)',runtime)
        self.assertIn('APPROVED_IMAGES = frozenset()',controller)
        for name in ('runtime_host.py','container_runner.py','container_entry.py'):ast.parse((root/name).read_text())

if __name__=='__main__':unittest.main()
