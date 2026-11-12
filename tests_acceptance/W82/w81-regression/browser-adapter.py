import subprocess,time,json,urllib.request,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[3]; OUT=ROOT/'tests_acceptance/W82/w81-regression'
files=['web/src/pages/LobbyPage.tsx','web/src/Layout.tsx','web/src/main.tsx','web/src/routes.ts','web/src/cases/model.ts','web/src/styles/w8.css']
before={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files}
p=subprocess.Popen(['./node_modules/.bin/vite','--host','127.0.0.1','--port','5191','--strictPort'],cwd=ROOT/'web',stdout=open(OUT/'vite.log','w'),stderr=subprocess.STDOUT)
checks=[]
def check(v,m):
 assert v,m
 checks.append(m)
try:
 for _ in range(50):
  try: urllib.request.urlopen('http://127.0.0.1:5191');break
  except: time.sleep(.1)
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path='/tmp/w8-headless/chrome-headless-shell-linux64/chrome-headless-shell',headless=True,args=['--no-sandbox'])
  page=b.new_page(viewport={'width':1440,'height':1000});mode=['normal'];pending=[]
  cases=[{'caseId':'A','title':'案件甲','isFictionalDemo':True},{'caseId':'B','title':'案件乙','isFictionalDemo':False}]
  def route(r):
   path=r.request.url.split('/api/v1')[-1]
   if path=='/cases':
    if mode[0]=='hold':pending.append(r);return
    if mode[0]=='malformed':r.fulfill(json={'cases':cases});return
    if mode[0]=='error':r.fulfill(status=500,json={'message':'fail'});return
    r.fulfill(json=[] if mode[0]=='empty' else cases);return
   if path=='/cases/A' and mode[0]=='holdCase':pending.append(r);return
   if path in ['/cases/A','/cases/B']:
    r.fulfill(json=next(c for c in cases if c['caseId']==path[-1]));return
   if path.endswith('/timeline'):r.fulfill(json={'caseEpochUtc':'2024-01-01T00:00:00Z','durationSec':60,'events':[]});return
   if path.endswith('/tracks'):r.fulfill(json={'tracks':[]});return
   r.fulfill(json=[])
  page.route('**/api/v1/**',route)
  page.goto('http://127.0.0.1:5191/');page.get_by_text('共 2 个案件').wait_for();check(page.url.endswith('/lobby'),'default route opens lobby')
  check(page.get_by_role('link',name='进入案件：案件甲').count()==1,'list entry rendered')
  check('尚未选择' in page.locator('.case-chip').inner_text(),'lobby no selected case')
  mode[0]='malformed';page.get_by_role('button',name='刷新案件列表').click();page.get_by_role('alert').wait_for();check(page.get_by_role('link',name='进入案件：案件甲').count()==0,'malformed payload clears old rows and errors')
  mode[0]='empty';page.get_by_role('button',name='刷新案件列表').click();page.get_by_text('暂无案件。当前没有可进入的案件。').wait_for();check(True,'empty state')
  mode[0]='error';page.get_by_role('button',name='刷新案件列表').click();page.get_by_role('alert').wait_for();check(True,'error state')
  mode[0]='normal';page.get_by_role('button',name='重试',exact=True).click();page.get_by_text('共 2 个案件').wait_for();check(True,'retry recovers')
  mode[0]='hold';page.get_by_role('button',name='刷新案件列表').click();page.wait_for_timeout(100)
  mode[0]='empty';page.get_by_role('button',name='刷新案件列表').click();page.get_by_text('暂无案件。当前没有可进入的案件。').wait_for()
  for r in pending:r.fulfill(json=cases)
  pending.clear();page.wait_for_timeout(150);check(page.get_by_text('暂无案件。当前没有可进入的案件。').count()==1,'late refresh does not replace newer state')
  mode[0]='normal';page.get_by_role('button',name='刷新案件列表').click();page.get_by_role('link',name='进入案件：案件乙').click();page.wait_for_timeout(200)
  check(page.url.endswith('/evidence?case=B'),'enter correct case')
  check('B' in page.locator('.case-chip').inner_text(),'header correct case')
  check('case=B' in page.locator('a.nav-item').filter(has_text='国际格式报告').get_attribute('href'),'report link keeps case')
  page.go_back();page.get_by_text('共 2 个案件').wait_for();check('尚未选择' in page.locator('.case-chip').inner_text(),'back to lobby clears case header')
  page.go_forward();page.wait_for_timeout(150);check(page.url.endswith('case=B'),'forward retains case')
  page.goto('http://127.0.0.1:5191/#/lobby');page.get_by_text('共 2 个案件').wait_for()
  mode[0]='hold';page.get_by_role('button',name='刷新案件列表').click();page.wait_for_timeout(100)
  mode[0]='empty';page.locator('.role-select').select_option('Public');page.get_by_text('暂无案件。当前没有可进入的案件。').wait_for()
  for r in pending:r.fulfill(json=cases)
  page.wait_for_timeout(150);check(page.get_by_text('暂无案件。当前没有可进入的案件。').count()==1,'identity switch rejects prior list')
  mode[0]='normal';page.get_by_role('button',name='刷新案件列表').click();page.get_by_text('共 2 个案件').wait_for()
  page.get_by_role('link',name='进入案件：案件甲').click();page.wait_for_timeout(150);check('A' in page.locator('.case-chip').inner_text(),'enter different case A after B')
  page.goto('http://127.0.0.1:5191/#/lobby');page.get_by_text('共 2 个案件').wait_for()
  pending.clear()
  mode[0]='holdCase';page.goto('http://127.0.0.1:5191/#/evidence?case=A');page.wait_for_timeout(150)
  mode[0]='normal';page.goto('http://127.0.0.1:5191/#/evidence?case=B');page.wait_for_timeout(150)
  for r in pending:r.fulfill(json=cases[0])
  pending.clear();page.wait_for_timeout(150);check('案件乙' in page.locator('.case-chip').inner_text() and '案件甲' not in page.locator('.case-chip').inner_text(),'late case A metadata cannot refill case B header')
  page.goto('http://127.0.0.1:5191/#/lobby');page.get_by_text('共 2 个案件').wait_for()
  page.set_viewport_size({'width':768,'height':1024});page.screenshot(path=str(OUT/'lobby-768.png'),full_page=True)
  check(page.evaluate('document.documentElement.scrollWidth <= innerWidth'),'768px no horizontal overflow')
  refresh=page.get_by_role('button',name='刷新案件列表');refresh.focus();page.keyboard.press('Tab');page.keyboard.press('Shift+Tab')
  check(refresh.evaluate("e=>getComputedStyle(e).outlineWidth==='3px'"),'keyboard focus has visible 3px outline')
  colors=refresh.evaluate("e=>{const s=getComputedStyle(e);return [s.color,s.backgroundColor]}");check(colors==['rgb(240, 246, 255)', 'rgb(35, 73, 101)'],'refresh has explicit light-on-dark contrast colors')
  b.close()
 check(before=={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files},'implementation unchanged during acceptance')
 (OUT/'result.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2));print(json.dumps(checks,ensure_ascii=False))
finally:p.terminate();p.wait()
