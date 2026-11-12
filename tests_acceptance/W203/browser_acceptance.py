"""Independent synthetic UI response doubles: no actual model or production data."""
import os,signal,subprocess,time,urllib.request
from urllib.parse import unquote
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
s=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15805','--strictPort'],cwd=ROOT/'web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
try:
 for _ in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:15805',timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=os.environ['MCIS_BROWSER_BIN'],headless=True,args=['--no-sandbox']);p=b.new_page(viewport={'width':390,'height':844});p.set_default_timeout(6000)
  calls=[];held=[];mode={'hold':False,'registry_error':False,'empty':False,'bad_citation':False}
  agents=[dict(agent=a,name=a,status='configured',model='ONLY_CONFIGURATION') for a in ['ships','timeline','environment','people_ops','causes_ecfc','aggregate']]
  def row(case):return dict(caseId=case,draftId='AD-001',agent='people_ops',kind='statement_extraction',targetEntityType='interviewStatements',targetEntityId='IR/? &',payload={'recordId':'IR/? &','secret':'SECRET_BODY'},citations=[{'quote':'SECRET_QUOTE'}],status='Confirmed',model='MODEL_'+case)
  def route(r):
   u=r.request.url
   if u.endswith('/agents') or u.endswith('/agents/drafts'):
    calls.append((r.request.method,u))
    if u.endswith('/agents'):
     if mode['registry_error']:r.fulfill(status=500,json={'code':'TEST_ERROR'});return
     r.fulfill(json=agents);return
    case=unquote(u.split('/cases/')[1].split('/agents/drafts')[0])
    if mode['hold']:held.append((r,case));return
    r.fulfill(json=[] if mode['empty'] else [{**row(case),'citations':[None]}] if mode['bad_citation'] else [row(case)]);return
   r.fulfill(status=404,json={'code':'SYNTHETIC_ONLY'})
  p.route('**/api/v1/**',route);p.add_init_script("localStorage.setItem('mcis.role','LeadInvestigator')")
  def goto(case):p.goto('http://127.0.0.1:15805/#/agents?case='+case)
  goto('A');p.get_by_label('草稿筛选').select_option('all');p.get_by_text('MODEL_A（仅记录，不证明实际参与）',exact=True).wait_for()
  assert p.get_by_role('link',name='前往原笔录与人工审核').get_attribute('href')=='#/interview?case=A&record=IR%2F%3F+%26'
  assert 'SECRET_' not in p.locator('body').inner_text();assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
  # Real keyboard-only refresh, then empty response; must not call POST or retain old row.
  mode['empty']=True;button=p.get_by_role('button',name='重新读取登记与队列');button.focus();p.keyboard.press('Enter');p.get_by_text('当前筛选没有草稿。',exact=False).wait_for();assert 'MODEL_A' not in p.locator('body').inner_text()
  mode['empty']=False;mode['hold']=True;button.click()
  for _ in range(50):
   p.wait_for_timeout(20)
   if held:break
  assert held
  mode['hold']=False;p.evaluate("location.hash='#/agents?case=B'");p.get_by_label('草稿筛选').select_option('all');p.get_by_text('MODEL_B（仅记录，不证明实际参与）',exact=True).wait_for()
  r,case=held.pop()
  try:r.fulfill(json=[row(case)])
  except Exception:pass
  p.wait_for_timeout(100);assert 'MODEL_A' not in p.locator('body').inner_text()
  # Registry failure is distinct from disconnected; queue is independently readable.
  mode['registry_error']=True;p.get_by_role('button',name='重新读取登记与队列').click();p.get_by_text('登记读取失败：TEST_ERROR',exact=False).wait_for();assert p.get_by_text('未连接',exact=True).count()==0
  p.get_by_text('MODEL_B（仅记录，不证明实际参与）',exact=True).wait_for()
  mode['registry_error']=False;mode['bad_citation']=True;p.get_by_role('button',name='重新读取登记与队列').click();p.get_by_text('队列读取失败：响应或连接异常',exact=False).wait_for();assert 'MODEL_B' not in p.locator('body').inner_text()
  mode['bad_citation']=False
  mode['registry_error']=False;mode['hold']=True;p.get_by_role('button',name='重新读取登记与队列').click()
  for _ in range(50):
   p.wait_for_timeout(20)
   if held:break
  assert held
  p.evaluate("location.hash='#/knowledge'");p.get_by_role('heading',name='案例、疑难与方法知识卡').wait_for()
  r,case=held.pop()
  try:r.fulfill(json=[row(case)])
  except Exception:pass
  p.wait_for_timeout(100);assert 'MODEL_B' not in p.locator('body').inner_text()
  mode['hold']=False;goto('B');p.get_by_label('草稿筛选').wait_for()
  p.evaluate("async()=>{const a=await import('/src/api.ts');a.setIdentity('ExternalExpert')}");p.get_by_text('当前角色不展示内部模型',exact=False).wait_for();before=len(calls);p.wait_for_timeout(100);assert len(calls)==before
  assert 'ONLY_CONFIGURATION' not in p.locator('body').inner_text();assert all(m=='GET' for m,u in calls)
  p.unroute_all(behavior='ignoreErrors');b.close()
 print('W203 independent browser: encoded link, metadata-only, mobile keyboard refresh, empty clears old data, delayed case/navigation discard, independent registry failure, malformed citation whole-batch rejection, ExternalExpert no reads, GET-only passed')
finally:os.killpg(s.pid,signal.SIGTERM);s.wait()
