"""Independent async UI acceptance with synthetic response doubles, not API integration."""
import os,signal,subprocess,time,urllib.request,copy
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
server=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15793','--strictPort'],cwd=ROOT/'web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
try:
 for _ in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:15793',timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox']);p=b.new_page();p.set_default_timeout(6000)
  held=[];writes=[]
  def route(r):
   if r.request.url.endswith('/suggestions'):
    writes.append(r.request.post_data_json);held.append(r);return
   if '/knowledge/cards' in r.request.url:r.fulfill(json={'items':[],'total':0,'limit':20,'offset':0});return
   r.fulfill(status=404,json={'code':'SYNTHETIC_ONLY'})
  p.route('**/api/v1/**',route)
  def enter():
   p.goto('http://127.0.0.1:15793/#/knowledge');p.get_by_text('人工创建候选（不会自动公开）',exact=True).click();p.get_by_role('button',name='在表单中填入合成示例（不保存）').click()
  def dispatch():
   p.get_by_role('button',name='生成模板预览（不保存）').evaluate('(el)=>{el.click();el.click()}')
   for _ in range(50):
    p.wait_for_timeout(20)
    if held:break
   assert len(held)==1
  def late():
   r=held.pop();source=copy.deepcopy(r.request.post_data_json['source'])
   d={'profile':'MCIS-KNOWLEDGE-SUGGESTION-1','provider':'template-stub-v1','modelUsed':False,'persisted':False,'reviewRequired':True,'inputDigest':'a'*64,'content':{'kind':r.request.post_data_json['kind'],'source':source,'title':'迟到结果不得出现','summary':source['excerpt'],'body':source['excerpt'],'tags':['合成待审'],'applicability':'仅合成'},'warnings':['非模型']}
   try:r.fulfill(json=d)
   except Exception:pass # Abort after source/navigation invalidation may close the route.
   p.wait_for_timeout(100)
   assert p.get_by_text('迟到结果不得出现',exact=True).count()==0
  enter();dispatch();assert len(writes)==1
  p.get_by_label('原文摘录').fill('修改后合成摘录');late();assert p.get_by_role('button',name='用预览填入候选表单').count()==0
  dispatch();p.evaluate("location.hash='#/knowledge?case=OTHER'");p.wait_for_timeout(50);late();assert p.get_by_role('button',name='用预览填入候选表单').count()==0
  enter();dispatch();p.evaluate("async()=>{const a=await import('/src/api.ts');a.setIdentity('Public')}");p.get_by_text('只读已发布公开/合成知识卡',exact=False).wait_for();late()
  assert p.get_by_role('button',name='生成模板预览（不保存）').count()==0
  p.evaluate("async()=>{const a=await import('/src/api.ts');a.setIdentity('Investigator')}")
  enter();before=p.get_by_label('正文').input_value();dispatch();held.pop().fulfill(status=503,json={'code':'SUGGESTIONS_UNAVAILABLE','message':'模板关闭'})
  p.get_by_text('预览读取失败，原候选未更改，可重试。',exact=False).wait_for();assert p.get_by_label('正文').input_value()==before and p.get_by_role('button',name='用预览填入候选表单').count()==0
  dispatch();held.pop().abort('failed');p.get_by_text('预览读取失败，原候选未更改，可重试。',exact=False).wait_for()
  assert p.get_by_label('正文').input_value()==before
  error=p.get_by_role('alert').inner_text();assert '核查队列' not in error and '勿重复发送' not in error and '重试' in error
  assert all('source' in item and set(item)=={'kind','source'} for item in writes)
  p.unroute_all(behavior='ignoreErrors');b.close()
 print('W19.2 independent browser: duplicate-click gate, delayed source-edit/navigation/role-change response discarded; 503/network errors retain draft and safe retry text; no candidate POST invoked (synthetic doubles)')
finally:os.killpg(server.pid,signal.SIGTERM);server.wait()
