"""Real synthetic service browser; only delivery delay is intercepted."""
import os,signal,subprocess,tempfile,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent
with tempfile.TemporaryDirectory(prefix='w52b-browser-') as tmp:
 env={**os.environ,'MCIS_DATA_DIR':tmp+'/data','MCIS_API':'http://127.0.0.1:15962','PYTHONPATH':str(ROOT/'service')}
 back=subprocess.Popen([str(ROOT/'service/.venv/bin/python'),str(HERE/'server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 front=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15963','--strictPort'],cwd=ROOT/'web',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 try:
  for port,path in [(15962,'/api/v1/health'),(15963,'/')]:
   for _ in range(100):
    try:urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',timeout=1);break
    except Exception:time.sleep(.1)
   else:raise RuntimeError('local startup failed')
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.environ['MCIS_BROWSER_BIN'],headless=True,args=['--no-sandbox'],env={**os.environ,'HOME':tmp,'XDG_CONFIG_HOME':tmp+'/config'})
   page=browser.new_page();errors=[];held=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.add_init_script("localStorage.setItem('mcis.role','LeadInvestigator')")
   page.goto('http://127.0.0.1:15963/#/interview?case=SYN-W52B')
   panel=page.get_by_role('region',name='人工笔录录入');panel.wait_for()
   assert '整个 .mcase 案件包' in panel.inner_text()
   for label,value in [('受询问人标识（必填）','Synthetic-P'),('受询问人姓名（必填）','Synthetic Person'),('职务（必填）','Synthetic Witness'),('所属单位（必填）','Synthetic'),('真实开始时间 UTC（必填，秒Z）','2026-01-01T00:00:00Z')]:panel.get_by_label(label,exact=True).fill(value)
   assert panel.get_by_role('button',name='保存空白人工笔录',exact=True).is_disabled()
   panel.get_by_role('checkbox').check();panel.get_by_role('button',name='保存空白人工笔录',exact=True).click()
   panel.get_by_text('已核验此请求的保存回执',exact=True).wait_for()
   panel.get_by_role('button',name='重新打开服务器当前笔录',exact=True).click()
   panel.get_by_text('服务器当前原文 · IR-01',exact=True).wait_for()
   question='  Synthetic question 中文🚢\n';answer='  Synthetic answer 原文\n'
   panel.get_by_label('问题原文（必填）',exact=True).fill(question);panel.get_by_label('回答原文（必填）',exact=True).fill(answer)
   panel.get_by_role('checkbox').check()
   sent=[]
   def lose_response(route):
    response=route.fetch();assert response.status==201
    sent.append(route.request.post_data_json);route.abort('failed')
   page.route('**/manual-interviews/IR-01/turns',lose_response)
   panel.get_by_role('button',name='保存追加问答',exact=True).click()
   panel.get_by_text('存在结果未确认的',exact=False).wait_for()
   for _ in range(200):
    if sent:break
    page.wait_for_timeout(25)
   assert len(sent)==1
   panel.get_by_role('button',name='只读查询原请求回执',exact=True).wait_for()
   page.wait_for_function("!Array.from(document.querySelectorAll('button')).find(e=>e.textContent==='只读查询原请求回执').disabled")
   page.unroute('**/manual-interviews/IR-01/turns',lose_response)
   page.reload();panel.get_by_text('原请求正文已不在内存',exact=False).wait_for()
   assert panel.get_by_role('button',name='同ID原样重试',exact=True).is_disabled()
   panel.get_by_role('button',name='只读查询原请求回执',exact=True).click()
   panel.get_by_text('已核验此请求的保存回执',exact=True).wait_for()
   panel.get_by_role('button',name='重新打开服务器当前笔录',exact=True).click()
   panel.get_by_text('服务器当前原文 · IR-01',exact=True).wait_for()
   api='http://127.0.0.1:15962/api/v1/cases/SYN-W52B';headers={'X-MCIS-Role':'LeadInvestigator'}
   doc=page.request.get(api+'/interviews/IR-01',headers=headers).json()
   assert len(doc['turns'])==1 and doc['turns'][0]['question']==question and doc['turns'][0]['answer']==answer
   assert 'Synthetic question' in panel.inner_text() and 'Synthetic answer' in panel.inner_text()
   # Real old writer changes full-document version while the UI retains its snapshot.
   panel.get_by_label('问题原文（必填）',exact=True).fill('Synthetic pending question')
   panel.get_by_label('回答原文（必填）',exact=True).fill('Synthetic pending answer')
   assert page.request.post(api+'/interviews/IR-01/turns',headers=headers,data={'question':'Synthetic concurrent','answer':'Synthetic old writer'}).status==201
   panel.get_by_role('checkbox').check();panel.get_by_role('button',name='保存追加问答',exact=True).click()
   panel.get_by_text('INTERVIEW_VERSION_CONFLICT',exact=False).wait_for()
   assert panel.get_by_label('回答原文（必填）',exact=True).input_value()=='Synthetic pending answer'
   assert panel.get_by_role('button',name='保存追加问答',exact=True).is_disabled()
   out=page.request.get(api+'/export',headers=headers)
   assert out.status==409 and 'INTERVIEW_RECEIPTS_BACKUP_UNSUPPORTED' in out.text()
   assert len(page.request.get(api+'/interviews/IR-01',headers=headers).json()['turns'])==2
   page.reload();panel.get_by_text('服务器当前原文 · IR-01',exact=True).wait_for()
   assert 'Synthetic old writer' in panel.inner_text()
   assert not errors,errors
   browser.close();print('PASS: actual service create/ack, committed response loss, reload receipt recovery, exact original text, real stale-version conflict, export denial, reopening.')
 finally:
  for proc in [front,back]:
   try:os.killpg(proc.pid,signal.SIGTERM)
   except ProcessLookupError:pass
