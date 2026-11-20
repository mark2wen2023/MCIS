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
    def test_container_positive_failure_timeout_and_gate(self):
        image='sha256:'+'a'*64;cid='b'*64
        for mode in ('ok','unapproved','bad-network','nonzero','timeout','create-timeout'):
            calls=[]
            def execute(argv,**kwargs):
                self.assertEqual(argv[0],'docker');calls.append(argv[1:])
                args=argv[1:]
                if args[:2]==['image','inspect']:
                    data=[{'Id':image,'Config':{'User':'65532:65532','Env':['PATH=/opt/pilot/bin:/usr/bin:/bin','LANG=C.UTF-8']}}]
                elif args[0]=='create':
                    if mode=='create-timeout':raise subprocess.TimeoutExpired(argv,20)
                    return NS(stdout=cid+'\n')
                elif args[0]=='inspect':
                    data=[{'Image':image,'State':{'Running':False},'HostConfig':{
                       'NetworkMode':'bridge' if mode=='bad-network' else 'none','ReadonlyRootfs':True,
                       'Privileged':False,'IpcMode':'private','CapDrop':['ALL'],'SecurityOpt':['no-new-privileges'],
                       'LogConfig':{'Type':'none'},'Tmpfs':{'/run/pilot':'rw,nosuid,nodev,size=512m,mode=0700,uid=65532,gid=65532','/tmp':'rw,nosuid,nodev,size=128m,mode=1777'}},
                       'Config':{'Labels':{'mcis.pilot.owner':'c'*32},'User':'65532:65532','Cmd':[*env['COMMAND'],'--subject','SYN-PILOT-reviewer','--role','LeadInvestigator']}}]
                elif args[0]=='wait':
                    if mode=='timeout':raise subprocess.TimeoutExpired(argv,240)
                    return NS(stdout='1' if mode=='nonzero' else '0')
                else:return NS(stdout='')
                return NS(stdout=json.dumps(data))
            env=extracted('tools/pilot_image_acceptance/container_runner.py',dict(subprocess=subprocess,json=json,re=re,secrets=NS(token_hex=lambda n:'c'*32),sys=NS(stderr=None)))
            if mode!='unapproved':env['APPROVED_IMAGES']=frozenset({image})
            try:result=env['run_container'](image,'SYN-PILOT-reviewer','LeadInvestigator',execute=execute)
            except (RuntimeError,subprocess.TimeoutExpired):self.assertNotEqual(mode,'ok')
            else:self.assertEqual(result['status'],'passed');self.assertEqual(mode,'ok')
            if mode=='unapproved':self.assertEqual(calls,[]);continue
            self.assertEqual(calls[-1],['rm','--force','mcis-pilot-'+'c'*32 if mode=='create-timeout' else cid])
            create=next(c for c in calls if c[0]=='create')
            self.assertIn('--network=none',create);self.assertIn('--pull=never',create)
            self.assertFalse(any(x in create for x in ('-v','--volume','--privileged','--publish')))
            if mode=='bad-network':self.assertFalse(any(c[0]=='start' for c in calls))

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
            host=env['RuntimeHost']('SYN-PILOT-reviewer','LeadInvestigator')
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
            env=dict(asynccontextmanager=asynccontextmanager,asyncio=asyncio,uvicorn=NS(Server=Server,Config=config))
            exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'<fake server only>','exec'),env)
            try:
                async with env['serving'](object(),'fake-key','fake-cert'):
                    events.append('yielded')
                    if mode=='body-error':raise Stop('synthetic failure')
            except RuntimeError:self.assertNotEqual(mode,'ok')
            else:self.assertEqual(mode,'ok')
            if mode=='early-exit':self.assertNotIn('yielded',events)
            else:self.assertEqual(events[-1],'stopped')
        for mode in ('ok','early-exit','body-error'):asyncio.run(scenario(mode))

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
        self.assertIn('await review_in_same_origin_page(self.page,prepared)',runtime)
        self.assertIn('APPROVED_IMAGES = frozenset()',controller)
        for name in ('runtime_host.py','container_runner.py','container_entry.py'):ast.parse((root/name).read_text())

if __name__=='__main__':unittest.main()
