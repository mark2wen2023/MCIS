"""Real HTTP + real Chromium, one supervised localhost process tree.
Uses existing Playwright installation/browser. No install or deployment.
"""
import base64,hashlib,json,os,subprocess,tempfile,time,urllib.request,sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[2]
LOG=ROOT/'logs'/('w42-independent-ui-'+os.environ.get('W42_RUN_LABEL','run'))
LOG.mkdir(exist_ok=True)
RAW=bytes(range(256))+b'\x00\xff<script>window.W42_XSS=1</script>'
H={'Content-Type':'application/json','X-MCIS-Role':'Investigator','X-MCIS-Operator':'Independent-Network'}
B={'profile':'mcis-evidence-intake-v1','fileName':'synthetic.bin','title':'<img src=x onerror="window.W42_XSS=1">','source':'Synthetic handover only','extractedBy':'Known extractor','extractedUtc':'2001-02-03T04:05:06Z','category':'Other','confidentiality':'Restricted','note':'original note','contentBase64':base64.b64encode(RAW).decode()}
results=[]
def check(name,fn):
    try:fn();results.append({'name':name,'result':'PASS'});print('PASS',name,flush=True)
    except Exception as e:
        results.append({'name':name,'result':'FAIL','error':repr(e)});print('FAIL',name,repr(e),flush=True);raise

def request(port,path,body=None,method=None,ctype=None):
    data=(json.dumps(body).encode() if isinstance(body,dict) else body) if body is not None else None
    req=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=data,headers={**H,**({'Content-Type':ctype} if ctype else {})},method=method)
    with urllib.request.urlopen(req,timeout=30) as r:return r.read(),dict(r.headers)
def jreq(port,path,body=None):return json.loads(request(port,path,body)[0])
def waitport(port):
    for _ in range(150):
        try:urllib.request.urlopen(f'http://127.0.0.1:{port}/',timeout=.3);return
        except urllib.error.HTTPError:return
        except OSError:time.sleep(.1)
    raise RuntimeError(f'Port {port} failed startup')
processes=[];handles=[]
def start(cmd,cwd,env,name):
    h=open(LOG/(name+'.log'),'w');handles.append(h)
    p=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=h,stderr=subprocess.STDOUT);processes.append(p);return p
