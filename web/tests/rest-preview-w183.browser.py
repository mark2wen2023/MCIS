"""Frontend lifecycle test with explicit API doubles, not core/backend acceptance."""
import subprocess,time,urllib.request,os,signal,json,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];p=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15883','--strictPort'],cwd=ROOT/'web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
source={'evidenceId':'E1','title':'Synthetic registered metadata','sha256':'a'*64}
response={'profile':'MCIS-REST-PREVIEW-1','caseId':'A','inputSha256':'b'*64,'sources':[source],'sourceBinding':'registered-metadata-only','persisted':False,'assessment':'technical-preview-only','result':{'coreVersion':'mcis-rest/1','mode':'rest-baseline-no-exceptions','totals':{'restHours':8,'workHours':0,'unknownHours':16},'coverage':{'recordHours':24,'has24hWindow':True,'has7dWindow':False,'unknownHours':16},'findings':[],'insufficientData':[],'assumptions':['synthetic test assumption']},'limitations':['synthetic lifecycle test response']}
try:
 for _ in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:15883',timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox']);page=browser.new_page(viewport={'width':1440,'height':1100});pending=[];mode=['ok'];posts=[]
  def route(r):
   url=r.request.url
   if '/rest:sources' in url:
    case=url.split('/cases/')[1].split('/')[0]
    if r.request.headers.get('x-mcis-role')=='Public':r.fulfill(status=403,json={});return
    r.fulfill(json={'profile':'MCIS-REST-PREVIEW-1','caseId':case,'sources':[] if case=='EMPTY' else [source],'sourceBinding':'registered-metadata-only'});return
   if '/rest:preview' in url:
    body=r.request.post_data_json;posts.append(body)
    binding={'caseId':url.split('/cases/')[1].split('/')[0],'schedule':{k:body[k] for k in ['recordStartUtc','recordEndUtc','intervals']},'sources':[source]}
    response['inputSha256']=hashlib.sha256(json.dumps(binding,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if mode[0]=='delay':pending.append(r);return
    if mode[0]=='503':r.fulfill(status=503,json={});return
    r.fulfill(json=response);return
   r.fulfill(json=[])
  page.route('**/api/v1/**',route);page.goto('http://127.0.0.1:15883/#/hf?case=A')
  page.get_by_label('记录起点 UTC',exact=True).wait_for();assert page.get_by_label('记录起点 UTC',exact=True).input_value()==''
  def fill():
   page.get_by_label('记录起点 UTC',exact=True).fill('2026-11-12T00:00:00Z');page.get_by_label('记录终点 UTC',exact=True).fill('2026-11-13T00:00:00Z')
   page.get_by_label('开始 UTC 1',exact=True).fill('2026-11-12T00:00:00Z');page.get_by_label('结束 UTC 1',exact=True).fill('2026-11-12T08:00:00Z');page.get_by_label('类型 1',exact=True).select_option('Rest');page.get_by_role('checkbox',name='E1').check();page.get_by_role('checkbox',name='我理解这是').check()
  fill();page.get_by_role('button',name='运行技术预览（不保存）',exact=True).click();page.get_by_role('heading',name='工休技术预览 · 未保存',exact=True).wait_for();assert len(posts)==1
  page.get_by_label('结束 UTC 1',exact=True).fill('2026-11-12T09:00:00Z');assert page.get_by_role('heading',name='工休技术预览 · 未保存',exact=True).count()==0
  page.get_by_label('结束 UTC 1',exact=True).fill('2026-11-12T08:00:00Z');page.get_by_role('checkbox',name='我理解这是').check();mode[0]='delay';page.get_by_role('button',name='运行技术预览（不保存）',exact=True).click();page.get_by_text('正在请求真实计算核心',exact=False).wait_for()
  page.get_by_label('结束 UTC 1',exact=True).fill('2026-11-12T09:00:00Z')
  for r in pending:
   try:r.fulfill(json=response)
   except Exception:pass
  page.wait_for_timeout(100);assert page.get_by_role('heading',name='工休技术预览 · 未保存',exact=True).count()==0
  mode[0]='503';page.get_by_role('checkbox',name='我理解这是').check();page.get_by_role('button',name='运行技术预览（不保存）',exact=True).click();page.get_by_role('alert').wait_for();assert '计算核心暂不可用' in page.get_by_role('alert').inner_text()
  page.evaluate("location.hash='/hf?case=B'");page.get_by_label('记录起点 UTC',exact=True).wait_for();assert page.get_by_label('记录起点 UTC',exact=True).input_value()==''
  page.locator('select[title="X-MCIS-Role"]').select_option('Public');page.get_by_role('alert').wait_for();assert page.get_by_label('记录起点 UTC',exact=True).count()==0
  page.locator('select[title="X-MCIS-Role"]').select_option('Investigator');page.evaluate("location.hash='/hf?case=EMPTY'");page.get_by_text('本案暂无允许绑定',exact=False).wait_for();assert page.get_by_role('button',name='运行技术预览（不保存）',exact=True).is_disabled()
  out=ROOT/'logs/w183-ui-self';out.mkdir(parents=True,exist_ok=True);page.screenshot(path=str(out/'rest-empty.png'),full_page=True);browser.close()
 print('W18.3 Chromium passed: blank input, explicit source, preview, edit invalidation, late-response suppression,503,no-source,case/identity clearing. API doubles only.')
finally:os.killpg(p.pid,signal.SIGTERM);p.wait()
