"""MCIS local Linux browser smoke harness, archived from the 2026-11-12 UTC+8 run.

Not a turnkey cross-platform installer. Requires Linux process groups, Python with
Playwright, the service environment installed, web/node_modules (npm ci), Node/npx,
a working .NET runtime and prebuilt real mcis-core DLL. Install browsers from
an official source yourself; this script does not download or alter dependencies.

Example, from repository root (replace browser/dotnet paths with your installation):
  MCIS_BROWSER_EXECUTABLE=<official-headless-shell> MCIS_DOTNET=<dotnet> \
    python tools/provenance/browser_smoke.py
Optional: MCIS_SERVICE_PYTHON, MCIS_CORE_DLL, MCIS_BROWSER_OUT. Use a NEW output
folder per run; screenshots with identical names would otherwise be replaced.
Default output and disposable database are in fresh temporary directories.
Services bind only 127.0.0.1. Existing project headless launch flags are retained;
run only in an approved isolated local test environment. No production writes.
"""
from pathlib import Path
import os, socket, subprocess, time, urllib.request, tempfile, signal, json, traceback, shutil
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(os.environ.get('MCIS_BROWSER_OUT', tempfile.mkdtemp(prefix='mcis-browser-artifacts-'))).resolve()
OUT.mkdir(parents=True,exist_ok=True)
BINARY=os.environ.get('MCIS_BROWSER_EXECUTABLE')
if not BINARY or not Path(BINARY).is_file():
 raise SystemExit('Set MCIS_BROWSER_EXECUTABLE to an installed official Chrome Headless Shell executable')
DOTNET=os.environ.get('MCIS_DOTNET') or shutil.which('dotnet')
if not DOTNET: raise SystemExit('Set MCIS_DOTNET or install dotnet on PATH')
SERVICE_PYTHON=os.environ.get('MCIS_SERVICE_PYTHON', str(ROOT/'service/.venv/bin/python'))
CORE_DLL=os.environ.get('MCIS_CORE_DLL', str(ROOT/'tools/mcis-core/out/mcis-core.dll'))
if not Path(SERVICE_PYTHON).is_file() or not Path(CORE_DLL).is_file():
 raise SystemExit('Service venv Python and prebuilt real MCIS core DLL are required')
YANGZE='CJK-2024-1230-YangZe22-VegaDream'; HAILI='CASE-2025-HAILI5-WANA17'
def port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def wait(url):
 for _ in range(150):
  try:
   with urllib.request.urlopen(url,timeout=2):return
  except Exception:time.sleep(.2)
 raise RuntimeError('server not ready '+url)
procs=[];logs=[];checks=[];errors=[];warns=[];network=[];writes=[]
tmp=Path(tempfile.mkdtemp(prefix='mcis-browser-qa-')); bp,fp=port(),port()
env=dict(os.environ, MCIS_DATA_DIR=str(tmp/'data'),MCIS_PORT=str(bp),MCIS_API=f'http://127.0.0.1:{bp}',MCIS_DOTNET=DOTNET,MCIS_CORE_DLL=CORE_DLL,MCIS_CORE=str(ROOT/'tests_acceptance/W6/mcis-core-norebuild.sh'))
base=f'http://127.0.0.1:{fp}'
def start(cmd,cwd,name):
 f=open(OUT/name,'w');logs.append(f)
 p=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);procs.append(p)
