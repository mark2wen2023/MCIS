"""Synthetic API-double browser test; not backend acceptance."""
import subprocess,time,urllib.request,os,signal,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
s=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15857','--strictPort'],cwd=ROOT/'web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
try:
 for _ in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:15857',timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=os.environ['MCIS_BROWSER_BIN'],headless=True,args=['--no-sandbox']);p=b.new_page();p.set_default_timeout(8000)
  mode={'badHash':True,'save':'broken','recoverOwner':False};downloads=[];p.on('download',lambda d:downloads.append(d))
  raw=b'{}';sha=hashlib.sha256(raw).hexdigest();posts=[]
  su={'profile':'MCIS-KNOWLEDGE-ARCHIVE-1','archiveSha256':sha,'byteLength':2,'cardCount':0,'auditCount':0,'auditHeadSha256':'0'*64,'auditSnapshotCount':0,'snapshotCoverage':{'mode':'legacy-only','firstSeq':None,'priorHeadSha256':'0'*64},'scope':'current-online-library-snapshot','restoreMode':'isolated-read-only-history','identityMode':'unverified-self-reported'}
  def route(r):
   u=r.request.url
   if u.endswith('archives:export'):r.fulfill(body=raw,headers={'Content-Type':'application/json','Cache-Control':'no-store','Content-Disposition':'attachment; filename=archive.json','X-Sha256':'a'*64 if mode['badHash'] else sha})
   elif u.endswith('archives:preview'):r.fulfill(json=su)
   elif u.endswith('/archives') and r.request.method=='POST':
    posts.append(r.request.post_data)
    if mode['save']=='known':r.fulfill(status=422,json={'code':'KNOWLEDGE_ARCHIVE_INVALID'},headers={'X-MCIS-Write-Outcome':'not-committed'})
    elif mode['save']=='owner':r.fulfill(status=409,json={'code':'KNOWLEDGE_ARCHIVE_OWNER_MISMATCH'})
    elif mode['save']=='denied':r.fulfill(status=403,json={'code':'FORBIDDEN'})
    elif mode['save']=='ok':r.fulfill(status=200,json={'archive':{'summary':su,'importedUtc':'2026-11-12T00:00:00Z','importedBy':'调查员 A','importedRole':'LeadInvestigator'},'replayed':True})
    else:r.fulfill(status=201,body='broken')
   elif u.endswith('/'+sha):
    if mode['recoverOwner']:r.fulfill(json={'archive':{'summary':su,'importedUtc':'2026-11-12T00:00:00Z','importedBy':'Other Lead','importedRole':'LeadInvestigator'},'envelope':{'format':'MCIS-KNOWLEDGE-ARCHIVE','version':1,'cards':[],'audit':[],'auditSnapshots':{}}})
    else:r.fulfill(status=404,json={'code':'KNOWLEDGE_ARCHIVE_NOT_FOUND'})
   elif '/knowledge/cards' in u:r.fulfill(json={'items':[],'total':0,'limit':20,'offset':0})
   else:r.fulfill(status=403,json={'code':'FORBIDDEN'})
  p.add_init_script("if(!localStorage.getItem('mcis.role'))localStorage.setItem('mcis.role','LeadInvestigator')");p.route('**/api/v1/**',route);p.goto('http://127.0.0.1:15857/#/knowledge')
  p.get_by_text('全局知识库独立归档（首席限定）',exact=True).click();p.get_by_role('button',name='导出当前在线快照').click();p.get_by_text('下载摘要不符或会话变化',exact=True).wait_for();assert not downloads
  mode['badHash']=False
  with p.expect_download() as event:p.get_by_role('button',name='导出当前在线快照').click()
  assert Path(event.value.path()).read_bytes()==raw
  p.locator('.w19-archive input[type=file]').set_input_files({'name':'synthetic.json','mimeType':'application/json','buffer':raw});p.get_by_text('旧历史完整审核快照不可用，丢失信息为未知。',exact=True).wait_for()
  p.locator('.w19-archive input[type=checkbox]').check();p.get_by_role('button',name='确认保存历史',exact=True).evaluate('(e)=>{e.click();e.click()}');p.get_by_text('历史保存结果待核验',exact=False).wait_for();assert len(posts)==1
  p.get_by_role('button',name='按同摘要核查保存结果').click();p.get_by_text('尚未查到保存记录',exact=False).wait_for();assert p.locator('.w19-archive input[type=file]').first.is_disabled();assert len(posts)==1
  mode['recoverOwner']=True;p.get_by_role('button',name='按同摘要核查保存结果').click();p.get_by_text('档案属于另一声明主体，不能核验本次保存',exact=True).wait_for();assert p.locator('.w19-archive input[type=file]').first.is_disabled()
  p.reload();p.get_by_text('全局知识库独立归档（首席限定）',exact=True).click();p.get_by_text('历史保存结果待核验',exact=False).wait_for();assert p.locator('.w19-archive input[type=file]').first.is_disabled()
  assert p.evaluate("sessionStorage.getItem('mcis.knowledge-archive.pending-sha.v2:'+encodeURIComponent(JSON.stringify(['LeadInvestigator','调查员 A'])))")==sha
  p.evaluate("localStorage.setItem('mcis.operator','Other Lead')");p.reload();p.get_by_text('全局知识库独立归档（首席限定）',exact=True).click();assert sha not in p.locator('body').inner_text();assert p.locator('.w19-archive input[type=file]').is_enabled()
  p.evaluate("localStorage.removeItem('mcis.operator')");p.reload();p.get_by_text('全局知识库独立归档（首席限定）',exact=True).click();p.get_by_text('历史保存结果待核验',exact=False).wait_for()
  p.locator('.w19-archive input[type=file]').last.set_input_files({'name':'wrong.json','mimeType':'application/json','buffer':b'[]'});p.get_by_text('原包摘要不同，拒绝重试，未知锁保留',exact=True).wait_for();assert len(posts)==1
  p.locator('.w19-archive input[type=file]').last.set_input_files({'name':'original.json','mimeType':'application/json','buffer':raw});p.get_by_text('原包摘要匹配',exact=False).wait_for();mode['save']='denied';p.get_by_label('我确认仅重试同一原包，不创建新操作').check();p.get_by_role('button',name='用完全相同原包重试').click();p.get_by_role('alert').filter(has_text='403').wait_for();assert p.locator('.w19-archive input[type=file]').first.is_disabled()
  p.locator('.w19-archive input[type=file]').last.set_input_files({'name':'original.json','mimeType':'application/json','buffer':raw});p.get_by_text('原包摘要匹配',exact=False).wait_for();mode['save']='owner';p.get_by_label('我确认仅重试同一原包，不创建新操作').check();p.get_by_role('button',name='用完全相同原包重试').click();p.get_by_role('alert').filter(has_text='OWNER_MISMATCH').wait_for();assert p.locator('.w19-archive input[type=file]').first.is_disabled()
  p.locator('.w19-archive input[type=file]').last.set_input_files({'name':'original.json','mimeType':'application/json','buffer':raw});p.get_by_text('原包摘要匹配',exact=False).wait_for();mode['save']='ok';p.get_by_label('我确认仅重试同一原包，不创建新操作').check();p.get_by_role('button',name='用完全相同原包重试').click();p.get_by_text('已核验历史保存回执',exact=False).wait_for();assert len(posts)==4 and all(x=='{}' for x in posts)
  mode['save']='known';p.locator('.w19-archive input[type=file]').set_input_files({'name':'original.json','mimeType':'application/json','buffer':raw});p.get_by_text('旧历史完整审核快照不可用，丢失信息为未知。',exact=True).wait_for();p.locator('.w19-archive input[type=checkbox]').check();p.get_by_role('button',name='确认保存历史',exact=True).click();p.get_by_role('alert').filter(has_text='422').wait_for();assert p.locator('.w19-archive input[type=file]').is_enabled();assert p.evaluate("sessionStorage.getItem('mcis.knowledge-archive.pending-sha.v2:'+encodeURIComponent(JSON.stringify(['LeadInvestigator','调查员 A'])))") is None
  p.evaluate("localStorage.setItem('mcis.role','Investigator')");p.reload();p.get_by_text('全局知识库独立归档（首席限定）',exact=True).click();p.get_by_text('本功能仅向获授权首席角色开放',exact=False).wait_for();assert sha not in p.locator('body').inner_text()
  b.close()
 print('Knowledge archive browser API doubles: preview SHA binding, unknown201, synchronous double click single POST, recovery404 retains lock, hard reload digest-only recovery passed')
finally:os.killpg(s.pid,signal.SIGTERM);s.wait()
