"""Real owned service/renderers; fault cases explicitly replace only response transport."""
import os,socket,subprocess,tempfile,time,json,urllib.request,io,zipfile,hashlib,base64
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent
CASE='SYN-INDEPENDENT-OUTPUT'
with tempfile.TemporaryDirectory(prefix='report-output-browser-') as tmp:
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(128)
    apiport=listener.getsockname()[1]
    reserve=socket.socket();reserve.bind(('127.0.0.1',0));webport=reserve.getsockname()[1];reserve.close()
    env={**os.environ,'PYTHONPATH':str(ROOT/'service'),'OUTPUT_ACCEPTANCE_DATA':tmp,'OUTPUT_ACCEPTANCE_FD':str(listener.fileno()),'MCIS_API':f'http://127.0.0.1:{apiport}'}
    processes=[]
    try:
        processes.append(subprocess.Popen([str(ROOT/'service/.venv/bin/python'),str(HERE/'server.py')],env=env,pass_fds=(listener.fileno(),),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
        listener.close()
        processes.append(subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',str(webport),'--strictPort'],cwd=ROOT/'web',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
        for port,path in [(apiport,'/api/v1/health'),(webport,'/')]:
            for _ in range(200):
                assert all(p.poll() is None for p in processes),'owned service exited'
                try:urllib.request.urlopen(f'http://127.0.0.1:{port}'+path,timeout=1);break
                except Exception:time.sleep(.1)
            else:raise RuntimeError('owned service not ready')
        report=json.loads((Path(tmp)/'synthetic-report.json').read_text())
        with sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path=os.environ['MCIS_BROWSER_BIN'],headless=True,args=['--no-sandbox'])
            page=browser.new_page();page.set_default_timeout(15000);posts=[];downloads=[]
            page.add_init_script("localStorage.setItem('mcis.role','LeadInvestigator');localStorage.setItem('mcis.operator','Independent Synthetic Output')")
            page.on('request',lambda r:posts.append(r) if r.method=='POST' and r.url.endswith('/output-bundle') else None)
            page.on('download',lambda d:downloads.append(d))
            page.on('console',lambda m:print('BROWSER-CONSOLE',m.text) if m.type=='error' else None)
            url=f'http://127.0.0.1:{webport}/#/report?case={CASE}&report='+report['reportId']
            def inspect(fmt):
                page.get_by_label('单一文件格式').select_option(fmt)
                page.get_by_label('本次渲染语言').select_option('en')
                page.get_by_role('button',name='读取当前已保存快照（不生成）',exact=True).click()
                page.get_by_label('我已核对已保存快照',exact=False).check()
            for fmt in ['pdf','docx']:
                page.goto(url);page.reload();inspect(fmt)
                try:
                    with page.expect_download() as captured:
                        page.get_by_role('button',name='生成可追溯下载包（仅一次）',exact=True).click()
                except Exception:
                    print('FAILED-DOWNLOAD-DOM',page.locator('body').inner_text());raise
                raw=Path(captured.value.path()).read_bytes()
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    assert z.namelist()==['report.'+fmt,'report.json','audit.json','manifest.json']
                    assert json.loads(z.read('report.json'))==report
                    for member in json.loads(z.read('manifest.json'))['members']:
                        data=z.read(member['name']);assert len(data)==member['byteLength'] and hashlib.sha256(data).hexdigest()==member['sha256']
                if fmt=='pdf':
                    context={'who':json.dumps(['LeadInvestigator','Independent Synthetic Output'],separators=(',',':')),'format':fmt,'lang':'en','preview':{'caseId':CASE,'reportId':report['reportId'],'reportDocumentSha256':hashlib.sha256(json.dumps(report,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'reportVersion':report['version'],'reportStatus':report['status'],'storedLanguage':report['lang'],'canonicalization':'MCIS-PY-JSON-1'}}
                    def validate(data,ctx):
                        return page.evaluate("""async ({b,a})=>{const m=await import('/src/reportOutput/model.ts');try{await m.validateBundle(Uint8Array.from(atob(b),x=>x.charCodeAt(0)),a,()=>true);return true}catch{return false}}""",{'b':base64.b64encode(data).decode(),'a':ctx})
                    assert validate(raw,context)
                    for offset in [0,6,14,len(raw)-6]:
                        bad=bytearray(raw);bad[offset]^=1;assert not validate(bytes(bad),context)
                    assert not validate(raw+b'X',context)
                    assert not validate(raw,{**context,'lang':'zh'})
                    assert not validate(raw,{**context,'who':'["LeadInvestigator","Wrong"]'})
                    assert not validate(raw,{**context,'preview':{**context['preview'],'reportDocumentSha256':'f'*64}})
                page.get_by_text('请自行确认完整文件落盘',exact=False).wait_for()
            # Real POST commits; only delivery is replaced with503 or invalid ZIP.
            for fault in ['lost','badzip']:
                page.goto(url);page.reload();inspect('pdf');prior=len(posts);prior_downloads=len(downloads)
                def intercept(route):
                    actual=route.fetch();assert actual.status==200
                    if fault=='lost':route.fulfill(status=503,json={'code':'SYNTHETIC_DELIVERY_FAILURE'})
                    else:route.fulfill(response=actual,body=b'not-a-zip')
                page.route('**/output-bundle',intercept)
                page.get_by_role('button',name='生成可追溯下载包（仅一次）',exact=True).click()
                page.get_by_role('heading',name='当次交付结果待核验',exact=True).wait_for()
                page.reload();page.get_by_role('heading',name='当次交付结果待核验',exact=True).wait_for()
                assert len(posts)==prior+1 and len(downloads)==prior_downloads
                page.get_by_label('我已检查本地下载',exact=False).check()
                page.get_by_role('button',name='放弃此投递并重新预览（不是恢复原文件）',exact=True).click()
                page.unroute('**/output-bundle',intercept)
            # Actual generation is committed; hold its response until identity changes.
            page.goto(url);page.reload();inspect('docx');held=[];prior_downloads=len(downloads)
            def delayed(route):
                response=route.fetch();assert response.status==200;held.append((route,response))
            page.route('**/output-bundle',delayed)
            page.get_by_role('button',name='生成可追溯下载包（仅一次）',exact=True).click()
            for _ in range(100):
                if held:break
                page.wait_for_timeout(50)
            assert held,'actual POST did not finish'
            page.locator('select[title="X-MCIS-Role"]').select_option('Investigator')
            route,response=held.pop();route.fulfill(response=response)
            page.get_by_text('当前身份无权访问完整报告内容',exact=False).first.wait_for()
            assert len(downloads)==prior_downloads
            browser.close()
        # Both failed-delivery probes and late discarded response really committed.
        import sqlite3
        database=next(Path(tmp).glob('*.db'))
        with sqlite3.connect(database) as connection:
            count=connection.execute("SELECT count(*) FROM audit_events WHERE action='report.export'").fetchone()[0]
            assert count==5,count
        print('PASS real PDF/DOCX service downloads; two actual commits with explicitly replaced503/malformed delivery stay unknown/no retry; actual delayed identity response discarded; exactly five export audits')
    finally:
        listener.close()
        for proc in processes:
            if proc.poll() is None:proc.terminate()
        for proc in processes:
            try:proc.wait(timeout=10)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
