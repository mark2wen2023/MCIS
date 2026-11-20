"""UNEXECUTED runtime for a reviewed offline image; not a general host launcher.
Invoked only by container_runner with its reviewed-image allowlist. No 4A/login.
"""
import argparse
import asyncio
from contextlib import asynccontextmanager, contextmanager, AsyncExitStack
import hashlib
import os
import re
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
from .fixtures import CASE_IDS, cases, encoded, sha
from .authority import CreationAuthority, CreationConfig
from .host_adapter import owned_creation_scope
from .prepare import checked, prepare_registered_case_a
from .browser_steps import review_in_same_origin_page

ORIGIN='https://127.0.0.1:8766'
OPERATIONS=frozenset({'case.read','evidence.preview','evidence.register','evidence.receipt.read',
                      'image.list','image.import','image.read','image.revise'})


def preflight():
    # Runtime corroboration, NOT a substitute for the controller's pinned,
    # reviewed image and Docker inspect. Never run against a business checkout.
    checked(os.geteuid()==65532,'Dedicated container user required')
    checked(set(os.environ)<= {'PATH','LANG','HOSTNAME','HOME'},'Unexpected process environment')
    checked({p.name for p in Path('/sys/class/net').iterdir()}=={'lo'},'External network interface present')
    mounts=[line.split() for line in Path('/proc/self/mountinfo').read_text().splitlines()]
    root=[m for m in mounts if m[4]=='/'];workspace=[m for m in mounts if m[4]=='/run/pilot']
    checked(len(root)==1 and 'ro' in root[0][5].split(','),'Read-only image required')
    checked(len(workspace)==1 and workspace[0][workspace[0].index('-')+1]=='tmpfs','Private tmpfs required')
    checked(not any(Path('/run/pilot').iterdir()),'New empty owned workspace required')
    checked(not Path('/var/run/docker.sock').exists(),'Container control socket forbidden')
    # Trusted image construction must freeze Python/dependencies, source/schema
    # allowlist and sandbox-capable Chromium. No checkout/editable/user packages.
    checked(Path(__file__).resolve().is_relative_to('/opt/pilot/source'),'Frozen source location required')


def tls_files(root):
    """Ephemeral private CA, trusted only by this newly owned browser HOME."""
    def run(args):
        subprocess.run(args,check=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL,timeout=15)
    key=root/'tls.key';cert=root/'tls.pem';home=root/'browser-home';home.mkdir()
    run(['/usr/bin/openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1',
         '-subj','/CN=MCIS synthetic loopback only','-addext','subjectAltName=IP:127.0.0.1',
         '-addext','basicConstraints=critical,CA:TRUE','-keyout',str(key),'-out',str(cert)])
    key.chmod(0o600)
    nss=home/'.pki'/'nssdb';nss.mkdir(parents=True)
    run(['/usr/bin/certutil','-N','--empty-password','-d','sql:'+str(nss)])
    run(['/usr/bin/certutil','-A','-d','sql:'+str(nss),'-n','synthetic-local-only','-t','C,,','-i',str(cert)])
    return key,cert,home


@asynccontextmanager
async def serving(app,key,cert):
    import uvicorn
    server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=8766,
        ssl_keyfile=str(key),ssl_certfile=str(cert),access_log=False,log_config=None,log_level='critical'))
    task=asyncio.create_task(server.serve())
    try:
        async with asyncio.timeout(15):
            while not server.started:
                if task.done():
                    await task
                    raise RuntimeError('Server exited before ready')
                await asyncio.sleep(.05)
        yield
    finally:
        server.should_exit=True
        try:await asyncio.wait_for(asyncio.shield(task),10)
        except (TimeoutError,asyncio.CancelledError):
            server.force_exit=True;task.cancel()
            await asyncio.gather(task,return_exceptions=True)
            raise RuntimeError('Server shutdown not confirmed') from None
        # Outer controller's deadline force-removes owned container if the
        # runtime/event loop cannot stop; no background process may survive it.


