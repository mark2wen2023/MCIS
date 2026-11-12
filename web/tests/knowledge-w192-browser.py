"""Real HTTP synthetic-only smoke. No real reports, model, deployment or external requests."""
import os,signal,subprocess,tempfile,time,urllib.request,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
procs=[]
def get(path,role='Investigator'):
 req=urllib.request.Request('http://127.0.0.1:18792/api/v1/knowledge'+path,headers={'X-MCIS-Role':role})
 return json.load(urllib.request.urlopen(req))
try:
 with tempfile.TemporaryDirectory(prefix='w192-synthetic-') as data:
  env={**os.environ,'MCIS_SEED_DEMO':'0','MCIS_DATA_DIR':data,'MCIS_PORT':'18792','MCIS_KNOWLEDGE_SUGGESTION_PROVIDER':'template-stub-v1'}
  procs.append(subprocess.Popen([str(ROOT/'service/.venv/bin/python'),'-m','mcis_service'],cwd=ROOT/'service',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True))
  procs.append(subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15792','--strictPort'],cwd=ROOT/'web',env={**os.environ,'MCIS_API':'http://127.0.0.1:18792'},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True))
  for url in ['http://127.0.0.1:18792/api/v1/knowledge/cards','http://127.0.0.1:15792']:
   for _ in range(100):
    try:urllib.request.urlopen(url,timeout=1);break
    except Exception:time.sleep(.1)
   else:raise AssertionError('Server unavailable')
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox']);p=browser.new_page(viewport={'width':1280,'height':900});p.set_default_timeout(8000)
   writes=[];p.on('request',lambda r:writes.append(r.url) if r.method=='POST' else None)
   p.goto('http://127.0.0.1:15792/#/knowledge');p.get_by_text('人工创建候选（不会自动公开）',exact=True).click()
   p.get_by_role('button',name='在表单中填入合成示例（不保存）').click()
   p.get_by_role('button',name='生成模板预览（不保存）').evaluate('(el)=>{el.click();el.click()}')
   p.get_by_text('template-stub-v1 · 非模型 · 未保存 · 待人工核查',exact=True).wait_for();assert len(writes)==1
   assert get('/cards?status=Candidate')['total']==0 and get('/audit')==[]
   p.get_by_role('button',name='用预览填入候选表单').click();assert len(writes)==1
   assert p.get_by_label('正文').input_value()==p.get_by_label('原文摘录').input_value()
   p.get_by_role('button',name='保存为内部待审候选',exact=True).click()
   p.get_by_text('待人工审批 1 条',exact=False).wait_for();assert get('/cards?status=Candidate')['total']==1 and get('/cards','Public')['total']==0
   p.get_by_role('button',name='生成模板预览（不保存）').click();p.get_by_text('template-stub-v1 · 非模型 · 未保存 · 待人工核查',exact=True).wait_for()
   p.get_by_label('原文摘录').fill('修改后的合成摘录');assert p.get_by_role('button',name='用预览填入候选表单').count()==0
   p.get_by_role('button',name='生成模板预览（不保存）').click();p.get_by_text('template-stub-v1 · 非模型 · 未保存 · 待人工核查',exact=True).wait_for()
   p.evaluate("async()=>{const a=await import('/src/api.ts');a.setIdentity('Public')}")
   p.get_by_text('只读已发布公开/合成知识卡',exact=False).wait_for();assert p.get_by_role('button',name='用预览填入候选表单').count()==0 and p.get_by_role('button',name='生成模板预览（不保存）').count()==0
   p.set_viewport_size({'width':390,'height':844});assert p.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
   browser.close()
 print('W19.2 real HTTP synthetic browser: preview double-click once, no persistence before explicit save, exact body/source copy, Candidate only, source edit invalidation, role invalidation, public/mobile passed')
finally:
 for p in procs:
  os.killpg(p.pid,signal.SIGTERM);p.wait()
