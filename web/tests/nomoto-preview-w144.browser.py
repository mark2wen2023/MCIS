"""Frontend lifecycle using explicit API doubles, not physics acceptance."""
import subprocess,time,urllib.request,os,signal,json,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];proc=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15144','--strictPort'],cwd=ROOT/'web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
try:
 for _ in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:15144',timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1440,'height':1100});mode=['ok'];pending=[];posts=[]
  def route(r):
   url=r.request.url
   if '/nomoto:' in url:
    case=url.split('/cases/')[1].split('/')[0]
    if r.request.headers.get('x-mcis-role')=='Public':r.fulfill(status=403,json={});return
    if url.endswith(':sources'):r.fulfill(json={'profile':'MCIS-NOMOTO-PREVIEW-1','caseId':case,'sources':[],'sourceBinding':'registered-metadata-only','identityMode':'local-role-header'});return
    body=r.request.post_data_json;posts.append(body);p=body['parameters'];binding={'caseId':case,'parameters':p,'sources':[]};sha=hashlib.sha256(json.dumps(binding,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest();point={'timeSeconds':0,'eastM':0,'northM':0,'headingDeg':float(p['headingDeg']),'speedKn':0,'rotDegPerSec':0,'rudderDeg':0}
    response={'profile':'MCIS-NOMOTO-PREVIEW-1','caseId':case,'inputSha256':sha,'sources':[],'sourceRole':'Investigator','sourceBinding':'registered-metadata-only','persisted':False,'assessment':'hypothetical-single-vessel-response','result':{'coreVersion':'mcis-nomoto/1','mode':'fixed-rudder-hypothesis','stepSeconds':.1,'comparisonStepSeconds':.05,'baseline':[point,{**point,'timeSeconds':1}],'response':[point,{**point,'timeSeconds':1,'rudderDeg':2}],'numericalDifference':{'endpointDistanceM':0,'endpointHeadingDifferenceDeg':0,'endpointRotDifferenceDegPerSec':0},'assumptions':['Synthetic UI response']},'limitations':['API double not physics validation']}
    if mode[0]=='delay':pending.append((r,response));return
    if mode[0]=='503':r.fulfill(status=503,json={});return
    if mode[0]=='hash':response['inputSha256']='f'*64
    r.fulfill(json=response);return
   r.fulfill(json=[])
  page.route('**/api/v1/**',route);page.goto('http://127.0.0.1:15144/#/whatif?case=A');page.get_by_label('初始航向',exact=False).wait_for();assert page.get_by_label('初始航向',exact=False).input_value()==''
  for label,value in [('初始航向','0'),('固定速度','0'),('K（','0.1'),('T（','10'),('参考速度','5'),('最大舵角','35'),('舵速','2'),('固定舵令（','10'),('时长','1'),('参数来源说明','Synthetic'),('不确定性说明','Not calibrated')]:page.get_by_label(label,exact=False).fill(value)
  run=page.get_by_role('button',name='运行单船假设预览（不保存）',exact=True);run.click();page.get_by_role('heading',name='单船假设响应 · 未保存',exact=True).wait_for();assert isinstance(posts[0]['parameters']['k'],str)
  page.get_by_label('不确定性说明',exact=False).fill('Changed note');assert page.get_by_role('heading',name='单船假设响应 · 未保存',exact=True).count()==0
  mode[0]='delay';run.click();page.get_by_text('等待真实计算',exact=False).wait_for();page.get_by_label('不确定性说明',exact=False).fill('Changed again')
  for r,response in pending:
   try:r.fulfill(json=response)
   except Exception:pass
  page.wait_for_timeout(100);assert page.get_by_role('heading',name='单船假设响应 · 未保存',exact=True).count()==0
  mode[0]='hash';run.click();page.get_by_role('alert').wait_for();assert page.get_by_role('heading',name='单船假设响应 · 未保存',exact=True).count()==0
  mode[0]='503';run.click();page.get_by_role('alert').wait_for();assert '计算核心暂不可用' in page.get_by_role('alert').inner_text()
  page.evaluate("location.hash='/whatif?case=B'");page.get_by_label('初始航向',exact=False).wait_for();assert page.get_by_label('初始航向',exact=False).input_value()==''
  page.locator('select[title="X-MCIS-Role"]').select_option('Public');page.get_by_role('alert').wait_for();assert page.get_by_label('初始航向',exact=False).count()==0
  page.locator('select[title="X-MCIS-Role"]').select_option('Investigator');page.get_by_label('初始航向',exact=False).wait_for();out=ROOT/'logs/w144-ui-self';out.mkdir(parents=True,exist_ok=True);page.screenshot(path=str(out/'nomoto-empty.png'),full_page=True);browser.close()
 print('W14.4 browser passed blank/string inputs, equal-scale chart rendered, input and late response invalidation,hash mismatch,503,case/identity clearing; API doubles only')
finally:os.killpg(proc.pid,signal.SIGTERM);proc.wait()