try:
 start([SERVICE_PYTHON,'-m','mcis_service'],ROOT/'service','backend.log')
 wait(f'http://127.0.0.1:{bp}/api/v1/health')
 subprocess.run(['npx','vite','build','--outDir',str(tmp/'dist'),'--emptyOutDir','--logLevel','error'],cwd=ROOT/'web',env=env,check=True,capture_output=True)
 start(['npx','vite','preview','--outDir',str(tmp/'dist'),'--host','127.0.0.1','--port',str(fp),'--strictPort'],ROOT/'web','frontend.log')
 wait(base)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=BINARY,headless=True,args=['--no-sandbox','--disable-gpu'])
  page=browser.new_page(viewport={'width':1440,'height':900},device_scale_factor=1)
  page.on('request',lambda r:writes.append({'method':r.method,'url':r.url}) if r.method in ['POST','PATCH','PUT','DELETE'] else None)
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda m: (errors if m.type=='error' else warns).append(m.text) if m.type in ['error','warning'] else None)
  page.on('response',lambda r:network.append({'url':r.url,'status':r.status}) if r.status>=400 else None)
  def check(name, value):
   checks.append({'name':name,'passed':bool(value)})
   if not value:
    (OUT/'failure-body.txt').write_text(page.locator('body').inner_text())
    page.screenshot(path=str(OUT/'failure.png'),full_page=True)
    raise AssertionError(name)
  def shots(name):
   for w,h in [(1440,900),(1920,1080)]:
    page.set_viewport_size({'width':w,'height':h})
    page.keyboard.press('Control+Home')
    page.screenshot(path=str(OUT/f'{name}-{w}.png'),full_page=False)
    sw=page.evaluate('document.documentElement.scrollWidth')
    checks.append({'name':f'{name}-{w}-layout','viewport':w,'scrollWidth':sw,'passed':sw==w})
    if sw!=w: raise AssertionError('document horizontal overflow')
   page.set_viewport_size({'width':1440,'height':900})
  page.goto(base+'/#/report?case='+YANGZE+'&template=cn-msa')
  page.get_by_test_id('report-page').wait_for()
  create=page.get_by_role('button',name='📄 生成双语报告',exact=True)
  create.wait_for(state='visible');create.click()
  page.get_by_test_id('report-sections').get_by_role('button').nth(16).wait_for()
  page.wait_for_url('**/*report=RPT-*')
  page.wait_for_function("!Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('生成双语报告')).disabled")
  check('YANGZE Chinese template 17 sections',page.get_by_test_id('report-sections').get_by_role('button').count()==17)
  page.get_by_test_id('report-sections').get_by_role('button',name='十四、事故责任认定',exact=False).click()
  page.wait_for_function("document.querySelector('.rpt-selected-heading').textContent.includes('十四、事故责任认定')")
  page.get_by_text('原公开报告记载',exact=False).first.wait_for()
  text=page.locator('body').inner_text()
  check('bounded excerpt/no new liability disclaimer','非完整章节' in text and '不代表系统重新作出责任认定' in text)
  page.get_by_text('章节来源与引用表',exact=False).click()
  check('precise source visible','report.txt#L1026-L1033' in page.locator('body').inner_text())
  page.wait_for_function("document.querySelector('.watermark')?.textContent.includes('真实案例')")
  check('authorized public global label consistent','真实案例（公开报告）' in page.locator('.watermark').inner_text() and '示例数据（虚构）' not in page.locator('body').inner_text())
  shots('report-yangze-liability')
  page.screenshot(path=str(OUT/'report-yangze-full.png'),full_page=True)
  report_url=page.url
  evlink=page.locator('a[href*="/evidence"][href*="EV-201"]').first
  evlink.click()
  page.get_by_role('button',name='校验哈希',exact=True).wait_for()
  check('report EV-201 link preserves YANGZE',YANGZE in page.url and 'EV-201' in page.url and '示例数据（虚构）' not in page.locator('body').inner_text())
  with page.expect_response(lambda r: r.request.method=='POST' and '/evidence/EV-201/verify' in r.url) as verified:
   page.get_by_role('button',name='校验哈希',exact=True).click()
  check('evidence verify writes YANGZE only',YANGZE in verified.value.url and verified.value.ok)
  shots('evidence-yangze')
  page.goto(base+'/#/evidence?case='+HAILI)
  page.get_by_role('button',name='校验哈希',exact=True).wait_for()
  check('evidence cross-case clears YANGZE selection',page.locator('tr.sel').inner_text().startswith('EV-101'))
  with page.expect_response(lambda r: r.request.method=='POST' and '/verify' in r.url) as haili_verified:
   page.get_by_role('button',name='校验哈希',exact=True).click()
  check('evidence cross-case write targets Haili',HAILI in haili_verified.value.url and haili_verified.value.ok)
  page.goto(report_url)
  page.get_by_label('报告案件').wait_for()
  page.get_by_label('报告案件').select_option(HAILI)
  page.get_by_role('button',name='📄 生成双语报告',exact=True).click()
  page.get_by_test_id('report-sections').get_by_role('button').nth(11).wait_for()
  check('Haili Chinese template 12 sections',page.get_by_test_id('report-sections').get_by_role('button').count()==12)
  shots('report-haili')
  page.goto(base+'/#/recs?case='+YANGZE)
  page.get_by_role('button',name='＋ 新建安全建议',exact=True).wait_for()
  check('recommendations report entry preserves YANGZE',YANGZE in page.get_by_role('link',name='📄 国际格式报告 →',exact=True).get_attribute('href'))
  page.get_by_role('button',name='＋ 新建安全建议',exact=True).click()
  page.get_by_placeholder('建议标题',exact=True).fill('QA temporary local recommendation')
  page.get_by_placeholder('建议对象',exact=True).fill('QA local-only target')
  with page.expect_response(lambda r: r.request.method=='POST' and r.url.endswith('/recommendations')) as created:
   page.get_by_role('button',name='保存',exact=True).click()
  check('recommendation create targets YANGZE',YANGZE in created.value.url and created.value.ok)
  page.get_by_text('QA temporary local recommendation',exact=True).first.wait_for()
  shots('recommendations-yangze')
  page.get_by_role('link',name='📄 国际格式报告 →',exact=True).click()
  page.get_by_label('报告案件').wait_for()
  check('recommendations actual report navigation preserves YANGZE',YANGZE in page.url and page.get_by_label('报告案件').input_value()==YANGZE)
  page.goto(base+'/#/analysis?case='+YANGZE)
  page.get_by_test_id('whatif-table').wait_for()
  tabs=page.get_by_test_id('series-pick').get_by_role('tab')
  tabs.nth(1).click()
  check('analysis series derived label','【推算】' in page.get_by_test_id('series-label').inner_text())
  check('analysis Y1 critical','临界' in page.get_by_test_id('critical-Y1').inner_text())
  shots('analysis-yangze')
  page.goto(base+'/#/interview')
  page.get_by_test_id('ic-roster').get_by_role('button').first.wait_for()
  people=page.get_by_test_id('ic-roster').get_by_role('button')
  people.nth(1).click()
  page.get_by_test_id('ic-transcript').wait_for()
  check('interview fictional badge','示例数据（虚构）' in page.get_by_test_id('interview-page').inner_text())
  check('interview nonempty transcript',len(page.get_by_test_id('ic-transcript').inner_text())>20)
  shots('interview-demo')
  page.goto(base+'/#/colreg?case='+HAILI)
  page.get_by_test_id('colreg-pivot').wait_for()
  check('colreg public disclaimer','不作责任认定' in page.get_by_test_id('colreg-disclaimer').inner_text())
  check('colreg public data',page.locator('[data-band]').count()>=4)
  shots('colreg-haili')
  check('no Vite/framework overlays',page.locator('vite-error-overlay').count()==0)
  check('no JS or console errors',not errors)
  check('no HTTP errors',not network)
  browser.close()
except Exception as e:
 errors.append('RUN: '+repr(e));(OUT/'traceback.txt').write_text(traceback.format_exc())
finally:
 for p in procs:
  try:os.killpg(p.pid,signal.SIGTERM)
  except ProcessLookupError:pass
 for p in procs:
  try:p.wait(10)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL)
 for f in logs:f.close()
 result={'browser':subprocess.check_output([BINARY,'--version'],text=True).strip(),'base':base,'backend':f'127.0.0.1:{bp}','checks':checks,'errors':errors,'warnings':warns,'httpErrors':network,'mutations':writes,'screenshots':[p.name for p in OUT.glob('*.png')]}
 (OUT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(json.dumps(result,ensure_ascii=False,indent=2))
 if errors:raise SystemExit(1)
