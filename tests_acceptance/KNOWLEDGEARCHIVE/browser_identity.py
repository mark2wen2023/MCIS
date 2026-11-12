"""Independent UI API doubles: delayed responses after identity change, not backend acceptance."""
import hashlib,json,os,signal,subprocess,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
raw=b'{}';sha=hashlib.sha256(raw).hexdigest()
su={'profile':'MCIS-KNOWLEDGE-ARCHIVE-1','archiveSha256':sha,'byteLength':2,'cardCount':0,'auditCount':0,'auditHeadSha256':'0'*64,'auditSnapshotCount':0,'snapshotCoverage':{'mode':'legacy-only','firstSeq':None,'priorHeadSha256':'0'*64},'scope':'current-online-library-snapshot','restoreMode':'isolated-read-only-history','identityMode':'unverified-self-reported'}
metadata={'summary':su,'importedUtc':'2026-01-01T00:00:00Z','importedBy':'SYNTHETIC-HISTORY-MARKER','importedRole':'LeadInvestigator'}
doc={'archive':metadata,'envelope':{'format':'MCIS-KNOWLEDGE-ARCHIVE','version':1,'cards':[],'audit':[],'auditSnapshots':{'coverage':su['snapshotCoverage'],'items':[]}}}
s=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15859','--strictPort'],cwd=ROOT/'web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
try:
 for _ in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:15859',timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ['MCIS_BROWSER_BIN'],headless=True,args=['--no-sandbox'])
  for mode in ('preview','detail','download','save'):
   ctx=browser.new_context();p=ctx.new_page();p.set_default_timeout(8000);held=[];downloads=[];errors=[];posts=[]
   p.on('download',lambda d:downloads.append(d));p.on('pageerror',lambda e:errors.append(str(e)))
   p.add_init_script("localStorage.setItem('mcis.role','LeadInvestigator');localStorage.setItem('mcis.operator','首席调查官')")
   def route(r):
    u=r.request.url
    target=(mode=='preview' and u.endswith(':preview') or mode=='download' and u.endswith(':export') or mode=='detail' and u.endswith('/'+sha) or mode=='save' and u.endswith('/archives') and r.request.method=='POST')
    if target:
     if mode=='save':posts.append(r.request.post_data)
     held.append(r);return
    if '/knowledge/cards' in u:r.fulfill(json={'items':[],'total':0,'limit':20,'offset':0})
    elif ':preview' in u:r.fulfill(json=su)
    elif '/archives?' in u:r.fulfill(json={'items':[metadata],'total':1,'limit':20,'offset':0})
    else:r.fulfill(status=403,json={'code':'FORBIDDEN'})
   p.route('**/api/v1/**',route);p.goto('http://127.0.0.1:15859/#/knowledge')
   p.get_by_text('全局知识库独立归档（首席限定）',exact=True).click()
   if mode in ('preview','save'):
    p.locator('.w19-archive input[type=file]').set_input_files({'name':'synthetic.json','mimeType':'application/json','buffer':raw})
    if mode=='save':
     p.get_by_text('旧历史完整审核快照不可用，丢失信息为未知。',exact=True).wait_for();p.locator('.w19-archive input[type=checkbox]').check();p.get_by_role('button',name='确认保存历史',exact=True).click()
   elif mode=='detail':
    p.get_by_role('button',name='读取只读历史列表',exact=True).click();p.get_by_role('button',name='浏览历史原文',exact=True).click()
   else:p.get_by_role('button',name='导出当前在线快照',exact=True).click()
   for _ in range(100):
    if held:break
    p.wait_for_timeout(20)
   assert len(held)==1,mode
   p.locator('select[title="X-MCIS-Role"]').select_option('Investigator')
   if mode=='download':held.pop().fulfill(body=raw,headers={'Content-Type':'application/json','Cache-Control':'no-store','Content-Disposition':'attachment; filename=synthetic.json','X-Sha256':sha})
   elif mode=='save':held.pop().fulfill(status=201,json={'archive':metadata,'replayed':False})
   else:held.pop().fulfill(json=su if mode=='preview' else doc)
   p.wait_for_timeout(250)
   text=p.locator('body').inner_text()
   assert 'SYNTHETIC-HISTORY-MARKER' not in text and sha not in text and '已核验历史保存回执' not in text,mode
   assert not downloads and not errors,(mode,errors)
   if mode=='save':
    assert len(posts)==1
    assert p.evaluate('Object.keys(sessionStorage).filter(k=>k.startsWith("mcis.knowledge-archive.pending-sha.v2:")).map(k=>sessionStorage.getItem(k))')==[sha]
    p.locator('select[title="X-MCIS-Role"]').select_option('LeadInvestigator')
    p.get_by_text('全局知识库独立归档（首席限定）',exact=True).click()
    p.get_by_text('历史保存结果待核验',exact=False).wait_for();assert p.get_by_label('选择 UTF-8 JSON（最多 8 MiB，非 ZIP）',exact=True).is_disabled()
   ctx.close()
  browser.close()
 print('PASS 4 independent API-double UI scenarios: late preview/detail/export/save after identity change; no stale disclosure/download; save remains digest-only unknown.')
finally:
 if s.poll() is None:os.killpg(s.pid,signal.SIGTERM)
 s.wait()