with tempfile.TemporaryDirectory(prefix='w42-independent-') as tmp:
    tmp=Path(tmp)
    env={**os.environ,'PYTHONPATH':str(ROOT/'service'),'MCIS_DATA_DIR':str(tmp/'server-a'),'MCIS_PORT':'18842','MCIS_SEED_DEMO':'0'}
    try:
        start([str(ROOT/'service/.venv/bin/python'),str(ROOT/'tests_acceptance/W42/browser_server.py')],ROOT,env,'server-a');waitport(18842)
        start([str(ROOT/'service/.venv/bin/python'),str(ROOT/'tests_acceptance/W42/browser_server.py')],ROOT,{**env,'MCIS_DATA_DIR':str(tmp/'server-b'),'MCIS_PORT':'18843'},'server-b');waitport(18843)
        start(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15842','--strictPort'],ROOT/'web',{**os.environ,'MCIS_API':'http://127.0.0.1:18842'},'vite');waitport(15842)
        C='/api/v1/cases/W42-NETWORK'
        def network_lifecycle():
            p=jreq(18842,C+'/evidence-intakes:preview',B);assert p['sourceSha256']==hashlib.sha256(RAW).hexdigest()
            body={**B,'requestDigest':p['requestDigest'],'confirmed':True}
            with ThreadPoolExecutor(max_workers=4) as pool:receipts=list(pool.map(lambda _:jreq(18842,C+'/evidence-intakes:commit',body),range(4)))
            assert len({r['evidenceId'] for r in receipts})==1
            r=receipts[0];assert jreq(18842,C+'/evidence-intakes/'+r['requestDigest'])['evidenceId']==r['evidenceId']
            assert jreq(18842,C+'/evidence/'+r['evidenceId']+'/intake')['requestDigest']==r['requestDigest']
            assert request(18842,C+'/evidence-intakes/'+r['requestDigest']+':download',{'purpose':'network byte check'})[0]==RAW
            reqs=[]
            for i in range(4):
                b={**B,'note':'distinct-'+str(i)};p=jreq(18842,C+'/evidence-intakes:preview',b);reqs.append({**b,'requestDigest':p['requestDigest'],'confirmed':True})
            with ThreadPoolExecutor(max_workers=4) as pool:distinct=list(pool.map(lambda b:jreq(18842,C+'/evidence-intakes:commit',b),reqs))
            assert len({r['evidenceId'] for r in distinct})==4
            package=request(18842,C+'/export')[0]
            # Fresh target must not already contain source case.
            import sqlite3
            db=sqlite3.connect(tmp/'server-b/network.db');db.execute("DELETE FROM cases WHERE case_id='W42-NETWORK'");db.commit();db.close()
            imported=request(18843,'/api/v1/cases:import',package,ctype='application/zip')[0]
            old=jreq(18842,C+'/evidence/'+r['evidenceId']+'/custody');new=jreq(18843,C+'/evidence/'+r['evidenceId']+'/custody');assert old==new
            assert jreq(18843,C+'/evidence-intakes/'+r['requestDigest'])['metadata']==r['metadata']
            assert request(18843,C+'/evidence-intakes/'+r['requestDigest']+':download',{'purpose':'fresh network byte check'})[0]==RAW
        check('NETWORK lifecycle + same/different concurrent + fresh DB mcase',network_lifecycle)
        with sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path=os.environ['MCIS_BROWSER_BIN'],headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
            context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
            page=context.new_page();calls=[]
            page.on('request',lambda r:calls.append((r.method,r.url)))
            def open_form(cid='W42-UI-A'):
                page.goto(f'http://127.0.0.1:15842/#/evidence?case={cid}')
                page.get_by_role('button',name='＋ 登记已有文件副本 / 查看登记原件').click()
            def fill(title=None):
                page.locator('input[type=file]').set_input_files({'name':'synthetic.bin','mimeType':'application/octet-stream','buffer':RAW})
                expect(page.get_by_text('选文件仅在本地读取，点服务端预览才上传。')).to_be_visible()
                page.get_by_label('证据标题（必填）').fill(title or B['title'])
                page.get_by_label('原来源 / 取得或移交方式（必填）').fill(B['source'])
                page.get_by_label('提取人（必填，非当前登记人默认值）').fill(B['extractedBy'])
                page.get_by_placeholder('YYYY-MM-DDTHH:mm:ssZ').fill(B['extractedUtc'])
                page.get_by_label('登记备注（可留空，保留原文）').fill(B['note'])
            def preview_ui():
                page.get_by_role('button',name='服务端预览（不登记）',exact=True).click()
                expect(page.get_by_role('heading',name='2 · 核对服务预览')).to_be_visible()
            def confirm_ui():page.locator('.w42-confirm input').check()
            def close_ui():page.get_by_role('button',name='关闭（不撤销已发请求）').click()
            def ui_lifecycle():
                open_form();n=len([x for x in calls if ':preview' in x[1]]);fill()
                assert len([x for x in calls if ':preview' in x[1]])==n
                preview_ui();confirm_ui();page.get_by_label('登记备注（可留空，保留原文）').fill('changed original note')
                expect(page.get_by_role('heading',name='2 · 核对服务预览')).to_have_count(0)
                preview_ui();expect(page.locator('.w42-confirm input')).not_to_be_checked();confirm_ui()
                page.get_by_role('button',name='确认登记文件副本',exact=True).evaluate('(b)=>{b.click();b.click()}')
                expect(page.get_by_role('heading',name='已核对登记回执',exact=False)).to_be_visible()
                assert len([x for x in calls if ':commit' in x[1]])==1
                assert page.evaluate('window.W42_XSS') is None
                page.get_by_label('本次下载目的（将记入访问记录）').fill('Browser independent check')
                with page.expect_download() as d:page.get_by_role('button',name='记录访问并下载原件').click()
                artifact=d.value;assert Path(artifact.path()).read_bytes()==RAW and artifact.suggested_filename=='synthetic.bin'
                page.screenshot(path=str(LOG/'1440-receipt.png'),full_page=True)
                close_ui();page.get_by_role('button',name='＋ 登记已有文件副本 / 查看登记原件').click()
                page.get_by_role('button',name='读取当前证据登记回执（只读）').click();expect(page.locator('.w42-receipt')).to_be_visible()
                page.set_viewport_size({'width':1920,'height':1080});page.screenshot(path=str(LOG/'1920-receipt.png'),full_page=True)
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                close_ui();page.get_by_role('button',name='＋ 登记已有文件副本 / 查看登记原件').focus();page.keyboard.press('Enter');expect(page.locator('.w42-panel')).to_be_visible()
            check('BROWSER local selection/invalidation/doubleclick/XSS/reopen/download/1440+1920/keyboard',ui_lifecycle)
            def unknown_response():
                close_ui();open_form();fill('Unknown response synthetic');preview_ui();confirm_ui()
                def lose(route):route.fetch();route.abort('failed')
                page.route('**/evidence-intakes:commit',lose)
                page.get_by_role('button',name='确认登记文件副本',exact=True).click()
                expect(page.get_by_role('button',name='只读核查本次登记',exact=True)).to_be_visible()
                expect(page.get_by_label('证据标题（必填）')).to_be_disabled()
                before=len([x for x in calls if ':commit' in x[1]])
                page.get_by_role('button',name='只读核查本次登记',exact=True).click();expect(page.locator('.w42-receipt')).to_be_visible()
                assert len([x for x in calls if ':commit' in x[1]])==before
                page.unroute('**/evidence-intakes:commit',lose)
            check('BROWSER lost write response recovered read-only',unknown_response)
            def delayed_preview_isolation():
                for mode in ('case','role','close','back'):
                    if page.locator('.w42-panel').count():close_ui()
                    open_form();fill('Delayed preview '+mode)
                    pending={}
                    def hold(route):pending['response']=route.fetch();pending['route']=route
                    page.route('**/evidence-intakes:preview',hold)
                    page.get_by_role('button',name='服务端预览（不登记）',exact=True).click()
                    for _ in range(50):
                        if 'route' in pending:break
                        page.wait_for_timeout(20)
                    assert 'route' in pending
                    if mode=='role':page.locator('select.role-select').select_option('Public')
                    elif mode=='case':page.evaluate("location.hash='/evidence?case=W42-UI-B'")
                    elif mode=='back':
                        page.evaluate("location.hash='/evidence?case=W42-UI-B'");page.wait_for_timeout(100);page.go_back()
                    else:close_ui();page.get_by_role('button',name='＋ 登记已有文件副本 / 查看登记原件').click()
                    try:pending['route'].fulfill(response=pending['response'])
                    except Exception:pass # Browser cancellation is an acceptable isolation path.
                    page.wait_for_timeout(150)
                    assert page.locator('.w42-preview').count()==0
                    page.unroute('**/evidence-intakes:preview',hold)
                    if mode=='role':page.locator('select.role-select').select_option('Investigator')
            check('BROWSER delayed preview case/role/reopen/Back isolation',delayed_preview_isolation)
            def inflight_leave():
                if page.locator('.w42-panel').count():close_ui()
                open_form();fill('In-flight leave retained');preview_ui();confirm_ui()
                def delay(route):route.continue_(headers={**route.request.headers,'X-W42-Delay':'yes'})
                page.route('**/evidence-intakes:commit',delay)
                page.get_by_role('button',name='确认登记文件副本',exact=True).click()
                close_ui();page.get_by_role('button',name='＋ 登记已有文件副本 / 查看登记原件').click()
                page.wait_for_timeout(1500)
                assert page.locator('.w42-receipt').count()==0
                rows=jreq(18842,'/api/v1/cases/W42-UI-A/evidence')
                assert sum(x['title']=='In-flight leave retained' for x in rows)==1
                page.unroute('**/evidence-intakes:commit',delay)
            check('BROWSER in-flight write survives close and cannot populate reopened session',inflight_leave)
            def delayed_evidence_selection():
                if page.locator('.w42-panel').count():close_ui()
                open_form();pending={}
                def hold_receipt(route):pending['response']=route.fetch();pending['route']=route
                page.route('**/evidence/*/intake',hold_receipt)
                page.get_by_role('button',name='读取当前证据登记回执（只读）').click()
                for _ in range(50):
                    if 'route' in pending:break
                    page.wait_for_timeout(20)
                assert 'route' in pending
                page.locator('.w42-evidence-select').last.click()
                expect(page.locator('.w42-panel')).to_have_count(0)
                page.get_by_role('button',name='＋ 登记已有文件副本 / 查看登记原件').click()
                try:pending['route'].fulfill(response=pending['response'])
                except Exception:pass
                page.wait_for_timeout(150);assert page.locator('.w42-receipt').count()==0
                page.unroute('**/evidence/*/intake',hold_receipt)
            check('BROWSER delayed receipt cannot cross evidence selection',delayed_evidence_selection)
            def browser_budget():
                if page.locator('.w42-panel').count():close_ui()
                open_form('W42-UI-B');fill('Eight MiB browser boundary')
                page.locator('input[type=file]').set_input_files({'name':'too-large.bin','mimeType':'application/octet-stream','buffer':b'x'*(8*1024*1024+1)})
                expect(page.get_by_role('alert')).to_contain_text('8 MiB')
                expect(page.get_by_role('button',name='服务端预览（不登记）',exact=True)).to_be_disabled()
                big=b'x'*(8*1024*1024)
                page.locator('input[type=file]').set_input_files({'name':'eight.bin','mimeType':'application/octet-stream','buffer':big})
                expect(page.get_by_text('选文件仅在本地读取，点服务端预览才上传。')).to_be_visible()
                preview_ui();confirm_ui();page.get_by_role('button',name='确认登记文件副本',exact=True).click()
                expect(page.locator('.w42-receipt')).to_be_visible(timeout=30000)
                page.get_by_label('本次下载目的（将记入访问记录）').fill('8MiB browser download')
                with page.expect_download() as d:page.get_by_role('button',name='记录访问并下载原件').click()
                assert Path(d.value.path()).read_bytes()==big
                page.locator('main').evaluate('(e)=>e.scrollTop=0')
                page.screenshot(path=str(LOG/'1920-panel-top.png'),full_page=True)
                page.set_viewport_size({'width':1440,'height':1000});page.locator('main').evaluate('(e)=>e.scrollTop=0')
                page.screenshot(path=str(LOG/'1440-panel-top.png'),full_page=True)
            check('BROWSER 8MiB upload/save/download and reject +1 byte',browser_budget)
            browser.close()
    finally:
        (LOG/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
        for p in reversed(processes):p.terminate()
        for p in reversed(processes):
            try:p.wait(timeout=10)
            except subprocess.TimeoutExpired:p.kill();p.wait()
        for h in handles:h.close()
