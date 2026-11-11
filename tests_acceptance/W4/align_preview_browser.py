"""Local-only W4.1 browser acceptance; requires frozen implementation and official headless shell.
Runs isolated disposable service data, Vite build/preview and browser on 127.0.0.1.
Screenshots remain local and are never uploaded. Not mobile/production/Unity acceptance.
"""
from pathlib import Path
from urllib.parse import urlparse
import hashlib
import os, socket, subprocess, time, urllib.request, urllib.error, tempfile, signal, json, traceback
from playwright.sync_api import sync_playwright, expect
ROOT=Path(os.environ.get('MCIS_REPO',str(Path(__file__).resolve().parents[2]))).resolve()
OUT=Path(os.environ['MCIS_BROWSER_OUT']).resolve(); OUT.mkdir(parents=True,exist_ok=False)
BINARY=os.environ['MCIS_BROWSER_EXECUTABLE']; DOTNET=os.environ['MCIS_DOTNET']
PYTHON=str(ROOT/'service/.venv/bin/python')
OTHER='CASE-2026-DEMO-LILY-MARY'; CASE='CJK-2024-1230-YangZe22-VegaDream'
def port():
 with socket.socket() as s: s.bind(('127.0.0.1',0)); return s.getsockname()[1]
def wait(url):
 for _ in range(200):
  try:
   with urllib.request.urlopen(url,timeout=2):return
  except Exception:time.sleep(.15)
 raise RuntimeError('not ready '+url)
