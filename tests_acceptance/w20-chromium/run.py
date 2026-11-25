"""W20 test-only pinned Linux Chrome + local app and SQLite; never deploy this fixture."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shutil
import subprocess
import tempfile
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

HERE = Path(__file__).resolve().parent
HTML = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="stylesheet" href="/{script}.css"><div id="root"></div><script type="module" src="/{script}.js"></script></html>'

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None

OPENER = build_opener(ProxyHandler({}), NoRedirect())
ENV = {k: os.environ[k] for k in ('HOME','PATH','LD_LIBRARY_PATH','LANG','LC_ALL','TMPDIR') if k in os.environ}

def env_for(work):
    home = work / 'home'
    home.mkdir(exist_ok=True)
    return {**ENV, 'HOME':str(home),'XDG_CACHE_HOME':str(home/'cache'), 'TMPDIR':str(work), 'PYTHONDONTWRITEBYTECODE':'1'}

def blob(p):
    data = p.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()

def stage(src, work):
    pin = json.loads((HERE / 'pins.json').read_text())
    dest = work / 'fixed'
    for rel, expected in pin['paths'].items():
        p = src / rel
        assert p.is_file() and blob(p) == expected, f'Fixed product artifact missing or different: {rel}'
        q = dest / rel
        q.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, q)
        assert blob(q) == expected
    print(f"W20 pins: {len(pin['paths'])} exact Git blobs at {pin['product']}", flush=True)
    return dest

def build(fixed, deps, work):
    web = fixed / 'web'
    (web / 'node_modules').symlink_to(deps, target_is_directory=True)
    shutil.copyfile(HERE / 'component.tsx', web / 'component.tsx')
    assets = work / 'assets'
    assets.mkdir()
    env = env_for(work)
    for entry, name in [('src/main.tsx','app'), ('component.tsx','component')]:
        subprocess.run([str(deps / '.bin/esbuild'), entry, '--bundle', '--platform=browser', '--format=esm',
                        '--jsx=automatic', '--define:process.env.NODE_ENV="production"', '--log-level=warning',
                        '--loader:.svg=dataurl', f'--outfile={assets / (name + ".js")}'],
                       cwd=web, env=env, check=True)
        print(f"Built {name} JS bytes={ (assets / (name + '.js')).stat().st_size }", flush=True)
    (assets / 'index.html').write_text(HTML.format(script='app'))
    fixture = assets / 'component'
    fixture.mkdir()
    (fixture / 'index.html').write_text(HTML.format(script='component'))
    return assets

@contextmanager
def host(args, fixed, assets, data, ev, suffix):
    env = {**env_for(data.parent),'PYTHONPATH':str(fixed / 'service')}
    with (ev / ('service-' + suffix + '.stderr')).open('w') as stderr:
        proc = subprocess.Popen([str(args.host_python), str(HERE / 'host.py'),
          str(data.parent/'model-fixture.json'), str(assets), str(data)],
          cwd=data.parent, env=env, text=True, stdout=subprocess.PIPE, stderr=stderr)
        try:
            line = proc.stdout.readline().strip() if select.select([proc.stdout],[],[],20)[0] else ''
            (ev / ('service-' + suffix + '.stdout')).write_text(line+'\n')
            assert re.fullmatch(r'W20_LOOPBACK_PORT=[1-9][0-9]{3,4}', line), 'Fixture service did not start'
            origin = 'http://127.0.0.1:' + line.split('=')[1]
            import time
            for _ in range(100):
                try:
                    with OPENER.open(origin+'/api/v1/health',timeout=1) as reply:
                        if reply.status == 200:
                            break
                except OSError:
                    time.sleep(.1)
            else:
                raise RuntimeError('Fixture service not ready')
            yield origin
        finally:
            if proc.poll() is None:
                proc.terminate()
                try: proc.wait(8)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            proc.stdout.close()

def send(origin, fixture, method, path, expected, payload=None):
    assert urlsplit(origin).hostname == '127.0.0.1' and path.startswith('/api/v1/')
    req = Request(origin+path, method=method, headers={**fixture.LEAD,'Content-Type':'application/json'},
          data=None if payload is None else json.dumps(payload).encode())
    try:
        with OPENER.open(req, timeout=8) as res:
            code, body = res.status, json.load(res)
    except HTTPError as e:
        code, body = e.code, json.load(e)
    assert code == expected, f'Fixed synthetic fixture operation unexpected: {method} {path} {code}, expected {expected}'
    return body

def case_setup(origin, f):
    send(origin,f,'POST','/api/v1/cases',201,f.DOC)
    send(origin,f,'POST',f.INTERVIEWS,201,{'recordId':f.RECORD,'interviewee':{'intervieweeId':'SYN-P','name':'Synthetic Person','role':'Synthetic Position','affiliation':'Synthetic organization'},'startUtc':'2026-01-01T00:00:00Z','statements':[]})
    send(origin,f,'POST',f'{f.INTERVIEWS}/{f.RECORD}/turns',201,{'question':'What was requested?','answer':f.QUOTE})

def drift(origin, f):
    send(origin,f,'POST',f'{f.INTERVIEWS}/{f.RECORD}/turns',201,{'question':'Any confirmation?','answer':'Synthetic addition; execution not stated.'})

def pending(origin,f):
    rows = send(origin,f,'GET',f'{f.INTERVIEWS}/{f.RECORD}',200)['statements']
    drafts = send(origin,f,'GET',f.DRAFTS,200)
    assert rows == [] and len(drafts) == 1 and drafts[0]['status'] == 'PendingReview'
    assert drafts[0]['citations'] == [{'recordId':f.RECORD,'round':1,'quote':f.QUOTE}]
    return drafts[0]

def read_fixture(path):
    # Runner Python need not have service dependencies; load only fixed literals via AST.
    import ast
    from types import SimpleNamespace
    tree = ast.parse(path.read_text())
    data = {}
    names = ('CASE','RECORD','ROOT','INTERVIEWS','DRAFTS','LEAD','QUOTE','DOC','ITEM')

    def literal(node):
        if isinstance(node,ast.Constant):
            return node.value
        if isinstance(node,ast.Name) and node.id in data:
            return data[node.id]
        if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Add):
            return literal(node.left)+literal(node.right)
        if isinstance(node,ast.FormattedValue) and node.conversion == -1 and node.format_spec is None:
            return str(literal(node.value))
        if isinstance(node,ast.JoinedStr):
            return ''.join(literal(v) for v in node.values)
        if isinstance(node,ast.Dict):
            return {literal(k):literal(v) for k,v in zip(node.keys,node.values)}
        raise ValueError(f'Unsupported fixed synthetic fixture literal: {type(node).__name__}')
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0], ast.Name):
            key = node.targets[0].id
            if key not in names:
                continue
            data[key] = literal(node.value)
    assert set(names) == set(data)
    return SimpleNamespace(**data)

def guarded_context(browser, origin, size):
    ctx = browser.new_context(viewport={'width':size[0], 'height':size[1]}, service_workers='block')
    blocked = []
    def route(r):
        p = urlsplit(r.request.url)
        if (p.scheme,p.netloc) == ('http',urlsplit(origin).netloc):
            r.continue_()
        else:
            blocked.append('non-loopback request')
            r.abort()
    ctx.route('**/*', route)
    ctx.route_web_socket('**/*', lambda route: (blocked.append('WebSocket'),route.close()))
    return ctx, blocked

def component(browser,origin,ev):
    from playwright.sync_api import expect
    ctx, blocked = guarded_context(browser,origin,(1440,900))
    try:
        page = ctx.new_page()
        errors = []
        page.on('pageerror',lambda _:errors.append('pageerror'))
        page.goto(origin+'/component/')
        check = page.get_by_role('checkbox')
        confirm = page.get_by_role('button',name='确认以上陈述并写回')
        select_phase = lambda n: page.get_by_role('button',name=n,exact=True).click()
        expect(confirm).to_be_disabled()
        check.check()
        expect(confirm).to_be_enabled()
        select_phase('same')
        expect(confirm).to_be_enabled()
        select_phase('missing')
        expect(check).to_be_disabled()
        expect(confirm).to_be_disabled()
        expect(page.get_by_test_id('local-decisions')).to_have_text('0')
        page.screenshot(path=str(ev/'01-component-missing.png'), full_page=True)
        select_phase('baseline')
        expect(check).not_to_be_checked()
        expect(confirm).to_be_disabled()
        check.check()
        select_phase('changed')
        expect(check).not_to_be_checked()
        expect(confirm).to_be_disabled()
        for phase in ('ambiguousQuote','ambiguousRound'):
            select_phase(phase)
            expect(check).to_be_disabled()
            expect(confirm).to_be_disabled()
            expect(page.get_by_test_id('local-decisions')).to_have_text('0')
        select_phase('baseline')
        expect(confirm).to_be_disabled()
        check.check()
        confirm.click()
        expect(page.get_by_test_id('local-decisions')).to_have_text('1')
        assert not blocked and not errors
        print('Component-only true Chromium: 7 synthetic phases, no service writes')
    finally:
        ctx.close()

def product(browser,origin,f,ev,expected_draft=None):
    reopened = expected_draft is not None
    from playwright.sync_api import expect
    size = (390,844) if reopened else (1440,900)
    ctx, blocked = guarded_context(browser,origin,size)
    identity = {'mcis.role':f.LEAD['X-MCIS-Role'],'mcis.operator':f.LEAD['X-MCIS-Operator']}
    ctx.add_init_script('for (const [k,v] of Object.entries('+json.dumps(identity)+')) localStorage.setItem(k,v)')
    try:
        page = ctx.new_page()
        errors = []
        page.on('pageerror',lambda _:errors.append('pageerror'))
        reviews = []
        page.on('request',lambda req: reviews.append(req.method)
                if req.method=='POST' and '/agents/drafts/' in req.url and req.url.endswith('/review') else None)
        page.goto(origin+f'/#/interview?case={f.CASE}&record={f.RECORD}')
        panel = page.get_by_test_id('w20-agent')
        expect(panel).to_be_visible(timeout=15000)
        draft = panel.get_by_role('article')
        extract = panel.get_by_role('button',name='提取当前笔录为待审草稿')
        confirm = panel.get_by_role('button',name='确认以上陈述并写回')
        if not reopened:
            expect(extract).to_be_enabled(timeout=15000)
            with page.expect_response(lambda r: r.url.endswith(':extract') and r.request.method=='POST') as create:
                extract.click()
            assert create.value.status==201
            expect(draft).to_contain_text('待人工审核')
            ack = draft.get_by_role('checkbox')
            expect(confirm).to_be_disabled()
            ack.check()
            expect(confirm).to_be_enabled()
            drift(origin,f)  # supported synthetic interview append, genuine concurrent update
            with page.expect_response(lambda r: '/agents/drafts/' in r.url and r.url.endswith('/review') and r.request.method=='POST') as review:
                confirm.click()
            assert review.value.status == 409 and review.value.json()['code']=='SOURCE_CHANGED'
            # The normal layout reloads the record after the request settles. Do not
            # require a transient alert to persist across that normal remount.
            expect(draft).to_contain_text('待人工审核')
            expect(confirm).to_be_disabled()
            assert reviews == ['POST']
            page.screenshot(path=str(ev/'02-product-source-changed.png'), full_page=True)
            first = pending(origin,f)['draftId']
            assert first == create.value.json()['draftId']
            print('Product W5 interview true Chrome desktop: stale source rejected; no statement written')
            assert not blocked and not errors
            return first
        else:
            expect(draft).to_contain_text('待人工审核', timeout=15000)
            expect(draft.get_by_role('checkbox')).not_to_be_checked()
            expect(confirm).to_be_disabled()
            page.screenshot(path=str(ev/'03-product-reopened.png'), full_page=True)
            assert not reviews and pending(origin,f)['draftId'] == expected_draft
            print('Product fresh 390px browser after actual restart: still pending; zero statements')
        assert not blocked and not errors
    finally:
        ctx.close()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--node-modules', type=Path, required=True)
    p.add_argument('--host-python', type=Path)
    p.add_argument('--browser', type=Path)
    p.add_argument('--evidence', type=Path)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--build-only', action='store_true')
    mode.add_argument('--http-only', action='store_true')
    a = p.parse_args()
    if not a.build_only:
        if not a.evidence or not a.host_python or (not a.http_only and not a.browser):
            p.error('actual service needs --evidence and --host-python; true Chrome also needs --browser')
        if any(not x.is_absolute() for x in [a.host_python,a.evidence,*([a.browser] if a.browser else [])]):
            p.error('supply absolute tool/evidence paths')
        a.evidence.mkdir()
    receipt = {'buildOnly':a.build_only,'httpOnly':a.http_only,'result':'failed','trueBrowser':False}
    try:
        with tempfile.TemporaryDirectory(prefix='mcis-w20-syn-') as t:
            work = Path(t)
            fixed = stage(a.source.resolve(),work)
            assets = build(fixed,a.node_modules.resolve(),work)
            if a.build_only:
                receipt['result']='passed'
                return
            data = work/'synthetic-data'
            data.mkdir()
            fixture=read_fixture(fixed/'tests_acceptance/w20-visible-context/check_service.py')
            (work/'model-fixture.json').write_text(json.dumps({'statements':[fixture.ITEM]}))
            if a.http_only:
                with host(a,fixed,assets,data,a.evidence,'initial') as origin:
                    case_setup(origin,fixture)
                    compare=send(origin,fixture,'GET',f'{fixture.ROOT}/interview-compare/{fixture.RECORD}',200)
                    assert compare['caseId']==fixture.CASE and compare['recordId']==fixture.RECORD
                    assert compare['turns'][0]['answer']==fixture.QUOTE
                    d=send(origin,fixture,'POST',f'{fixture.ROOT}/agents/people_ops/interviews/{fixture.RECORD}:extract',201,{})
                    drift(origin,fixture)
                    result=send(origin,fixture,'POST',fixture.DRAFTS+'/'+d['draftId']+'/review',409,{'decision':'Confirmed','note':''})
                    assert result['code']=='SOURCE_CHANGED'
                    assert pending(origin,fixture)['draftId']==d['draftId']
                with host(a,fixed,assets,data,a.evidence,'reopened') as origin:
                    assert pending(origin,fixture)['draftId']==d['draftId']
                print('W20 HTTP-only preflight PASS: actual HTTP + SQLite restart; browser NOT verified')
            else:
                version=subprocess.check_output([str(a.browser),'--version'],text=True,stderr=subprocess.STDOUT,env=env_for(work),timeout=10).strip()
                receipt['browserVersion']=version
                receipt['browserSandboxRequested']=True
                from playwright.sync_api import sync_playwright
                with sync_playwright() as pw:
                    browser=pw.chromium.launch(executable_path=str(a.browser),headless=True,chromium_sandbox=True,env=env_for(work),args=['--no-proxy-server'])
                    try:
                        with host(a,fixed,assets,data,a.evidence,'initial') as origin:
                            component(browser,origin,a.evidence)
                            case_setup(origin,fixture)
                            old_id = product(browser,origin,fixture,a.evidence)
                        with host(a,fixed,assets,data,a.evidence,'reopened') as origin:
                            product(browser,origin,fixture,a.evidence,expected_draft=old_id)
                    finally:
                        browser.close()
                receipt['trueBrowser']=True
                print('W20 actual sandboxed Chromium + exact app + loopback HTTP/SQLite PASS')
            receipt['result']='passed'
    except subprocess.CalledProcessError as e:
        if e.output: print(e.output.strip())
        raise
    finally:
        if a.evidence:
            (a.evidence/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':
    main()
