"""True loopback API/CLI/database/browser; delivery faults replace only real responses."""
import os,socket,subprocess,tempfile,time,json,urllib.request,urllib.error,sqlite3
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent
A='INDEPENDENT-BROWSER-A';B='INDEPENDENT-BROWSER-B';checks=[]
def check(value,label):
 assert value,label
 checks.append(label)
with tempfile.TemporaryDirectory(prefix='ecfc-independent-browser-')as tmp:
 listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(128);apiport=listener.getsockname()[1]
 reserve=socket.socket();reserve.bind(('127.0.0.1',0));webport=reserve.getsockname()[1];reserve.close()
 env={**os.environ,'PYTHONPATH':str(ROOT/'service'),'ECFC_ACCEPTANCE_DATA':tmp,'ECFC_ACCEPTANCE_FD':str(listener.fileno()),'MCIS_API':f'http://127.0.0.1:{apiport}'}
 processes=[]
 def counts():
  with sqlite3.connect(Path(tmp)/'mcis.db')as s:return tuple(s.execute('select count(*) from '+t).fetchone()[0]for t in ('ecfc_drafts','ecfc_draft_audit','ecfc_draft_requests'))
 try:
  processes.append(subprocess.Popen([str(ROOT/'service/.venv/bin/python'),str(HERE/'server.py')],env=env,pass_fds=(listener.fileno(),),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL));listener.close()
  processes.append(subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',str(webport),'--strictPort'],cwd=ROOT/'web',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL))
  for port,path in [(apiport,'/api/v1/health'),(webport,'/')]:
   for _ in range(200):
    assert all(p.poll()is None for p in processes),'owned process exited'
    try:urllib.request.urlopen(f'http://127.0.0.1:{port}'+path,timeout=1);break
    except Exception:time.sleep(.1)
   else:raise RuntimeError('owned server unavailable')
  with sync_playwright()as pw:
   browser=pw.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
   page=browser.new_page();page.set_default_timeout(15000);posts=[]
   page.add_init_script("if(!localStorage.getItem('mcis.role')){localStorage.setItem('mcis.role','LeadInvestigator');localStorage.setItem('mcis.operator','Independent Browser')}")
   page.on('request',lambda r:posts.append(r)if r.method=='POST'and r.url.endswith('/ecfc/save')else None)
   origin=f'http://127.0.0.1:{webport}';url=origin+'/#/ecfc?case='+A
   def ack():page.get_by_label('我了解保存后整个案件暂不能导出',exact=False).check()
   def reopen():page.get_by_role('button',name='重新打开服务端草稿（放弃未保存修改）',exact=True).click();page.get_by_label('调查范围 / 假设说明',exact=True).wait_for()
   def save():page.get_by_role('button',name='保存 ECFC 人工草稿',exact=True).click();page.get_by_text('此请求的保存回执已核验。',exact=False).wait_for()
   page.goto(url);page.get_by_label('调查范围 / 假设说明',exact=True).fill('Independent browser hypothesis')
   check(page.get_by_role('button',name='保存 ECFC 人工草稿',exact=True).is_disabled(),'backup acknowledgement required')
   page.get_by_role('button',name='添加人工节点',exact=True).click();page.get_by_label('节点描述 1',exact=True).fill('Synthetic vessel turns <script>alert(1)</script>')
   check(page.get_by_label('相对时间秒 1（留空未知）',exact=True).input_value()=='','unknown time remains blank')
   page.locator('.ecfc-source input').check();page.locator('.ecfc-node input[type=checkbox]').last.check()
   page.get_by_role('button',name='预览结构与方法提示（不保存）',exact=True).click();page.get_by_role('heading',name='结构已接受 · 方法提示单列',exact=True).wait_for()
   check(counts()==(0,0,0),'preview is zero-write with real CLI')
   check(page.locator('svg rect[stroke-dasharray]').count()>0,'presumptive event dashed rectangle')
   ack();button=page.get_by_role('button',name='保存 ECFC 人工草稿',exact=True);button.evaluate('(e)=>{e.click();e.click()}');page.get_by_text('此请求的保存回执已核验。',exact=False).wait_for()
   check(len(posts)==1 and counts()==(1,1,1),'double click commits once')
   reopen();check(page.get_by_label('节点描述 1',exact=True).input_value().endswith('<script>alert(1)</script>'),'saved content reopens as literal text')
   page.get_by_role('button',name='添加人工节点',exact=True).click();page.get_by_label('节点类型 2',exact=True).select_option('Condition');page.get_by_label('节点描述 2',exact=True).fill('Synthetic fog hypothesis')
   page.get_by_role('button',name='添加人工连线',exact=True).click();page.get_by_label('起点 ID 1',exact=True).fill('N2');page.get_by_label('终点 ID 1',exact=True).fill('N1')
   page.get_by_role('button',name='预览结构与方法提示（不保存）',exact=True).click();page.get_by_role('heading',name='结构已接受 · 方法提示单列',exact=True).wait_for()
   check(page.locator('svg ellipse[stroke-dasharray]').count()==1,'presumptive condition ellipse')
   ack();save();check(counts()==(1,2,2),'edit creates exactly second revision')
   reopen();page.get_by_role('button',name='读取审计摘要',exact=True).click();page.get_by_text('版本 2 ·',exact=False).wait_for();check(page.get_by_text('版本 1 ·',exact=False).count()==1,'independent audit shows two revisions')
   # Real commit, delivery replaced with503. Never claims the write rolled back.
   page.get_by_label('调查范围 / 假设说明',exact=True).fill('Committed response deliberately lost');ack()
   def lose(route):
    real=route.fetch();assert real.status==200;route.fulfill(status=503,json={'code':'SYNTHETIC_LOST_RESPONSE'})
   page.route('**/ecfc/save',lose);page.get_by_role('button',name='保存 ECFC 人工草稿',exact=True).click();page.get_by_role('heading',name='保存结果待核对',exact=True).wait_for();page.unroute('**/ecfc/save',lose)
   check(counts()==(1,3,3),'unknown transport still committed once')
   page.reload();page.get_by_role('heading',name='保存结果待核对',exact=True).wait_for();check(len(posts)==3,'reload does not resubmit unknown request')
   check(page.get_by_role('button',name='保存 ECFC 人工草稿',exact=True).is_disabled(),'unknown lock blocks new request')
   page.get_by_role('button',name='读取最新草稿及审计以核对待核请求',exact=True).click();page.get_by_label('我已核对最新草稿及审计',exact=False).check();page.get_by_role('button',name='明确放弃本地等待并重新读取最新草稿',exact=True).click();page.get_by_label('调查范围 / 假设说明',exact=True).wait_for()
   check(page.get_by_label('调查范围 / 假设说明',exact=True).input_value()=='Committed response deliberately lost'and counts()==(1,3,3),'explicit abandon fresh-loads latest without new write')
   page.locator('.ecfc-source input').check();page.get_by_label('我已核对当前来源并重新选择',exact=False).check()
   # A real saved reply held until navigation; it cannot populate the other case.
   page.get_by_label('调查范围 / 假设说明',exact=True).fill('Late A response');ack();held=[]
   def hold(route):
    real=route.fetch();assert real.status==200;held.append((route,real))
   page.route('**/ecfc/save',hold);page.get_by_role('button',name='保存 ECFC 人工草稿',exact=True).click()
   for _ in range(100):
    if held:break
    page.wait_for_timeout(50)
   check(bool(held),'real save response held after commit')
   page.evaluate("location.hash='/ecfc?case='+"+json.dumps(B));page.get_by_label('调查范围 / 假设说明',exact=True).wait_for()
   route,real=held.pop();route.fulfill(response=real);page.unroute('**/ecfc/save',hold);page.wait_for_timeout(200)
   check(page.get_by_label('调查范围 / 假设说明',exact=True).input_value()==''and 'Late A response'not in page.locator('body').inner_text(),'late reply does not populate new case')
   page.go_back();page.get_by_role('heading',name='保存结果待核对',exact=True).wait_for();check(len(posts)==4 and counts()==(1,4,4),'back restores scoped unknown lock without repeat save')
   # Real identity downgrade is rejected by server and removes raw editor.
   page.evaluate("async()=>{const api=await import('/src/api.ts');api.setIdentity('Investigator','Independent Browser')}");page.get_by_role('alert').wait_for();check(page.get_by_label('调查范围 / 假设说明',exact=True).count()==0,'identity downgrade removes raw editor')
   page.set_viewport_size({'width':390,'height':844});check(page.locator('body').evaluate('(e)=>e.scrollWidth<=innerWidth+2'),'mobile denied screen has no horizontal overflow')
   browser.close()
  print(json.dumps({'passed':len(checks),'checks':checks,'finalCounts':counts()},ensure_ascii=False))
 finally:
  for p in reversed(processes):
   if p.poll()is None:p.terminate()
  for p in processes:
   try:p.wait(timeout=10)
   except subprocess.TimeoutExpired:p.kill();p.wait()