class RuntimeHost:
    def __init__(self,subject,role,progress=None):
        checked(isinstance(subject,str) and subject.startswith('SYN-PILOT-') and subject.strip()==subject,
                'Explicit synthetic server subject required')
        checked(role in ('Investigator','LeadInvestigator'),'Explicit creation role required')
        self.progress=progress
        self.subject=subject;self.role=role;self.page=None;self.creator=None;self._used=False

    def mark(self,stage):
        if self.progress is not None:self.progress.mark(stage)

    @asynccontextmanager
    async def approved_scope(self):
        checked(not self._used,'Host scope already consumed');self._used=True
        preflight()  # BEFORE importing any business/ORM/FastAPI or issuing session.
        self.mark('preflight')
        from mcis_service.common.local_review_pilot import PilotSessions,PilotSession,COOKIE_NAME
        from playwright.async_api import async_playwright
        token=secrets.token_urlsafe(32);digest=hashlib.sha256(token.encode('ascii')).hexdigest()
        deadline=time.monotonic()+180
        sessions=PilotSessions({digest:PilotSession(self.subject,self.role,deadline,
            frozenset((cid,op) for cid in CASE_IDS for op in OPERATIONS))})
        config=CreationConfig(self.subject,self.role,deadline,
            frozenset((d['caseId'],'case.create',sha(encoded(d))) for d in cases()))
        authority=CreationAuthority(config)
        try:
            stack=AsyncExitStack()
            try:
                root=Path(stack.enter_context(tempfile.TemporaryDirectory(prefix='acceptance-',dir='/run/pilot')))
                class Workspace:
                    @contextmanager
                    def isolated_workspace(self):yield root
                self.creator,app,_=stack.enter_context(owned_creation_scope(authority=authority,
                    approved_host=Workspace(),sessions=sessions,origin=ORIGIN))
                key,cert,home=tls_files(root)
                await stack.enter_async_context(serving(app,key,cert))
                pw=await stack.enter_async_context(async_playwright())
                browser=await pw.chromium.launch(headless=True,chromium_sandbox=True,
                    executable_path='/opt/pilot/chromium/chrome',
                    env={'PATH':'/usr/bin:/bin','HOME':str(home),'TMPDIR':str(root),'LANG':'C.UTF-8'})
                stack.push_async_callback(browser.close)
                context=await browser.new_context(ignore_https_errors=False,service_workers='block')
                stack.push_async_callback(context.close)
                # Fresh synthetic credential created in this server scope only;
                # HttpOnly cookie is installed through trusted bootstrap, never JS.
                await context.add_cookies([{'name':COOKIE_NAME,'value':token,'domain':'127.0.0.1','path':'/',
                                           'secure':True,'httpOnly':True,'sameSite':'Strict'}])
                token=None
                self.page=await context.new_page()
                self.page.set_default_timeout(10000)
                response=await self.page.goto(ORIGIN+'/pilot')
                checked(response is not None and response.status==200,'HTTPS shell readiness failed')
                self.mark('https_ready')
                yield
            finally:
                sessions.revoke(digest)
                await stack.aclose()
                if self.progress is not None:self.progress.cleaned()
        finally:
            sessions.revoke(digest);token=None;self.page=None;self.creator=None

    async def create_case(self,body):
        checked(self.creator is not None,'No preparation scope')
        return await self.creator.create_case(body)

    async def request(self,method,path,body):
        checked(self.page is not None and self.page.url.startswith(ORIGIN+'/'),'No authenticated page')
        base=r'/api/v1/cases/(?:SYN-PILOT-A|SYN-PILOT-B)'
        allowed=(method=='GET' and re.fullmatch(base+r'(?:/image-reviews|/evidence-intakes/[0-9a-f]{64})?',path)) or (method=='POST' and re.fullmatch(base+r'/evidence-intakes:(?:preview|commit)',path))
        checked(allowed,'Request outside fixed preparation routes')
        # Real browser same-origin fetch supplies Origin/Sec-Fetch-Site/Cookie.
        # No fabricated security headers, no retry and no returned credential.
        result=await self.page.evaluate('''async ({method,path,body}) => {
            const response=await fetch(path,{method,credentials:'same-origin',redirect:'error',
              headers:body===null?{}:{'Content-Type':'application/json'},
              body:body===null?undefined:JSON.stringify(body)});
            return [response.status,await response.json()];
        }''',{'method':method,'path':path,'body':body})
        return result

    async def review_in_same_origin_page(self,prepared):
        return await review_in_same_origin_page(self.page,prepared,mark=self.mark)


async def run(subject,role,progress=None):
    async with asyncio.timeout(150):
        return await prepare_registered_case_a(host=RuntimeHost(subject,role,progress))


def main():
    from .receipt import Receipt
    parser=argparse.ArgumentParser();parser.add_argument('--subject',required=True)
    parser.add_argument('--role',required=True,choices=('Investigator','LeadInvestigator'))
    parser.add_argument('--image',required=True)
    args=parser.parse_args();progress=Receipt(args.image)
    try:
        asyncio.run(run(args.subject,args.role,progress))
        raw=progress.finish(True)
    except BaseException:raw=progress.finish(False)
    return progress.value['exitCode'],raw
