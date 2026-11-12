"""Actual backend + Chromium implementation smoke, no successful API mocks."""
import os,time,tempfile,json,subprocess,signal,urllib.request,traceback,importlib.util
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'logs/w42-browser-self';OUT.mkdir(parents=True,exist_ok=True)
PORT=15840;API=18840;procs=[];checks=[]
env=dict(os.environ,MCIS_DATA_DIR=tempfile.mkdtemp(prefix='w42-self-'),MCIS_API=f'http://127.0.0.1:{API}',MCIS_AGENT_BASE_URL='',MCIS_AGENT_MODEL='',PYTHONPATH=str(ROOT/'service'))
def start(cmd,cwd,name):
 p=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=open(OUT/name,'w'),stderr=subprocess.STDOUT,start_new_session=True);procs.append(p)
def wait(url):
 for _ in range(100):
  try:urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url,timeout=1);return
  except Exception:time.sleep(.1)
 raise RuntimeError('server unavailable')
def get(path):
 return json.load(urllib.request.build_opener(urllib.request.ProxyHandler({})).open(f'http://127.0.0.1:{API}/api/v1/cases/'+path))
def ck(v,name):checks.append({'name':name,'passed':bool(v)});assert v,name
try:
 fixture=ROOT/'web/tests/evidence-intake-w42.fixture.py'
 code=f"import importlib.util,uvicorn;s=importlib.util.spec_from_file_location('w42fixture',{str(fixture)!r});m=importlib.util.module_from_spec(s);s.loader.exec_module(m);uvicorn.run(m.app,host='127.0.0.1',port={API})"
 start([str(ROOT/'service/.venv/bin/python'),'-c',code],ROOT,'service.log');wait(f'http://127.0.0.1:{API}/api/v1/health')
 start(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',str(PORT),'--strictPort'],ROOT/'web','vite.log');wait(f'http://127.0.0.1:{PORT}')
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ['MCIS_BROWSER_BIN'],headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True);errors=[];page.on('pageerror',lambda e:errors.append(str(e)));requests=[];page.on('request',lambda r:requests.append((r.method,r.url)))
  def fill():
   page.get_by_label('证据标题（必填）',exact=True).fill('合成副本 <img src=x onerror=alert(1)>')
   page.get_by_label('原来源 / 取得或移交方式（必填）',exact=True).fill('  Synthetic handoff\n line2  ')
   page.get_by_label('提取人（必填，非当前登记人默认值）',exact=True).fill('  Synthetic extractor  ')
   page.get_by_label('提取时间 UTC（整秒，必填）',exact=True).fill('2020-02-29T12:34:56Z')
   page.get_by_label('登记备注（可留空，保留原文）',exact=False).fill(' original note\n  keep spacing  ')
  page.goto(f'http://127.0.0.1:{PORT}/#/evidence?case=QA-W42-A');page.get_by_role('button',name='＋ 登记已有文件副本 / 查看登记原件',exact=True).click()
  ck(page.get_by_label('提取时间 UTC（整秒，必填）',exact=True).input_value()=='' and page.get_by_label('提取人（必填，非当前登记人默认值）',exact=True).input_value()=='','no fabricated extraction metadata')
  fill();raw=b'\x00\xff\xef\xbb\xbfSynthetic\r\noriginal\x00';before=len(requests)
  page.get_by_label('原件文件（最多 8 MiB，可为零字节）',exact=True).set_input_files({'name':'synthetic.bin','mimeType':'application/octet-stream','buffer':raw});page.get_by_text('本地文件：synthetic.bin',exact=False).wait_for()
  ck(not any(m=='POST' for m,u in requests[before:]),'local selection no upload')
  page.get_by_role('button',name='服务端预览（不登记）',exact=True).click();page.get_by_role('heading',name='2 · 核对服务预览',exact=True).wait_for();ck(get('QA-W42-A/evidence')==[],'preview no evidence write');ck(get('QA-W42-A/custody:verify-chain')['count']==0,'preview no custody writes')
  ck(page.get_by_role('button',name='确认登记文件副本',exact=True).is_disabled(),'manual restricted confirmation required');ck(page.locator('.w42-panel img').count()==0,'metadata escaped')
  page.get_by_label('我已核对目标案件',exact=False).check();page.get_by_label('登记备注（可留空，保留原文）',exact=False).fill(' changed original note ');ck(page.get_by_role('heading',name='2 · 核对服务预览',exact=True).count()==0,'edit invalidates preview and confirmation')
  page.get_by_role('button',name='服务端预览（不登记）',exact=True).click();page.get_by_label('我已核对目标案件',exact=False).check();before=len(requests);page.get_by_role('button',name='确认登记文件副本',exact=True).dblclick();page.get_by_role('heading',name='已核对登记回执 · EV-001',exact=True).wait_for()
  ck(sum(m=='POST' and u.endswith('evidence-intakes:commit') for m,u in requests[before:])==1,'double click one commit')
  ev=get('QA-W42-A/evidence');ck(len(ev)==1 and ev[0]['status']=='Unverified' and ev[0]['extractedUtc']=='2020-02-29T12:34:56Z','actual saved metadata and unverified status');ck('系统登记 UTC' in page.locator('.w42-receipt').inner_text(),'registration separately labelled')
  page.get_by_label('本次下载目的（将记入访问记录）',exact=True).fill('  synthetic review copy  ')
  with page.expect_download() as dl:page.get_by_role('button',name='记录访问并下载原件',exact=True).click()
  ck(Path(dl.value.path()).read_bytes()==raw and dl.value.suggested_filename=='synthetic.bin','download raw bytes exact and original name')
  events=get('QA-W42-A/evidence/EV-001/custody');ck(len(events)==2 and events[-1]['kind']=='Access' and events[-1]['detail']=='  synthetic review copy  ','download purpose retained in actual custody')
  page.get_by_role('button',name='关闭（不撤销已发请求）',exact=True).click();page.get_by_role('button',name='＋ 登记已有文件副本 / 查看登记原件',exact=True).click();page.get_by_role('button',name='读取当前证据登记回执（只读）',exact=True).click();page.get_by_role('heading',name='已核对登记回执 · EV-001',exact=True).wait_for();ck(len(get('QA-W42-A/evidence/EV-001/custody'))==2,'reopen receipt read does not append access')
  for w,h in [(1440,1000),(1920,1080)]:
   page.set_viewport_size({'width':w,'height':h});ck(page.evaluate('document.documentElement.scrollWidth <= innerWidth'),f'{w} no document overflow');page.screenshot(path=str(OUT/f'{w}.png'),full_page=True)
  page.goto(f'http://127.0.0.1:{PORT}/#/evidence?case=QA-W42-B');page.get_by_role('button',name='＋ 登记已有文件副本 / 查看登记原件',exact=True).click();fill();page.get_by_label('原件文件（最多 8 MiB，可为零字节）',exact=True).set_input_files({'name':'zero.bin','mimeType':'application/octet-stream','buffer':b''});page.get_by_text('本地文件：zero.bin',exact=False).wait_for();page.get_by_role('button',name='服务端预览（不登记）',exact=True).click();page.get_by_label('我已核对目标案件',exact=False).check();page.get_by_role('button',name='确认登记文件副本',exact=True).click();page.get_by_role('heading',name='已核对登记回执 · EV-001',exact=True).wait_for();ck('0 bytes' in page.locator('.w42-receipt').inner_text(),'zero byte file actual registration')
  page.goto(f'http://127.0.0.1:{PORT}/#/evidence?case=QA-W42-C');page.get_by_role('button',name='＋ 登记已有文件副本 / 查看登记原件',exact=True).click();fill()
  page.get_by_label('原件文件（最多 8 MiB，可为零字节）',exact=True).set_input_files({'name':'delayed.bin','mimeType':'application/octet-stream','buffer':raw});page.get_by_text('本地文件：delayed.bin',exact=False).wait_for();page.get_by_role('button',name='服务端预览（不登记）',exact=True).click();page.get_by_label('我已核对目标案件',exact=False).check()
  with page.expect_request(lambda r:r.method=='POST' and r.url.endswith('/evidence-intakes:commit')):page.get_by_role('button',name='确认登记文件副本',exact=True).click()
  page.get_by_role('button',name='关闭（不撤销已发请求）',exact=True).click();page.get_by_role('button',name='＋ 登记已有文件副本 / 查看登记原件',exact=True).click()
  stored=[]
  for _ in range(100):
   stored=get('QA-W42-C/evidence')
   if stored:break
   time.sleep(.05)
  ck(len(stored)==1,'D01 dispatched commit survives close before server body read')
  page.wait_for_timeout(300);ck(page.locator('.w42-receipt').count()==0 and page.get_by_label('证据标题（必填）',exact=True).input_value()=='','D01 late commit cannot populate reopened form')
  ck(len(get('QA-W42-C/evidence/EV-001/custody'))==1,'D01 no automatic resend or duplicate register')
  ck(not errors,'no JS runtime errors');browser.close()
except Exception:
 (OUT/'error.txt').write_text(traceback.format_exc())
 try:(OUT/'page.txt').write_text(page.locator('body').inner_text());page.screenshot(path=str(OUT/'failure.png'),full_page=True)
 except Exception:pass
 raise
finally:
 (OUT/'results.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
 for p in procs:
  try:os.killpg(p.pid,signal.SIGTERM)
  except ProcessLookupError:pass
print(f'{len(checks)} actual-backend Chromium implementation checks passed')
