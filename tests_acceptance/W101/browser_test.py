from pathlib import Path
import os,subprocess,time,urllib.request,json,signal,traceback,zipfile,io,tempfile,sys
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];SCRIPT=Path(__file__).resolve().parent
OUT=Path(os.environ.get('MCIS_W101_ARTIFACT_DIR',tempfile.mkdtemp(prefix='mcis-w101-qa-')));OUT.mkdir(parents=True,exist_ok=True)
SERVICE=Path(os.environ.get('MCIS_W101_SERVICE_ROOT',ROOT/'service'))
PY=Path(os.environ.get('MCIS_W101_PYTHON',SERVICE/'.venv/bin/python'))
BIN=os.environ.get('MCIS_BROWSER_BIN')
if not BIN: raise RuntimeError('Set MCIS_BROWSER_BIN to your installed Chromium executable')
checks=[];procs=[];errors=[]
def ck(name,v):
 if not v:
  try:(OUT/('failure-'+name.replace('/','_')+'.txt')).write_text(page.url+'\n'+page.locator('body').inner_text());page.screenshot(path=str(OUT/'failure.png'),full_page=True)
  except Exception:pass
 checks.append({'name':name,'passed':bool(v)});assert v,name
base='http://127.0.0.1:15810'
env=dict(os.environ,MCIS_DATA_DIR=tempfile.mkdtemp(prefix='mcis-w101-data-'),PYTHONPATH=os.pathsep.join([str(SERVICE),str(SCRIPT)]),MCIS_W101_ARTIFACT_DIR=str(OUT),MCIS_API='http://127.0.0.1:18810',MCIS_AGENT_BASE_URL='',MCIS_AGENT_MODEL='')
def start(cmd,cwd,name):
 p=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=open(OUT/name,'w'),stderr=subprocess.STDOUT,start_new_session=True);procs.append(p)
def wait(url):
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 for _ in range(100):
  try:opener.open(url,timeout=1);return
  except Exception:time.sleep(.1)
 raise Exception('server not ready '+url)
