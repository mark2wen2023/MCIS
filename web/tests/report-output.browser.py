"""Browser API doubles using actual synthetic renderer ZIP fixtures, not real backend UI acceptance."""
import os,subprocess,time,signal,urllib.request,json,base64,hashlib,re
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
text=(ROOT/'web/tests/report-output-fixtures.ts').read_text();fixtures=json.loads(text.split('export const fixtures = ',1)[1].rsplit(' as const',1)[0]);f=fixtures['pdf'];body=base64.b64decode(f['zipBase64']);headers=f['context']['headers'];preview=f['context']['preview']
s=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15861','--strictPort'],cwd=ROOT/'web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
try:
 for _ in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:15861',timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=os.environ['MCIS_BROWSER_BIN'],headless=True,args=['--no-sandbox']);p=b.new_page();p.set_default_timeout(8000);posts=[];held=[];downloads=[];previews=[];mode={'post':'success','preview':200};p.on('download',lambda d:downloads.append(d))
  p.add_init_script("if(!localStorage.getItem('mcis.role')){localStorage.setItem('mcis.role','LeadInvestigator');localStorage.setItem('mcis.operator','Synthetic Export')}")
  def route(r):
   if r.request.method=='GET':
    previews.append(r.request.url)
    r.fulfill(status=mode['preview'],json=preview,headers={'Cache-Control':'no-store'})
   else:
    posts.append(r.request.post_data)
    if mode['post']=='hold':held.append(r)
    elif mode['post']=='bad':r.fulfill(body=b'broken',headers={**headers,'content-length':'6'})
    elif mode['post']=='403':r.fulfill(status=403,json={'code':'FORBIDDEN'})
    elif mode['post']=='500':r.fulfill(status=500,json={'code':'FAILED'})
    else:r.fulfill(body=body,headers=headers)
  p.route('**/api/v1/**',route)
  def fresh():
   p.goto('http://127.0.0.1:15861/tests/report-output-harness.html');p.evaluate('sessionStorage.clear()');p.reload()
  def inspect():
   p.get_by_label('单一文件格式').select_option('pdf');p.get_by_label('本次渲染语言').select_option('zh');p.get_by_role('button',name='读取当前已保存快照（不生成）',exact=True).click();p.get_by_text(preview['reportDocumentSha256'],exact=True).wait_for();p.get_by_label('我已核对已保存快照',exact=False).check()
  fresh();inspect()
  with p.expect_download() as dl:p.get_by_role('button',name='生成可追溯下载包（仅一次）',exact=True).evaluate('(e)=>{e.click();e.click()}')
  assert Path(dl.value.path()).read_bytes()==body and len(posts)==1;p.get_by_text('请自行确认完整文件落盘',exact=False).wait_for();assert p.evaluate('sessionStorage.length')==0
  for error in ['bad','500']:
   fresh();mode['post']=error;inspect();before=len(posts);p.get_by_role('button',name='生成可追溯下载包（仅一次）',exact=True).click();p.get_by_role('heading',name='当次交付结果待核验',exact=True).wait_for();p.wait_for_timeout(100);assert len(posts)==before+1 and len(downloads)==1
   p.reload();p.get_by_role('heading',name='当次交付结果待核验',exact=True).wait_for();assert p.get_by_label('单一文件格式').is_disabled();assert p.get_by_role('button',name='放弃此投递并重新预览（不是恢复原文件）',exact=True).is_disabled()
   p.get_by_label('我已检查本地下载',exact=False).check();p.get_by_role('button',name='放弃此投递并重新预览（不是恢复原文件）',exact=True).click();assert p.get_by_role('button',name='生成可追溯下载包（仅一次）',exact=True).count()==0;assert len(posts)==before+1
  fresh();mode['post']='success';inspect();p.evaluate("()=>{window._storageSet=Storage.prototype.setItem;Storage.prototype.setItem=function(){throw new Error('unavailable')}}");before=len(posts);p.get_by_role('button',name='生成可追溯下载包（仅一次）',exact=True).click();p.get_by_text('无法可靠保存待核元数据',exact=False).wait_for();assert len(posts)==before
  p.get_by_role('button',name='重新检查本地待核存储（不生成）',exact=True).click();p.get_by_text('本地待核存储仍不可用',exact=False).wait_for();assert len(posts)==before
  p.evaluate('()=>{Storage.prototype.setItem=window._storageSet}');p.get_by_role('button',name='重新检查本地待核存储（不生成）',exact=True).click();p.get_by_text('本地存储检查完成',exact=False).wait_for();assert p.get_by_role('button',name='生成可追溯下载包（仅一次）',exact=True).count()==0;assert len(posts)==before
  p.evaluate("args=>{const who=JSON.stringify(['LeadInvestigator','Synthetic Export']);sessionStorage.setItem('mcis.report-output.unknown.v1:'+encodeURIComponent(JSON.stringify([who,args.caseId,args.reportId])),'{broken');sessionStorage.setItem('unrelated-scope','keep')}",preview);p.reload();p.get_by_text('待核元数据无法读取或结构异常',exact=False).wait_for();assert p.get_by_role('button',name='清除此范围本地待核标记并重新预览',exact=True).is_disabled()
  p.get_by_label('我已检查本地下载，明确清除此身份',exact=False).check();p.get_by_role('button',name='清除此范围本地待核标记并重新预览',exact=True).click();p.get_by_text('已明确清除本范围本地待核标记',exact=False).wait_for();assert p.evaluate("sessionStorage.getItem('unrelated-scope')")=='keep';assert len(posts)==before;assert p.get_by_role('button',name='生成可追溯下载包（仅一次）',exact=True).count()==0
  fresh();p.evaluate("()=>{const real=window.fetch;window.fetch=(url,init)=>real(url,{...init,signal:undefined})}");mode['post']='hold';inspect();before=len(posts);p.get_by_role('button',name='生成可追溯下载包（仅一次）',exact=True).click()
  for _ in range(30):
   if held:break
   p.wait_for_timeout(20)
  assert held;p.get_by_role('button',name='停止等待（不撤销已发操作）',exact=True).click();p.get_by_text('已停止等待并丢弃迟到响应',exact=False).wait_for();held.pop().fulfill(body=body,headers=headers);p.wait_for_timeout(100);assert len(downloads)==1 and len(posts)==before+1;assert p.get_by_role('heading',name='当次交付结果待核验',exact=True).count()==1;assert p.get_by_label('单一文件格式').is_disabled()
  for button in ['Switch case','Switch identity']:
   fresh();mode['post']='hold';inspect();p.get_by_role('button',name='生成可追溯下载包（仅一次）',exact=True).click()
   for _ in range(30):
    if held:break
    p.wait_for_timeout(20)
   assert held and p.get_by_label('单一文件格式').is_disabled();p.get_by_role('button',name=button,exact=True).click();held.pop().fulfill(body=body,headers=headers);p.wait_for_timeout(150);assert len(downloads)==1 and p.get_by_role('heading',name='当次交付结果待核验',exact=True).count()==0
   p.evaluate("localStorage.setItem('mcis.role','LeadInvestigator');localStorage.setItem('mcis.operator','Synthetic Export')")
  fresh();mode['post']='403';inspect();p.get_by_role('button',name='生成可追溯下载包（仅一次）',exact=True).click();p.get_by_text('Parent protected text cleared',exact=True).wait_for();assert 'PROTECTED-REPORT-TEXT' not in p.locator('body').inner_text();assert p.evaluate('sessionStorage.length')==1
  b.close()
 print('Report output browser API doubles passed: exact downloaded ZIP, sync double click, unknown/no retry, reload/abandon, storage failure no POST, late case/identity no save,403 clears parent preserving metadata')
finally:os.killpg(s.pid,signal.SIGTERM);s.wait()
