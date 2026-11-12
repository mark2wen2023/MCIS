"""Synthetic frontend lifecycle API doubles, not backend atomic-write acceptance."""
import subprocess,time,urllib.request,os,signal,json,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];proc=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15184','--strictPort'],cwd=ROOT/'web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
try:
 for _ in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:15184',timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1440,'height':1100});documents={};requests={};posted=[];mode=['ok']
  def envelope(case,doc):return {'profile':'MCIS-HFACS-DRAFT-1','caseId':case,'document':doc,'sourceStatus':'unchanged' if doc else 'none','persisted':doc is not None,'identityMode':'local-role-header'}
  def route(r):
   url=r.request.url
   if '/hfacs:' in url:
    case=url.split('/cases/')[1].split('/')[0];role=r.request.headers.get('x-mcis-role')
    if role=='Public':r.fulfill(status=403,json={});return
    if url.endswith(':context'):r.fulfill(json={'profile':'MCIS-HFACS-DRAFT-1','caseId':case,'taxonomyVersion':'mcis-hfacs-project/1','categories':[{'code':'UA','name':'Synthetic grouping','layer':'UnsafeActs','parentCode':None,'isLeaf':False}],'sources':[],'writeAllowed':True,'identityMode':'local-role-header','sourceBinding':'registered-metadata-only'});return
    if url.endswith(':draft'):r.fulfill(json=envelope(case,documents.get(case)));return
    if url.endswith(':audit'):r.fulfill(status=403,json={});return
    body=r.request.post_data_json;posted.append(body)
    if mode[0]=='conflict':r.fulfill(status=409,json={});return
    if mode[0]=='503':r.fulfill(status=503,json={});return
    if body['requestId'] in requests:r.fulfill(json=requests[body['requestId']]);return
    old=documents.get(case);draft=body['draft'];doc={'caseId':case,'revision':(old['revision'] if old else 0)+1,'draft':draft,'sources':body['expectedSources'],'classification':{'coreVersion':'mcis-hfacs/1','taxonomyVersion':'mcis-hfacs-project/1','entries':[{'id':e['id'],'categoryCode':e['categoryCode'],'layer':'UnsafeActs','description':e['description'],'strength':'ToBeVerified','reviewStatus':'Draft','origin':'Investigator'} for e in draft['entries']]},'status':'Draft','strength':'ToBeVerified','origin':'Investigator','savedBy':'调查员 A','savedRole':'Investigator','savedUtc':'2026-11-12T00:00:00Z'}
    doc['digest']=hashlib.sha256(json.dumps({k:doc[k] for k in ['caseId','revision','draft','sources','classification']},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest();documents[case]=doc;response=envelope(case,doc);requests[body['requestId']]=response
    if mode[0]=='unknown':r.abort('failed');return
    r.fulfill(json=response);return
   r.fulfill(status=403,json={})
  page.route('**/api/v1/**',route);page.goto('http://127.0.0.1:15184/#/hf?case=A');page.get_by_role('button',name='人工分类草稿（可保存）',exact=True).click();page.get_by_label('调查范围 / 工作任务情境',exact=True).wait_for();assert page.get_by_label('调查范围 / 工作任务情境',exact=True).input_value()==''
  page.get_by_label('调查范围 / 工作任务情境',exact=True).fill('Synthetic task scope');page.get_by_role('button',name='添加人工条目',exact=True).click();page.get_by_label('条目 ID 1',exact=True).fill('F1');page.get_by_label('项目分类 1',exact=True).select_option('UA');assert '分组/根类别草稿' in page.get_by_label('项目分类 1',exact=True).inner_text();page.get_by_label('情境描述 1',exact=True).fill('Synthetic description');page.get_by_label('人工分类理由 1',exact=True).fill('Synthetic hypothesis rationale')
  save=page.get_by_role('button',name='保存人工分类草稿',exact=True);mode[0]='unknown';save.click();page.get_by_role('button',name='重试同一保存请求',exact=False).wait_for();page.get_by_text('请求失败或响应无法核验',exact=False).wait_for();assert page.get_by_label('情境描述 1',exact=True).is_disabled()
  mode[0]='ok';page.get_by_role('button',name='重试同一保存请求',exact=False).click();page.get_by_text('已核验此请求的保存回执',exact=False).wait_for();assert posted[0]==posted[1];assert documents['A']['revision']==1
  page.get_by_role('button',name='重新打开服务端草稿',exact=False).click();page.get_by_label('情境描述 1',exact=True).wait_for();assert page.get_by_label('情境描述 1',exact=True).input_value()=='Synthetic description'
  out=ROOT/'logs/w184-ui-self';out.mkdir(parents=True,exist_ok=True);page.screenshot(path=str(out/'hfacs-reopened.png'),full_page=True)
  page.get_by_label('情境描述 1',exact=True).fill('Changed hypothetical description');mode[0]='503';save.click();page.get_by_text('服务暂不可用或保存状态未确认',exact=False).wait_for();assert page.get_by_label('情境描述 1',exact=True).is_disabled();failed_body=posted[-1];mode[0]='ok';page.get_by_role('button',name='重试同一保存请求',exact=False).click();page.get_by_text('已核验此请求的保存回执',exact=False).wait_for();assert posted[-1]==failed_body;assert documents['A']['revision']==2
  page.get_by_label('情境描述 1',exact=True).fill('Conflict edit');mode[0]='conflict';save.click();page.get_by_text('已停止保存，不会自动覆盖',exact=False).wait_for();assert documents['A']['revision']==2
  page.get_by_role('button',name='读取审计摘要',exact=True).click();page.get_by_text('当前身份或案件策略不允许',exact=False).wait_for()
  page.evaluate("location.hash='/hf?case=B'");page.get_by_role('button',name='人工分类草稿（可保存）',exact=True).click();page.get_by_label('调查范围 / 工作任务情境',exact=True).wait_for();assert page.get_by_label('调查范围 / 工作任务情境',exact=True).input_value()==''
  page.locator('select[title="X-MCIS-Role"]').select_option('Public');page.get_by_role('button',name='人工分类草稿（可保存）',exact=True).click();page.get_by_text('当前身份或案件策略不允许',exact=False).wait_for();assert page.get_by_label('调查范围 / 工作任务情境',exact=True).count()==0
  browser.close()
 print('W18.4 browser passed: blank/group taxonomy/save unknown frozen/same request retry/reopen/conflict no overwrite/audit denied/case identity isolation; API doubles only')
finally:os.killpg(proc.pid,signal.SIGTERM);proc.wait()
