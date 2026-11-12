"""Synthetic API doubles only: overview never posts to inference/review endpoints."""
import copy,os,signal,subprocess,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
server=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15803','--strictPort'],cwd=ROOT/'web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
try:
 for _ in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:15803',timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox']);p=b.new_page(viewport={'width':1280,'height':900});p.set_default_timeout(7000)
  calls=[];held=[];mode={'hold':False,'error':None,'invalid':False}
  agents=[dict(agent=a,name=a,status='configured' if a=='people_ops' else 'not_connected',model='synthetic-model' if a=='people_ops' else 'none') for a in ['ships','timeline','environment','people_ops','causes_ecfc','aggregate']]
  row=dict(caseId='SYNTHETIC',draftId='AD-001',agent='people_ops',kind='statement_extraction',targetEntityType='interviewStatements',targetEntityId='IR-01',payload={'recordId':'IR-01','privateText':'NEVER SHOW PRIVATE'},citations=[{'quote':'NEVER SHOW QUOTE'}],status='PendingReview',model='synthetic-model',createdUtc='2026-11-12T00:00:00Z')
  def route(r):
   u=r.request.url
   if u.endswith('/agents') or '/agents/drafts' in u:
    calls.append((r.request.method,u))
    if u.endswith('/agents'):r.fulfill(json=agents);return
    if mode['hold']:held.append(r);return
    if mode['error']:r.fulfill(status=mode['error'],json={'code':'FORBIDDEN' if mode['error']==403 else 'ERROR'});return
    if mode['invalid']:r.fulfill(json=[{**row,'caseId':'OTHER'}]);return
    r.fulfill(json=[{**row,'draftId':'AD-'+str(i).zfill(3)} for i in range(1,23)]+[{**row,'draftId':'AD-030','status':'Confirmed'}]);return
   r.fulfill(status=404,json={'code':'SYNTHETIC_ONLY'})
  p.route('**/api/v1/**',route);p.add_init_script("localStorage.setItem('mcis.role','LeadInvestigator')")
  p.goto('http://127.0.0.1:15803/#/agents?case=SYNTHETIC');p.get_by_text('待审 22 / 全部 23',exact=False).wait_for()
  assert '主智能体会话与自动任务调度尚未接通' in p.locator('body').inner_text();assert '已配置 · 连接与能力未验证' in p.locator('body').inner_text()
  assert 'NEVER SHOW' not in p.locator('body').inner_text();assert p.get_by_role('link',name='前往原笔录与人工审核').count()==20
  p.get_by_role('button',name='下一页',exact=True).click();assert p.get_by_role('link',name='前往原笔录与人工审核').count()==2
  p.get_by_label('草稿筛选').select_option('reviewed');assert p.get_by_role('link',name='前往原笔录与人工审核').count()==1
  assert p.get_by_role('link',name='前往原笔录与人工审核').get_attribute('href')=='#/interview?case=SYNTHETIC&record=IR-01'
  mode['error']=403;p.get_by_role('button',name='重新读取登记与队列').click();p.get_by_text('后端拒绝当前身份或案件策略。',exact=False).wait_for();assert p.get_by_role('link',name='前往原笔录与人工审核').count()==0
  mode['error']=None;mode['invalid']=True;p.get_by_role('button',name='重新读取登记与队列').click();p.get_by_text('响应或连接异常',exact=False).wait_for()
  mode['invalid']=False;mode['hold']=True;p.get_by_role('button',name='重新读取登记与队列').click()
  for _ in range(50):
   p.wait_for_timeout(20)
   if held:break
  assert held
  p.evaluate("async()=>{const a=await import('/src/api.ts');a.setIdentity('Public')}");p.get_by_text('当前角色不展示内部模型',exact=False).wait_for();before=len(calls)
  held.pop().fulfill(json=[row]);p.wait_for_timeout(100);assert 'synthetic-model' not in p.locator('body').inner_text() and len(calls)==before
  p.set_viewport_size({'width':390,'height':844});p.wait_for_timeout(100);assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
  assert all(m=='GET' for m,u in calls)
  p.unroute_all(behavior='ignoreErrors');b.close()
 print('W20.3 synthetic browser: real status wording, metadata-only queue, pagination, safe link,403/invalid batch fail closed, delayed role response discarded, no protected Public reads/no writes,mobile passed')
finally:os.killpg(server.pid,signal.SIGTERM);server.wait()