bp,fp=port(),port(); base=f'http://127.0.0.1:{fp}'; back=f'http://127.0.0.1:{bp}/api/v1'
data=Path(tempfile.mkdtemp(prefix='w41-data-'))
env=dict(os.environ,MCIS_DATA_DIR=str(data),MCIS_PORT=str(bp),MCIS_API=f'http://127.0.0.1:{bp}',MCIS_CORE=str(ROOT/'tests_acceptance/W6/mcis-core-norebuild.sh'),MCIS_CORE_DLL=str(ROOT/'tools/mcis-core/out/mcis-core.dll'))
env.pop('MCIS_DB_URL',None)
procs=[]; handles=[]; checks=[]; errors=[]; consoles=[]; http=[]; writes=[]; shots=[]; phase='setup'
def api(path,method='GET',body=None,role='LeadInvestigator'):
 b=None if body is None else json.dumps(body).encode()
 req=urllib.request.Request(back+path,data=b,method=method,headers={'X-MCIS-Role':role,'X-MCIS-Operator':'BrowserAcceptance','Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=15) as r:return json.load(r)
def cp(path):return '/cases/'+CASE+path
def start(cmd,cwd,name):
 f=open(OUT/name,'w');handles.append(f);procs.append(subprocess.Popen(cmd,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True))
def check(name,ok,detail=None):
 checks.append({'name':name,'passed':bool(ok),'detail':detail})
 if not ok:raise AssertionError(name)
freeze=(ROOT/'logs/w4.1-impl-hashes-frozen.txt').read_text();(OUT/'implementation-hashes.txt').write_text(freeze)
def frozen_ok():
 return all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha for sha,path in (line.split(maxsplit=1) for line in freeze.strip().splitlines()))
try:
 check('frozen implementation hashes before',frozen_ok())
 start([PYTHON,'-m','mcis_service'],ROOT/'service','backend.log');wait(back+'/health')
 subprocess.run(['npx','vite','build','--outDir',str(OUT/'dist'),'--emptyOutDir','--logLevel','error'],cwd=ROOT/'web',env=env,check=True,capture_output=True)
 start(['npx','vite','preview','--outDir',str(OUT/'dist'),'--host','127.0.0.1','--port',str(fp),'--strictPort'],ROOT/'web','frontend.log');wait(base)
 before=api(cp('/audit?category=Consultation')); before_seq=max([e['seq'] for e in before],default=0)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=BINARY,headless=True,args=['--no-sandbox','--disable-gpu'])
  page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
  external=[]
  def local_only(route):
   if urlparse(route.request.url).hostname not in ['127.0.0.1',None]:external.append(route.request.url);route.abort()
   else:route.continue_()
  page.route('**/*',local_only)
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda m:consoles.append({'phase':phase,'type':m.type,'text':m.text}) if m.type in ['error','warning'] else None)
  page.on('response',lambda r:http.append({'phase':phase,'status':r.status,'url':r.url,'role':r.request.headers.get('x-mcis-role')}) if r.status>=400 else None)
  page.on('request',lambda r:writes.append({'phase':phase,'method':r.method,'url':r.url,'body':r.post_data}) if r.method in ['POST','PATCH','PUT','DELETE'] else None)
  import sqlite3
  def snapshot():
   with sqlite3.connect(data/'mcis.db') as db:
    names=[r[0] for r in db.execute("select name from sqlite_master where type='table' order by name")]
    return {name:sorted(db.execute('select * from "'+name+'"').fetchall(),key=repr) for name in names}
  original=snapshot()
  panel=page.locator('.w4-preview');result=panel.get_by_role('region',name='临时预览结果')
  def expand():
   d=page.locator('.w4-preview-disclosure')
   if d.get_attribute('open') is None:d.locator('summary').first.click()
   expect(panel.get_by_role('button',name='重新读取预览权限')).to_be_visible()
  def role(name):page.locator('.topbar select').select_option(name);expand()
  def filltwo(offsetless=False):
   expect(panel.locator('textarea.w4-csv').first).to_be_visible()
   if panel.locator('textarea.w4-csv').count()==1:
    panel.get_by_role('button',name='添加CSV源').click();expect(panel.locator('textarea.w4-csv')).to_have_count(2)
   for i,v in enumerate([45,50]):
    panel.locator('textarea.w4-csv').nth(i).fill('time_utc,cog_deg\n2026-05-18T06:20:00'+('' if offsetless else 'Z')+','+str(v)+'\n2026-05-18T06:21:00'+('' if offsetless else 'Z')+','+str(v)+'\n')
    panel.get_by_label('UTC时间列名',exact=True).nth(i).fill('time_utc');panel.get_by_label('值列名',exact=True).nth(i).fill('cog_deg')
   panel.get_by_role('checkbox').check()
  def run():
   with page.expect_response(lambda r:r.request.method=='POST' and '/timeline/align-preview' in r.url) as response:panel.get_by_role('button',name='计算临时预览',exact=True).click()
   return response.value
  phase='normal';page.goto(base+'/#/evidence?case='+CASE)
  expect(page.locator('.w4-preview-disclosure')).to_be_visible();check('preview collapsed by default',page.locator('.w4-preview-disclosure').get_attribute('open') is None)
  expand();expect(panel.locator('textarea.w4-csv')).to_be_visible()
  check('explicit temporary UTC units no anchors warnings',all(x in panel.inner_text() for x in ['未改人工复核','不写审计','无offset按UTC','航速为节','未提供锚点']))
  check('explicit supported mappings',panel.locator('fieldset select').first.locator('option').evaluate_all('(xs)=>xs.map(x=>x.value)')==['Heading','CourseOverGround','SpeedOverGround'])
  check('ack required',panel.get_by_role('button',name='计算临时预览',exact=True).is_disabled())
  panel.get_by_role('checkbox').check();n=len(writes);runbutton=panel.get_by_role('button',name='计算临时预览',exact=True);runbutton.click();expect(panel.get_by_role('alert')).to_contain_text('非空');check('empty CSV blocked before request',len(writes)==n)
  filltwo();n=len(writes)
  with page.expect_response(lambda r:r.request.method=='POST' and '/timeline/align-preview' in r.url) as resp:runbutton.evaluate('(b)=>{b.click();b.click()}')
  check('real core preview HTTP200',resp.value.status==200);doc=resp.value.json();expect(result).to_be_visible();check('doubleclick one preview',len(writes)==n+1)
  check('real scoped five degree conflict',doc['caseId']==CASE and doc['result']['caseId']==CASE and doc['previewOnly'] and not doc['persisted'] and any(c['delta']==5 and c['deltaUnit']=='deg' for c in doc['result']['conflicts']))
  check('unanchored remains uncalibrated',not doc['result']['calibration']['allCalibrated'] and '未全部校准' in result.inner_text() and '5 deg' in result.inner_text())
  check('all persistent tables unchanged after successful preview',snapshot()==original)
  filltwo(offsetless=True);check('editing clears old result',result.count()==0);r=run();check('offsetless UTC succeeds',r.status==200 and r.json()['result']['conflicts'][0]['delta']==5)
  # UTF8 budget:90000 Chinese chars=270000bytes, below limit in character count but over byte limit.
  panel.locator('textarea.w4-csv').first.fill('中'*90000);n=len(writes);runbutton.click();expect(panel.get_by_role('alert')).to_contain_text('256KiB');check('UTF8 byte budget blocks without request',len(writes)==n)
  filltwo();panel.get_by_role('button',name='添加CSV源').click();panel.get_by_role('button',name='添加CSV源').click();check('four source maximum',panel.locator('textarea.w4-csv').count()==4 and panel.get_by_role('button',name='添加CSV源').is_disabled())
  panel.get_by_role('button',name='移除数据源').last.click();panel.get_by_role('button',name='移除数据源').last.click()
  # Incorrect timestamp mapping is real core input, may return diagnostic rather thanHTTP error.
  panel.get_by_label('UTC时间列名',exact=True).first.fill('missing_column');r=run();check('malformed input never stale success',r.status in [200,422] and (r.status!=200 or r.json()!=doc))
  if r.status==200:expect(result).to_contain_text('导入诊断')
  else:expect(panel.get_by_role('alert')).to_be_visible()
  phase='role-readonly';role('InterestedState');expect(panel.locator('textarea.w4-csv')).to_have_value('');filltwo();r=run();check('timeline RO can preview',r.status==200)
  # Hold old successful preview while leaving case; no result orCSV may reappear.
  phase='normal';held=[]
  def holdpreview(route):
   response=route.fetch();held.append((route,response.body(),response.status))
  page.route('**/timeline/align-preview',holdpreview);runbutton.click()
  for _ in range(100):
   if held:break
   page.wait_for_timeout(20)
  check('old preview response held',bool(held));page.evaluate('(h)=>location.hash=h','#/evidence?case='+OTHER);expand();expect(panel.locator('textarea.w4-csv')).to_have_value('')
  for route,body,status in held:route.fulfill(status=status,content_type='application/json',body=body)
  page.wait_for_timeout(100);check('old case preview cannot refill new case',result.count()==0 and panel.locator('textarea.w4-csv').input_value()=='')
  page.unroute('**/timeline/align-preview')
  role('Investigator');filltwo();held_role=[]
  def holdrole(route):
   response=route.fetch();held_role.append((route,response.body(),response.status))
  page.route('**/timeline/align-preview',holdrole);runbutton.click()
  for _ in range(100):
   if held_role:break
   page.wait_for_timeout(20)
  check('allowed old-role preview response held',bool(held_role));phase='role-denied';role('Public');expect(panel.get_by_role('alert')).to_contain_text('无timeline读取权限')
  for route,body,status in held_role:route.fulfill(status=status,content_type='application/json',body=body)
  page.wait_for_timeout(100);check('late allowed preview cannot refill denied role',result.count()==0 and panel.locator('textarea.w4-csv').count()==0)
  page.unroute('**/timeline/align-preview')
  # Hold old whole-Evidence list payload acrossDeny; prove obsoletedata cannot refill.
  role('Investigator');held_ev=[]
  def holdevidence(route):
   if route.request.headers.get('x-mcis-role')=='Investigator':
    response=route.fetch();held_ev.append((route,response.body(),response.status))
   else:route.continue_()
  page.route('**/cases/'+OTHER+'/evidence',holdevidence);page.reload();expand()
  for _ in range(100):
   if held_ev:break
   page.wait_for_timeout(20)
  check('old Evidence response held',bool(held_ev));filltwo();phase='role-denied';role('Public');expect(panel.get_by_role('alert')).to_contain_text('无timeline读取权限')
  check('Deny has no CSV or preview action',panel.locator('textarea.w4-csv').count()==0 and panel.get_by_role('button',name='计算临时预览',exact=True).count()==0)
  for route,body,status in held_ev:route.fulfill(status=status,content_type='application/json',body=body)
  page.wait_for_timeout(150);check('old Evidence list cannot refill Deny',page.locator('tr').filter(has_text='EV-001').count()==0)
  page.unroute('**/cases/'+OTHER+'/evidence')
  role('Investigator');filltwo();phase='expected-policy-error'
  page.route('**/access-policy',lambda route:route.fulfill(status=503,content_type='application/json',body=json.dumps({'code':'TEST_POLICY_DOWN','message':'Injected preview policy failure'})))
  panel.get_by_role('button',name='重新读取预览权限').click();expect(panel.get_by_role('alert')).to_contain_text('权限读取失败');check('policy failure fail closed',panel.locator('textarea.w4-csv').count()==0)
  page.unroute('**/access-policy');phase='normal';panel.get_by_role('button',name='重新读取预览权限').click();expect(panel.locator('textarea.w4-csv').first).to_be_visible();filltwo()
  phase='expected-preview-failure';n=len(writes)
  page.route('**/timeline/align-preview',lambda route:route.fulfill(status=503,content_type='application/json',body=json.dumps({'code':'CORE_UNAVAILABLE','message':'Injected local core failure'})))
  r=run();expect(panel.get_by_role('alert')).to_contain_text('CORE_UNAVAILABLE');page.wait_for_timeout(150);check('failure explicit no retry or stale result',len(writes)==n+1 and result.count()==0)
  page.unroute('**/timeline/align-preview');phase='normal';r=run();expect(result).to_be_visible()
  for width in (1440,768):
   page.set_viewport_size({'width':width,'height':1000});result.scroll_into_view_if_needed();page.screenshot(path=str(OUT/f'align-{width}.png'),full_page=True);shots.append(f'align-{width}.png')
   dims=page.evaluate('({document:document.documentElement.scrollWidth,main:document.querySelector(".main").clientWidth,scroll:document.querySelector(".main").scrollWidth})');check('no layout overflow '+str(width),dims['document']==width and dims['scroll']<=dims['main'],dims)
  check('all persistent table contents unchanged including audit evidence conflict custody',snapshot()==original)
  check('every browser POST is scoped preview not legacy core',all('/cases/' in w['url'] and w['url'].endswith('/timeline/align-preview') for w in writes),writes)
  check('no external network',not external,external);check('no JS errors',not errors,list(errors))
  unexpected=[r for r in http if not (r['status']==403 and r['role'] in ['InterestedState','Public']) and not (r['phase'] in ['expected-policy-error','expected-preview-failure'] and r['status']==503) and not (r['url'].endswith('/timeline/align-preview') and r['status']==422)]
  check('all HTTP errors explained',not unexpected,unexpected);check('no unexpected console errors',not [c for c in consoles if c['type']=='error' and not c['text'].startswith('Failed to load resource:')],consoles)
  check('frozen implementation hashes after',frozen_ok())
  browser.close()
except Exception as e:
 errors.append('HARNESS: '+repr(e));(OUT/'exception.txt').write_text(traceback.format_exc())
 try: (OUT/'failure-body.txt').write_text(page.locator('body').inner_text());page.screenshot(path=str(OUT/'failure.png'),full_page=True)
 except Exception:pass
 raise
finally:
 (OUT/'result.json').write_text(json.dumps({'checks':checks,'errors':errors,'console':consoles,'httpErrors':http,'mutations':writes,'screenshotsLocalOnly':shots},ensure_ascii=False,indent=2))
 for p in reversed(procs):
  try:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=10)
  except Exception:pass
 for f in handles:f.close()
if any(not c['passed'] for c in checks):
 raise SystemExit(1)
