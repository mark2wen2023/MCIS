"""Independent W12.2 UI acceptance. Real Vite/Chromium, synthetic intercepted API.
No backend correctness claim: server/C# acceptance is separate. Only loopback used.
"""
import copy,json,os,signal,subprocess,time,urllib.request
from pathlib import Path
from datetime import datetime,timedelta,timezone
from urllib.parse import urlparse,parse_qs
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
PORT=15942
URL=f'http://127.0.0.1:{PORT}'
OUT=Path('/tmp/w122-independent');OUT.mkdir(exist_ok=True)
E='2026-01-01T00:00:00Z'
CID='ACCEPT-ONLY-NONFICTION-FLAG'
case={'caseId':CID,'title':'Synthetic acceptance fixture, non-fiction flag exercise only','isFictionalDemo':False,'caseEpochUtc':E}
vessels=[{'caseId':CID,'vesselId':v,'name':'Fixture '+v} for v in ['A','B']]
def data(n=2501):
 rows=[]
 for i in range(n):
  utc=(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(seconds=i)).isoformat().replace('+00:00','Z')
  a={'vesselId':'A','timeSec':i,'utc':utc,'latDeg':0,'lonDeg':0,'sogKn':10,'cogDeg':90,'source':'<script>window.INJECTED=1</script> independent acceptance only'}
  if i%5<4:a['provenance']=['Measured','Interpolated','ManualDrawn','Simulated'][i%5]
  b={**a,'vesselId':'B','lonDeg':.01,'sogKn':0};b.pop('source')
  rows.append({'timeSec':i,'utc':utc,'own':a,'target':b,'currentDistanceNm':.6,'dcpaNm':.1,'tcpaMin':0 if i==0 else (None if i==1 else -1),'isDiverging':i!=1,'isDegenerate':i==1})
 return {**case,'profile':'MCIS-CURRENT-CPA-1','origin':{'latDeg':0,'lonDeg':0},'vessels':vessels,'window':{'fromSec':None,'toSec':None},'inputDigest':'b'*64,'coreVersion':'independent-ui-fixture' if n else None,'counts':{'own':n+1,'target':n+2,'matched':n,'unmatchedOwn':1,'unmatchedTarget':2},'rows':rows}
