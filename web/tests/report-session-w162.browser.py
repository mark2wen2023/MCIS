"""Synthetic API doubles: session isolation, not service/CLI acceptance."""
import subprocess,time,urllib.request,os,signal,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
server=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15862','--strictPort'],cwd=ROOT/'web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
def report(case='CASE-A',rid='R1',text='SECRET-A'):
 return dict(caseId=case,reportId=rid,familyId='F',parentReportId=None,templateId='imo-cic',lang='bilingual',version=1,status='Draft',realDataStatus='authorized-public',isFictionalDemo=False,createdUtc='2026-11-12T00:00:00Z',createdBy='synthetic',sections=[dict(sectionId='s',titleZh=text,titleEn='Synthetic',textZh=text,textEn=text,dataSources=[],status='Draft',source='Generated',generatedText=dict(textZh='',textEn=''),reviewedBy=None,reviewedAt=None,reviews=[],missing=False,sentences=[])],disclaimerZh='synthetic',disclaimerEn='synthetic',reportHref='#/report')
try:
 for _ in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:15862',timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
  page=browser.new_page();page.set_default_timeout(8000);page.on('pageerror',lambda e:print('PAGEERROR',e,flush=True));held=[];mode={'hold':False,'write':False,'audit403':False,'exportHold':False}
  def route(r):
   u=r.request.url;case='CASE-B' if '/CASE-B/' in u else 'CASE-A';rid='R2' if '/R2' in u else 'R1'
   if u.endswith('/cases'):r.fulfill(json=[dict(caseId=c,title='Dynamic '+c,isFictionalDemo=False) for c in ['CASE-A','CASE-B']]);return
   if 'report-glossary' in u:r.fulfill(json=[]);return
   if r.request.headers.get('x-mcis-role')=='Observer':r.fulfill(status=403,json={'code':'FORBIDDEN','message':'synthetic denial'});return
   if 'report-templates' in u:r.fulfill(json={'caseId':'CASE-B' if 'CASE-B' in u else 'CASE-A','templates':[],'realDataStatus':'authorized-public'})
   elif u.endswith('/reports') and r.request.method=='POST' and mode['write']:held.append(r)
   elif u.endswith('/reports'):r.fulfill(json={'caseId':case,'realDataStatus':'authorized-public','reports':[report(case,'R1'),report(case,'R2','SECRET-R2')]})
   elif u.endswith('/gisis'):r.fulfill(json={'caseId':case,'isFictionalDemo':False,'realDataStatus':'authorized-public','fields':[],'notice':'synthetic'})
   elif u.endswith('/audit'):r.fulfill(status=403 if mode['audit403'] else 200,json={'code':'FORBIDDEN','message':'audit denied'} if mode['audit403'] else [])
   elif '/reports/' in u and '/export?' in u:
    if mode['exportHold']:held.append(r)
    else:r.fulfill(body=b'synthetic pdf',headers={'Content-Type':'application/pdf'})
   elif '/reports/' in u:
    if mode['hold'] and rid=='R1':held.append(r)
    else:r.fulfill(json=report(case,rid,'SECRET-R2' if rid=='R2' else 'SECRET-A'))
   else:r.fulfill(status=404,json={})
  page.route('**/api/v1/**',route)
  page.goto('http://127.0.0.1:15862/#/report?case=CASE-A&report=R1')
  page.get_by_text('SECRET-A / Synthetic',exact=True).first.wait_for()
  assert page.get_by_role('option',name='Dynamic CASE-B').count()==1
  page.evaluate("async()=>{const a=await import('/src/api.ts');a.setIdentity('Observer','test')} ")
  page.get_by_text('当前身份无权访问完整报告内容',exact=False).wait_for();assert page.get_by_text('SECRET-A / Synthetic',exact=True).count()==0
  assert page.get_by_role('button',name='📄 生成双语报告',exact=True).is_disabled()
  body=page.locator('body').inner_text()
  for phrase in ['仅支持满足完整资料权限的原文报告','尚未提供字段级脱敏报告','默认 Investigator 受限是有意的访问边界变更','联系授权管理员按单位规则处理']:assert phrase in body
  page.evaluate("async()=>{const a=await import('/src/api.ts');a.setIdentity('LeadInvestigator','test')}")
  page.get_by_text('SECRET-A / Synthetic',exact=True).first.wait_for()
  mode['hold']=True
  page.evaluate("location.hash='#/report?case=CASE-A&report=R1&lang=en'")
  for _ in range(50):
   page.wait_for_timeout(20)
   if held:break
  assert held
  page.evaluate("location.hash='#/report?case=CASE-A&report=R2'")
  page.get_by_text('SECRET-R2 / Synthetic',exact=True).first.wait_for()
  held.pop().fulfill(json=report(text='LATE-SECRET'));page.wait_for_timeout(100);assert 'LATE-SECRET' not in page.locator('body').inner_text()
  mode['hold']=False;mode['exportHold']=True
  downloads=[];page.on('download',lambda d:downloads.append(d))
  page.get_by_role('button',name='PDF 中文',exact=True).click()
  for _ in range(50):
   page.wait_for_timeout(20)
   if held:break
  assert held
  page.evaluate("location.hash='#/report?case=CASE-B&report=R2'")
  page.wait_for_timeout(100);held.pop().fulfill(body=b'synthetic old PDF',headers={'Content-Type':'application/pdf'})
  page.wait_for_timeout(100);assert not downloads
  mode['exportHold']=False
  page.evaluate("location.hash='#/report?case=CASE-A&report=R2'")
  page.get_by_text('SECRET-R2 / Synthetic',exact=True).first.wait_for()
  mode['write']=True
  page.get_by_role('button',name='📄 生成双语报告',exact=True).click()
  for _ in range(50):
   page.wait_for_timeout(20)
   if held:break
  assert held
  page.get_by_label('报告案件',exact=True).select_option('CASE-B')
  page.wait_for_timeout(150);held.pop().fulfill(json=report(rid='CREATED-LATE',text='WRITE-LATE'));page.wait_for_timeout(100)
  assert 'CASE-B' in page.url and 'CREATED-LATE' not in page.url and 'WRITE-LATE' not in page.locator('body').inner_text()
  mode['audit403']=True
  page.evaluate("location.hash='#/report?case=CASE-A&report=R2&lang=zh'")
  page.get_by_text('审计未获读取或读取失败',exact=False).wait_for();assert page.get_by_text('SECRET-R2 / Synthetic',exact=True).count()>0
  browser.close()
 print('W16.2 browser: dynamic cases, identity clear/403, late same-case GET, late dispatched write/download, independent audit denial passed (API doubles)')
finally:os.killpg(server.pid,signal.SIGTERM);server.wait()