try:
 start([str(PY),'-m','uvicorn','qa_app:app','--host','127.0.0.1','--port','18810'],ROOT,'browser-service.log');wait('http://127.0.0.1:18810/api/v1/health')
 start(['npm','run','dev','--','--port','15810'],ROOT/'web','browser-vite.log');wait(base)
 subprocess.run([str(PY),str(SCRIPT/'http_test.py')],check=True,env=env)
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=BIN,headless=True,args=['--no-sandbox','--disable-gpu'])
  page=b.new_page(viewport={'width':1440,'height':900});page.on('pageerror',lambda e:errors.append(str(e)))
  requests=[];page.on('request',lambda r:requests.append({'url':r.url,'method':r.method}) if '/api/v1/' in r.url else None)
  def goto(case='QA-TRACK'):
   page.goto(base+'/#/track?case='+case)
   try:page.locator('.w10-case').wait_for()
   except Exception:
    (OUT/'goto-failure.txt').write_text(page.url+'\n'+page.locator('body').inner_text());page.screenshot(path=str(OUT/'goto-failure.png'),full_page=True);raise
  def ready():page.get_by_role('button',name='读取已保存航迹',exact=True).wait_for()
  goto();ready();ck('track page real content no overlay',page.get_by_role('heading',name='已保存航迹检查').count()==1 and page.locator('vite-error-overlay').count()==0)
  ck('2051 stored points + 2000 plot samples explicit','显示 2000 / 2051 点' in page.locator('body').inner_text() and page.locator('svg circle').count()==2000)
  ck('100 rows first page',page.locator('tbody tr').count()==100 and '第 1 / 21 页' in page.locator('body').inner_text())
  ck('date-line warning and source caveat','经度跨度超过180°' in page.locator('body').inner_text() and '不证明证据完整或可信' in page.locator('body').inner_text())
  page.get_by_role('button',name='查看点 1',exact=True).focus();page.keyboard.press('Enter');detail=page.get_by_role('region',name='选中点详情')
  ck('keyboard selection exact negative/zero/360/UTC',all(t in detail.inner_text() for t in ['2025-12-31T23:59:59Z','-1 s','0 kn / 360°','-180° / -90°']))
  ck('malicious source remains literal text', '<script>alert(1)</script>' in detail.inner_text() and page.locator('.w10-page script').count()==0 and page.locator('.w10-page img').count()==0)
  page.get_by_role('button',name='下一页',exact=True).click();ck('pagination preserves exact index',page.get_by_role('button',name='查看点 101',exact=True).count()==1 and page.locator('tbody tr').count()==100)
  page.get_by_label('筛选来源类型').select_option('Unknown');ck('unknown filter not guessed measured','第 1 / 7 页 · 683 点' in page.locator('body').inner_text() and page.get_by_role('region',name='选中点详情').count()==0)
  page.get_by_label('筛选来源类型').select_option('ManualDrawn');ck('empty source filter no fake points','此来源类型没有航迹点' in page.locator('body').inner_text() and page.locator('svg circle').count()==0)
  page.get_by_label('筛选来源类型').select_option('all')
  a=page.get_by_label('起始相对秒（可留空）');z=page.get_by_label('结束相对秒（可留空）');before=len(requests);a.fill('0');z.fill('100');ck('typing does not request',len(requests)==before)
  page.get_by_role('button',name='读取已保存航迹',exact=True).click();ready();page.get_by_text('第 1 / 2 页 · 101 点 · 每页 100 点',exact=True).wait_for();ck('window applies real HTTP without resampling',any('fromSec=0&toSec=100' in x['url'] for x in requests) and not any('stepSec' in x['url'] for x in requests))
  before=len(requests);a.fill('100');z.fill('0');page.get_by_role('button',name='读取已保存航迹',exact=True).click();ck('reversed window rejected no network',len(requests)==before and '起始时间不能晚于结束时间' in page.get_by_role('alert').inner_text())
  a.fill('');z.fill('');page.get_by_role('button',name='读取已保存航迹',exact=True).click();ready();page.get_by_text('显示 2000 / 2051 点',exact=False).wait_for();ck('refresh resets filter page selection',page.get_by_label('筛选来源类型').input_value()=='all' and '第 1 / 21 页' in page.locator('body').inner_text())
  for width,height in [(1440,900),(1920,1080)]:
   page.set_viewport_size({'width':width,'height':height});ck(str(width)+' desktop no outer overflow',page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'));page.screenshot(path=str(OUT/f'track-{width}.png'),full_page=True);page.locator('.w10-chart-detail').scroll_into_view_if_needed();page.screenshot(path=str(OUT/f'track-chart-{width}.png'),full_page=False)
  goto('QA-EMPTY');ck('nonfictional empty case honest', '非虚构案件' in page.locator('.w10-case').inner_text() and '本案没有船舶或已保存航迹' in page.locator('body').inner_text() and page.locator('svg').count()==0)
  goto('QA-NOPOINT');ck('registered empty vessel no synthetic track','本船没有已保存航迹点' in page.locator('body').inner_text() and page.locator('svg').count()==0)
  goto('CASE-2026-DEMO-LILY-MARY');opts=page.get_by_label('选择船舶').locator('option').evaluate_all('(xs)=>xs.map(x=>x.value)');ck('real seed has two selectable vessels',len(opts)==2);page.get_by_label('选择船舶').select_option(opts[1]);ck('vessel selection works',page.get_by_label('选择船舶').input_value()==opts[1]);ck('fictional badge explicit','虚构演示' in page.locator('.w10-case').inner_text())
  page.locator('select.role-select').select_option('Public');page.locator('.w10-case').wait_for();ck('Public uses real read permission',page.locator('tbody tr').count()>0)
  page.locator('select.role-select').select_option('Investigator');page.locator('.w10-case').wait_for();goto()
  # All error and race scenarios below are deliberate endpoint response doubles.
  point={'vesselId':'QA-V1','timeSec':0,'utc':'2026-01-01T00:00:00Z','latDeg':0,'lonDeg':0,'sogKn':0,'cogDeg':360,'source':'LATE-OLD'}
  payload={'caseId':'QA-TRACK','tracks':[{'vesselId':'QA-V1','points':[point]}]}
  budget={'caseId':'QA-TRACK','tracks':[{'vesselId':'QA-V1','points':[{**point,'source':'BUDGET-FIXTURE'}]*50000}]}
  page.route('**/cases/QA-TRACK/tracks*',lambda r:r.fulfill(json=budget));page.get_by_role('button',name='读取已保存航迹',exact=True).click();page.get_by_text('显示 2000 / 50000 点',exact=False).wait_for();ck('50000 accepted all table pages and plot budget','第 1 / 500 页' in page.locator('body').inner_text() and page.locator('svg circle').count()==2000)
  page.locator('svg g[aria-hidden] > circle').nth(1999).click(force=True);ck('plot endpoint selects exact final table point',page.get_by_role('button',name='查看点 50000',exact=True).count()==1 and '第 500 / 500 页' in page.locator('body').inner_text());page.unroute('**/cases/QA-TRACK/tracks*');page.get_by_role('button',name='读取已保存航迹',exact=True).click();page.locator('.w10-case').wait_for()
  scenarios=[('wrong case',200,{**payload,'caseId':'WRONG'}),('wrong point vessel',200,{'caseId':'QA-TRACK','tracks':[{'vesselId':'QA-V1','points':[{**point,'vesselId':'WRONG'}]}]}),('bad coordinate',200,{'caseId':'QA-TRACK','tracks':[{'vesselId':'QA-V1','points':[{**point,'latDeg':91}]}]}),('invalid UTC',200,{'caseId':'QA-TRACK','tracks':[{'vesselId':'QA-V1','points':[{**point,'utc':'2026-02-30T00:00:00Z'}]}]}),('403',403,{}),('404',404,{}),('500',500,{}),('too many',200,{'caseId':'QA-TRACK','tracks':[{'vesselId':'QA-V1','points':[point]*50001}]}),('too many buckets',200,{'caseId':'QA-TRACK','tracks':[{'vesselId':'V'+str(i),'points':[]} for i in range(1001)]})]
  for name,status,data in scenarios:
   page.route('**/cases/QA-TRACK/tracks*',lambda r,_req,status=status,data=data:r.fulfill(status=status,json=data));page.get_by_role('button',name='读取已保存航迹',exact=True).click();page.get_by_role('alert').wait_for();ck(name+' fails closed',page.locator('.w10-case').count()==0 and page.locator('tbody tr').count()==0);page.unroute('**/cases/QA-TRACK/tracks*');page.get_by_role('button',name='读取已保存航迹',exact=True).click();page.locator('.w10-case').wait_for()
  # Snapshot switch with old response delayed, then navigate between actual cases.
  held=[];page.route('**/cases/QA-TRACK/tracks*',lambda r:held.append(r));page.get_by_role('button',name='读取已保存航迹',exact=True).click();page.get_by_role('link',name='返回案件大厅',exact=True).click();page.wait_for_url('**/#/lobby')
  for r in held:
   try:r.fulfill(json=payload)
   except Exception:pass
  page.unroute('**/cases/QA-TRACK/tracks*');page.go_back();page.get_by_role('heading',name='已保存航迹检查',exact=True).wait_for();ck('fast Back no stale response','LATE-OLD' not in page.locator('.w10-page').inner_text());ck('aborted navigation read can recover',page.get_by_role('button',name='读取已保存航迹',exact=True).is_enabled());page.get_by_role('button',name='读取已保存航迹',exact=True).click();page.locator('.w10-case').wait_for()
  page.get_by_role('link',name='本案船舶参数',exact=True).click();page.locator('.w9-page').wait_for();page.go_back();page.locator('.w10-case').wait_for();page.go_forward();page.locator('.w9-page').wait_for();page.go_back();page.locator('.w10-case').wait_for();ck('normal Back Forward keeps case',page.locator('.w10-case').inner_text().find('QA-TRACK')>=0)
  # Switching to a different case must never accept an old response.
  held=[];page.route('**/cases/QA-TRACK/tracks*',lambda r:held.append(r));page.get_by_role('button',name='读取已保存航迹',exact=True).click();page.goto(base+'/#/track?case=QA-EMPTY');page.locator('.w10-case').wait_for()
  for r in held:
   try:r.fulfill(json=payload)
   except Exception:pass
  page.unroute('**/cases/QA-TRACK/tracks*');ck('cross-case late data suppressed','QA-EMPTY' in page.locator('.w10-case').inner_text() and page.locator('tbody tr').count()==0)
  goto();held=[];page.route('**/cases/QA-TRACK/tracks*',lambda r:held.append(r));page.get_by_role('button',name='读取已保存航迹',exact=True).click();page.locator('select.role-select').select_option('Public')
  for r in held:
   try:r.fulfill(status=403,json={})
   except Exception:pass
  page.unroute('**/cases/QA-TRACK/tracks*');page.get_by_role('alert').wait_for();ck('role change clears old data',page.locator('tbody tr').count()==0);page.locator('select.role-select').select_option('Investigator');page.locator('.w10-case').wait_for()
  page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(OUT/'track-mobile.png'),full_page=True);mobile=page.evaluate('document.documentElement.scrollWidth');hide=page.add_style_tag(content='.w10-page{display:none!important}');baseline=page.evaluate('document.documentElement.scrollWidth');hide.evaluate('(e)=>e.remove()');checks.append({'name':'390 shared shell overflow','passed':mobile<=390,'knownDefect':mobile>390 and mobile==baseline,'width':mobile,'baseline':baseline});ck('no added mobile outer overflow',mobile==baseline)
  ck('all UI requests read only',all(r['method']=='GET' for r in requests));ck('no runtime JS errors',not errors);b.close()
except Exception:
 (OUT/'browser-error.txt').write_text(traceback.format_exc());raise
finally:
 (OUT/'browser-results.json').write_text(json.dumps({'checks':checks,'errors':errors},ensure_ascii=False,indent=2))
 for p in procs:
  try:os.killpg(p.pid,signal.SIGTERM)
  except ProcessLookupError:pass
print(f"{sum(c['passed'] for c in checks)} browser checks passed; {sum(bool(c.get('knownDefect')) for c in checks)} known shared-shell defect")