state={'mode':'good','held':[],'calls':0};passed=[]
log=open(OUT/'vite.log','w')
proc=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',str(PORT),'--strictPort'],cwd=ROOT/'web',stdout=log,stderr=log,start_new_session=True)
try:
 for _ in range(150):
  try:urllib.request.urlopen(URL,timeout=.5);break
  except Exception:time.sleep(.1)
 else:raise AssertionError('Vite unavailable')
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  p=browser.new_page(viewport={'width':1440,'height':1000});p.set_default_timeout(12000)
  p.add_init_script("localStorage.setItem('mcis.role','LeadInvestigator')")
  errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
  def intercept(route):
   u=urlparse(route.request.url)
   if u.hostname!='127.0.0.1':route.abort();return
   path=u.path
   if not path.startswith('/api/'):route.continue_();return
   response={};status=200
   if '/analysis/current' in path:
    state['calls']+=1
    if state['mode']=='hold':state['held'].append(route);return
    if state['mode']=='error':status=502;response={'code':'ANALYSIS_CORE_OUTPUT','message':'计算核心无效，独立验收错误态'}
    elif state['mode']=='deny':status=403;response={'code':'DENIED','message':'Forbidden'}
    else:
     response=data(0 if state['mode']=='empty' else 2501)
     if state['mode']=='wrong-case':response['caseId']='OTHER-CASE'
     if state['mode']=='wrong-count':response['counts']['matched']=2500
     if state['mode']=='wrong-window':response['window']['fromSec']=1
   elif path.endswith('/vessels'):response=[] if 'NO-SHIPS' in path else vessels
   elif path.endswith('/'+CID):response=case
   elif path.endswith('/NO-SHIPS'):response={**case,'caseId':'NO-SHIPS'}
   elif path.endswith('/UNKNOWN'):status=404;response={'code':'NOT_FOUND','message':'案件不存在（独立验收）'}
   elif path.endswith('/analysis/cases'):response={'cases':[]}
   elif path.endswith('/analysis'):status=404;response={'code':'NO_REFERENCE','message':'此案无历史基准'}
   else:response=[]
   route.fulfill(status=status,content_type='application/json',body=json.dumps(response))
  p.route('**/*',intercept)
  def open_case(cid=CID):
   p.goto(URL+'/#/analysis?case='+cid)
  def select():
   p.get_by_label('本船',exact=True).select_option('A');p.get_by_label('目标船',exact=True).select_option('B')
  def calc():p.get_by_role('button',name='计算同刻已存点',exact=True).click()
  panel=p.get_by_role('region',name='当前案计算结果')
  def ready():panel.wait_for()
  def release():
   for r in state['held']:
    try:r.fulfill(status=200,content_type='application/json',body=json.dumps(data()))
    except Exception:pass # Aborted requests may already have lost their browser route.
   state['held'].clear();p.wait_for_timeout(200)
  def hold():
   state['mode']='hold';calc()
   for _ in range(100):
    p.wait_for_timeout(20)
    if state['held']:break
   assert state['held']
  open_case();select();before=state['calls']
  p.get_by_role('button',name='计算同刻已存点',exact=True).evaluate('(b)=>{b.click();b.click();b.click()}');ready()
  assert state['calls']==before+1
  text=panel.inner_text()
  for label in ['记录为实测','记录为插值','记录为手绘','记录为仿真','未提供来源类型','来源标签未提供','核心标记已远离','不适用','2000 / 2501','均匀展示抽样'] :assert label in text,label
  assert '非虚构标记不等于资料已核验' in p.locator('.w122-head').inner_text()
  assert '示例数据（虚构）' not in p.locator('.w122-head').inner_text()
  assert p.evaluate('window.INJECTED') is None
  assert panel.locator('tbody tr').count()==100
  for _ in range(25):panel.get_by_role('button',name='下一页').click()
  assert panel.locator('tbody tr').count()==1 and '26 / 26 页' in panel.inner_text()
  assert '2500' in panel.locator('tbody tr').inner_text()
  # Inspect the actual chart instance, rather than infer rendering from source.
  options=p.evaluate("""async()=>{const e=await import('/node_modules/.vite/deps/echarts.js');const el=document.querySelector('.w122-result [_echarts_instance_]');return e.getInstanceByDom(el).getOption().series.map(s=>({type:s.type,n:s.data.length}))}""")
  assert all(s['type']=='scatter' and s['n']<=2000 for s in options),options
  assert not any('rows' in x or 'inputDigest' in x for x in p.evaluate('Object.values(localStorage).concat(Object.values(sessionStorage))'))
  for w,h in [(1440,1000),(1920,1080)]:
   p.set_viewport_size({'width':w,'height':h});p.screenshot(path=str(OUT/f'ui-{w}.png'),full_page=True)
   assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
  passed.append('2501 results, 2000 scatter cap, 26-page complete table, 5 provenance states, escaping, non-fiction caveat, rounded-negative and degenerate TCPA, no raw storage, duplicate suppression, 1440/1920')
  # Input changes clear synchronously; invalid window must not send.
  p.get_by_label('起始相对秒',exact=True).fill('NaN');assert panel.count()==0
  n=state['calls'];calc();p.get_by_role('alert').wait_for();assert state['calls']==n
  p.get_by_label('起始相对秒',exact=True).fill('')
  for mode in ['wrong-case','wrong-count','wrong-window','error','deny']:
   state['mode']=mode;calc();p.get_by_role('alert').wait_for();assert panel.count()==0
  state['mode']='empty';calc();ready();assert '没有可配对同刻点' in panel.inner_text() and panel.locator('canvas').count()==0
  passed.append('input invalidation; invalid-window no request; wrong case/count/window response rejection; 502,403 and empty states')
  state['mode']='good';calc();ready();hold()
  p.evaluate("async()=>{const a=await import('/src/api.ts');a.setIdentity('Public','Acceptance new operator')}")
  release();assert panel.count()==0
  select();assert panel.count()==0
  passed.append('held response rejected after identity switch; old rows absent')
  state['mode']='good';calc();ready();hold()
  p.get_by_label('起始相对秒',exact=True).fill('1');release();assert panel.count()==0
  p.get_by_label('起始相对秒',exact=True).fill('');state['mode']='good';calc();ready();hold()
  p.evaluate("location.hash='#/analysis?case=NO-SHIPS'");p.get_by_text('本案不足两艘已登记船舶。先登记船舶并保存航迹，不会回退到虚构案例。',exact=True).wait_for();release();assert panel.count()==0
  p.go_back();select();assert panel.count()==0
  passed.append('held response rejected after input/case change; no-ships state; Back does not revive result')
  state['mode']='good';calc();ready();hold()
  p.get_by_role('link',name='打开历史冻结基准（非当前案计算）',exact=True).click();release();assert panel.count()==0
  p.get_by_role('link',name='返回当前案件已保存航迹分析',exact=True).click();select();assert panel.count()==0
  passed.append('reference-mode navigation rejects held current result and return does not revive it')
  state['mode']='good';calc();ready();hold()
  p.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide'))");release();assert panel.count()==0
  p.get_by_role('button',name='重新读取本案',exact=True).click();select();assert panel.count()==0
  open_case('UNKNOWN');p.get_by_role('alert').filter(has_text='案件不存在').wait_for();assert panel.count()==0
  passed.append('pagehide invalidation, reread requires new calculation; unknown case explicit error')
  assert not errors,errors
  browser.close()
 print(json.dumps({'passed':passed,'pageErrors':errors,'chartOptions':options},ensure_ascii=False,indent=2))
 (OUT/'result.json').write_text(json.dumps({'passed':passed,'pageErrors':errors,'chartOptions':options},ensure_ascii=False,indent=2))
finally:
 os.killpg(proc.pid,signal.SIGTERM);proc.wait();log.close()
