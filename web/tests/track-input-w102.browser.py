"""Real service/browser implementation smoke. No page.route or mocked HTTP."""
import os,sys,time,tempfile,json,subprocess,signal,urllib.request,traceback
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'logs/w102-browser-self';OUT.mkdir(parents=True,exist_ok=True)
PORT=15820;API=18820;procs=[];checks=[]
env=dict(os.environ,MCIS_DATA_DIR=tempfile.mkdtemp(prefix='w102-self-'),MCIS_API=f'http://127.0.0.1:{API}',MCIS_AGENT_BASE_URL='',MCIS_AGENT_MODEL='',PYTHONPATH=str(ROOT/'service')+os.pathsep+str(ROOT/'web/tests'))
def start(cmd,cwd,name):
 p=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=open(OUT/name,'w'),stderr=subprocess.STDOUT,start_new_session=True);procs.append(p)
def wait(url):
 for _ in range(100):
  try:urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url,timeout=1);return
  except Exception:time.sleep(.1)
 raise RuntimeError('server unavailable')
def ck(v,name):
 checks.append({'name':name,'passed':bool(v)});assert v,name
try:
 start([str(ROOT/'service/.venv/bin/python'),'-m','uvicorn','w102_qa_app:app','--host','127.0.0.1','--port',str(API)],ROOT,'service.log');wait(f'http://127.0.0.1:{API}/api/v1/health')
 start(['npm','run','dev','--','--port',str(PORT)],ROOT/'web','vite.log');wait(f'http://127.0.0.1:{PORT}')
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ['MCIS_BROWSER_BIN'],headless=True,args=['--no-sandbox'])
  page=browser.new_page(viewport={'width':1440,'height':900},accept_downloads=True);errors=[];page.on('pageerror',lambda e:errors.append(str(e)));requests=[];page.on('request',lambda r:requests.append((r.method,r.url)))
  page.goto(f'http://127.0.0.1:{PORT}/#/track?case=QA-W102-A');page.get_by_role('button',name='＋ 导入明确语义 UTC CSV / 查看导入原件',exact=True).click()
  page.get_by_label('目标船舶').select_option('V1');page.get_by_label('资料来源说明（必填）').fill('synthetic input <img src=x onerror=alert(1)>');page.get_by_label('UTC 时间依据说明（必填）').fill('Synthetic complete UTC generated for tests, not AIS')
  content=b'\xef\xbb\xbfutc,latDeg,lonDeg,sogKn,sogStatus,cogDeg,cogStatus,hdgDeg,hdgStatus\r\n2025-12-31T23:59:59Z,30,121,102.2,reported,90,reported,511,unavailable\r\n2026-01-01T00:00:00.123Z,30.1,121.1,0,reported,0,reported,,unavailable\r\n'
  before=len([r for r in requests if r[0]=='POST']);page.get_by_label('CSV 原件',exact=False).set_input_files({'name':'raw.csv','mimeType':'text/csv','buffer':content});page.get_by_text('SHA-256：',exact=False).first.wait_for();ck(len([r for r in requests if r[0]=='POST'])==before,'file selection no upload')
  page.get_by_role('button',name='服务端预览（不保存）',exact=True).click();page.get_by_role('heading',name='2 · 核对预览与来源声明').wait_for();ck('102.2' in page.locator('.w102-table').inner_text(),'reported102.2 preserved');ck('不可用 / 未提供' in page.locator('.w102-table').inner_text(),'hdg unavailable not cog')
  ck(page.locator('.w102-panel img').count()==0,'escaped source statement');ck(page.get_by_role('button',name='确认保存本次航迹').is_disabled(),'manual confirm required')
  page.get_by_label('我已核对目标案件',exact=False).check();page.get_by_role('button',name='确认保存本次航迹',exact=True).click();page.get_by_role('heading',name='已核对保存回执').wait_for();ck('2 点' in page.locator('.w102-receipt').inner_text(),'real commit receipt')
  with page.expect_download() as dl:page.get_by_role('button',name='下载已保存 CSV 原件').click()
  ck(Path(dl.value.path()).read_bytes()==content,'source exact bytes BOM CRLF sentinel retained')
  with page.expect_download() as dl:page.get_by_role('button',name='下载导入说明 JSON').click()
  report=json.loads(Path(dl.value.path()).read_bytes());ck(report['metadata']['timeBasis'].startswith('Synthetic'),'timeBasis report preserved')
  page.get_by_role('button',name='读取已保存航迹',exact=True).click();page.get_by_text('第 1 / 1 页 · 2 点 · 每页 100 点',exact=True).wait_for();ck('102.2' in page.locator('.w10-table-scroll').inner_text(),'saved points real GET')
  page.reload();page.get_by_role('button',name='＋ 导入明确语义 UTC CSV / 查看导入原件',exact=True).click();page.get_by_label('目标船舶').select_option('V1');page.get_by_role('button',name='读取本船导入回执（只读）').click();page.get_by_role('heading',name='已核对保存回执').wait_for();ck('2 点' in page.locator('.w102-receipt').inner_text(),'reopen receipt no duplicate commit')
  for w,h in [(1440,900),(1920,1080)]:
   page.set_viewport_size({'width':w,'height':h});ck(page.evaluate('document.documentElement.scrollWidth <= innerWidth'),f'{w} no outer overflow');page.screenshot(path=str(OUT/f'{w}.png'),full_page=True)
  ck(not errors,'no JS errors');browser.close()
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
print(f'{len(checks)} real-browser implementation checks passed')
