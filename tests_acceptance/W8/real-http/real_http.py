import subprocess, os, tempfile, time, json, urllib.request, hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path('/workspace/shared/mcis-w8-work'); SERVICE=Path('/workspace/shared/mcis-canonical-validation/service'); OUT=Path('/workspace/shared/w8-http-review')
files=['web/src/pages/LobbyPage.tsx','web/src/Layout.tsx','web/src/main.tsx','web/src/routes.ts','web/src/cases/model.ts','web/src/styles/w8.css']
before={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files}
checks=[]; procs=[]
def check(v,m):
 assert v,m
 checks.append(m)
def wait(url):
 for _ in range(200):
  try:return urllib.request.urlopen(url).read()
  except:time.sleep(.1)
 raise RuntimeError('startup timeout '+url)
try:
 with tempfile.TemporaryDirectory(prefix='mcis-w8-real-') as data:
  env=os.environ.copy();env.update(MCIS_DATA_DIR=data,MCIS_PORT='18781',MCIS_SEED_DEMO='1');env.pop('MCIS_DB_URL',None)
  procs.append(subprocess.Popen([str(SERVICE/'.venv/bin/python'),'-m','mcis_service'],cwd=SERVICE,env=env,stdout=open(OUT/'service.log','w'),stderr=subprocess.STDOUT))
  cases=json.loads(wait('http://127.0.0.1:18781/api/v1/cases'))
  check(isinstance(cases,list) and len(cases)==3,'real fresh SQLite service returns three canonical seeded cases')
  (OUT/'cases-response.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2))
  env=os.environ.copy();env['MCIS_API']='http://127.0.0.1:18781'
  procs.append(subprocess.Popen(['./node_modules/.bin/vite','--host','127.0.0.1','--port','5193','--strictPort'],cwd=ROOT/'web',env=env,stdout=open(OUT/'vite.log','w'),stderr=subprocess.STDOUT))
  wait('http://127.0.0.1:5193/')
  with sync_playwright() as pw:
   b=pw.chromium.launch(executable_path='/tmp/w8-headless/chrome-headless-shell-linux64/chrome-headless-shell',headless=True,args=['--no-sandbox'])
   page=b.new_page();errors=[];requests=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   page.on('response',lambda r:requests.append({'url':r.url,'status':r.status}) if '/api/v1/' in r.url else None)
   page.goto('http://127.0.0.1:5193/');page.get_by_text('共 3 个案件').wait_for()
   check(page.url.endswith('/lobby'),'actual proxy GET /cases parses and renders default lobby')
   check(page.locator('.w8-cases li').count()==3,'all real summaries rendered')
   check(page.locator('.w8-kind').filter(has_text='虚构演示').count()==1,'only fictional demo marked fictional')
   check(page.locator('.w8-kind').filter(has_text='非虚构案件').count()==2,'two public report cases marked non-fictional')
   page.get_by_role('button',name='刷新案件列表').click();page.get_by_text('共 3 个案件').wait_for();check(True,'real refresh completes')
   for c in cases:
    page.get_by_role('link',name='进入案件：'+c['title'],exact=True).click()
    page.wait_for_function('(id)=>document.querySelector(".case-chip").textContent.includes(id)',arg=c['caseId'])
    page.wait_for_timeout(500)
    check(c['caseId'] in page.url,'correct selected URL '+c['caseId'])
    check(c['title'].replace('【虚构演示】','') in page.locator('.case-chip').inner_text(),'actual case metadata header '+c['caseId'])
    href=page.locator('a.nav-item').filter(has_text='国际格式报告').get_attribute('href')
    expected='/report' if c['caseId']=='CASE-2026-DEMO-LILY-MARY' else '/report?case='+c['caseId']
    check(href.endswith(expected),'downstream navigation case '+c['caseId'])
    check(any('/cases/'+c['caseId']+'/evidence' in r['url'] and r['status']==200 for r in requests),'real evidence response '+c['caseId'])
    page.go_back();page.get_by_text('共 3 个案件').wait_for()
   page.locator('.role-select').select_option('Public');page.get_by_text('共 3 个案件').wait_for();check(True,'Public role switch fetches real case summaries')
   check(not errors,'no browser runtime errors')
   b.close()
  check(all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in before.items()),'implementation unchanged')
  (OUT/'requests.json').write_text(json.dumps(requests,indent=2))
finally:
 for p in reversed(procs):
  p.terminate()
  try:p.wait(timeout=10)
  except subprocess.TimeoutExpired:p.kill();p.wait()
 (OUT/'result.json').write_text(json.dumps({'checks':checks,'passed':len(checks)},ensure_ascii=False,indent=2))
print(json.dumps({'passed':len(checks),'checks':checks},ensure_ascii=False))
