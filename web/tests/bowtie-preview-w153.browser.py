"""Frontend lifecycle tests with explicit API doubles; not core acceptance."""
import subprocess,time,urllib.request,os,signal,json,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];server=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15153','--strictPort'],cwd=ROOT/'web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
try:
 for _ in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:15153',timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1440,'height':1000});pending=[];mode=['ok'];posts=[]
  def route(r):
   url=r.request.url
   if '/bowtie:' in url:
    case=url.split('/cases/')[1].split('/')[0]
    if r.request.headers.get('x-mcis-role')=='Public':r.fulfill(status=403,json={});return
    if url.endswith(':sources'):r.fulfill(json={'profile':'MCIS-BOWTIE-PREVIEW-1','caseId':case,'sources':[],'sourceBinding':'registered-metadata-only','identityMode':'local-role-header'});return
    body=r.request.post_data_json;posts.append(body);binding={'caseId':case,'model':body['model'],'sources':[]};sha=hashlib.sha256(json.dumps(binding,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    response={'profile':'MCIS-BOWTIE-PREVIEW-1','caseId':case,'inputSha256':sha,'sources':[],'sourceRole':'Investigator','sourceBinding':'registered-metadata-only','persisted':False,'assessment':'hypothesis-structure-only','result':{'coreVersion':'mcis-bowtie/1','mode':'hypothesis-structure-only','constructionErrors':[],'validationIssues':[{'code':'sys_empty_model','elementId':body['model']['topEvent']['id'],'message':'Synthetic empty model','severity':'Error'}],'structureValid':False,'notCheckedRefCount':0,'nodeCount':len(body['model']['nodes'])+1,'edgeCount':len(body['model']['edges'])},'limitations':['Synthetic lifecycle response']}
    if mode[0]=='delay':pending.append((r,response));return
    if mode[0]=='503':r.fulfill(status=503,json={});return
    if mode[0]=='hash':response['inputSha256']='f'*64
    r.fulfill(json=response);return
   r.fulfill(json=[])
  page.route('**/api/v1/**',route);page.goto('http://127.0.0.1:15153/#/systemic?case=A');page.get_by_label('顶事件 ID',exact=True).wait_for();assert page.get_by_label('顶事件 ID',exact=True).input_value()==''
  page.get_by_label('危险源',exact=False).fill('Synthetic hazard');page.get_by_label('顶事件 ID',exact=True).fill('TOP');page.get_by_label('顶事件描述',exact=True).fill('Synthetic loss of control')
  run=page.get_by_role('button',name='运行结构核查（不保存）',exact=True);run.click();page.get_by_role('heading',name='核心结构核查结果 · 非事实确认',exact=True).wait_for();assert posts[0]['sourceEvidenceIds']==[]
  page.get_by_role('button',name='定位相关输入',exact=True).click();assert page.locator('#w153-top').evaluate('(e)=>document.activeElement===e')
  page.get_by_role('button',name='添加节点',exact=True).click();assert page.get_by_role('heading',name='核心结构核查结果 · 非事实确认',exact=True).count()==0
  page.get_by_label('节点 ID 1',exact=True).fill('T');page.get_by_label('节点名称 1',exact=True).fill('Synthetic threat')
  page.get_by_role('button',name='添加连线',exact=True).click();page.get_by_label('起点 ID 1',exact=True).fill('T');page.get_by_label('终点 ID 1',exact=True).fill('TOP')
  mode[0]='delay';run.click();page.get_by_text('等待真实核心',exact=False).wait_for();page.get_by_label('节点名称 1',exact=True).fill('Changed threat')
  for r,response in pending:
   try:r.fulfill(json=response)
   except Exception:pass
  page.wait_for_timeout(100);assert page.get_by_role('heading',name='核心结构核查结果 · 非事实确认',exact=True).count()==0
  mode[0]='hash';run.click();page.get_by_role('alert').wait_for();assert page.get_by_role('heading',name='核心结构核查结果 · 非事实确认',exact=True).count()==0
  mode[0]='503';run.click();page.get_by_role('alert').wait_for();assert '计算核心暂不可用' in page.get_by_role('alert').inner_text()
  page.evaluate("location.hash='/systemic?case=B'");page.get_by_label('顶事件 ID',exact=True).wait_for();assert page.get_by_label('顶事件 ID',exact=True).input_value()==''
  page.locator('select[title="X-MCIS-Role"]').select_option('Public');page.get_by_role('alert').wait_for();assert page.get_by_label('顶事件 ID',exact=True).count()==0
  page.locator('select[title="X-MCIS-Role"]').select_option('Investigator');page.get_by_label('顶事件 ID',exact=True).wait_for()
  out=ROOT/'logs/w153-ui-self';out.mkdir(parents=True,exist_ok=True);page.screenshot(path=str(out/'bowtie-empty.png'),full_page=True);browser.close()
 print('W15.3 browser lifecycle passed: blank,zero-source,diagnostic focus,edit/late suppression,hash mismatch,503,case/identity clear. API doubles only.')
finally:os.killpg(server.pid,signal.SIGTERM);server.wait()
