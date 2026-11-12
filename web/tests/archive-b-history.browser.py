"""Synthetic API doubles, isolated actual component; not backend acceptance."""
import subprocess,time,urllib.request,os,signal,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
s=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15855','--strictPort'],cwd=ROOT/'web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
try:
 for _ in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:15855',timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox']);p=b.new_page();p.set_default_timeout(8000);p.add_init_script("localStorage.setItem('mcis.role','LeadInvestigator')")
  requests=[];downloads=[];held=[];mode={'hold':False,'lookup403':False,'badsha':False};raw=b'synthetic historical bytes'
  headers={'Content-Disposition':'attachment; filename="original.bin"','Cache-Control':'no-store','X-Sha256':hashlib.sha256(raw).hexdigest()}
  p.on('download',lambda d:downloads.append(d))
  def route(r):
   u=r.request.url;requests.append(u)
   if '/archive-history/' in u:
    if mode['hold']:held.append(r)
    else:r.fulfill(body=raw,headers={**headers,'X-Sha256':'0'*64} if mode['badsha'] else headers)
   elif u.endswith('/intake'):r.fulfill(status=403 if mode['lookup403'] else 409,json={'code':'FORBIDDEN' if mode['lookup403'] else 'ARCHIVE_HISTORY_ONLY'})
   else:r.fulfill(status=404,json={})
  p.route('**/api/v1/**',route)
  def open_panel():
   p.get_by_role('button',name='＋ 登记已有文件副本 / 查看登记原件',exact=True).click();p.get_by_role('button',name='读取当前证据登记回执（只读）',exact=True).click()
  p.goto('http://127.0.0.1:15855/tests/archive-b-history-harness.html');open_panel()
  p.get_by_role('button',name='记录访问并下载历史原件',exact=True).wait_for();assert not any('/archive-history/' in u for u in requests)
  assert p.get_by_text('已核对登记回执',exact=False).count()==0
  mode['badsha']=True;p.get_by_role('button',name='记录访问并下载历史原件',exact=True).click();p.get_by_text('历史下载未完成',exact=False).wait_for();assert not downloads
  mode['badsha']=False
  with p.expect_download() as dl:p.get_by_role('button',name='记录访问并下载历史原件',exact=True).click()
  assert Path(dl.value.path()).read_bytes()==raw
  before=len(downloads);mode['hold']=True;p.get_by_role('button',name='记录访问并下载历史原件',exact=True).click()
  for _ in range(50):
   p.wait_for_timeout(20)
   if held:break
  assert held;p.get_by_role('button',name='Switch synthetic case',exact=True).click();held.pop().fulfill(body=raw,headers=headers);p.wait_for_timeout(100);assert len(downloads)==before
  mode['hold']=False;mode['lookup403']=True;open_panel();p.get_by_text('当前身份或案件策略不允许',exact=False).wait_for();assert p.get_by_role('button',name='记录访问并下载历史原件',exact=True).count()==0
  p.get_by_role('button',name='关闭（不撤销已发请求）',exact=True).click();mode['lookup403']=False;open_panel();p.get_by_role('button',name='记录访问并下载历史原件',exact=True).wait_for()
  mode['hold']=True;p.get_by_role('button',name='记录访问并下载历史原件',exact=True).click()
  for _ in range(50):
   p.wait_for_timeout(20)
   if held:break
  assert held;p.get_by_role('button',name='Switch synthetic identity',exact=True).click();held.pop().fulfill(body=raw,headers=headers);p.wait_for_timeout(100);assert len(downloads)==before
  p.unroute_all(behavior='ignoreErrors');b.close()
 print('Archive B history browser: explicit409-only history action,no receipt activation,hash refusal,exact download,case/identity late suppression,403 no guessed history passed(API doubles)')
finally:os.killpg(s.pid,signal.SIGTERM);s.wait()
