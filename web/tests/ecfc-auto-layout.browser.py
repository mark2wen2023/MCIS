"""One real sandboxed Chrome pass over the existing candidate ECFC editor: load a synthetic saved draft
(API doubles, loopback only), preview (persisted:false), press the explicit auto-layout control once.
Zero write: any save POST fails the run. Not real-service or professional acceptance; not W11 whole package."""
import hashlib,json,os,subprocess,sys,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];OUT=Path(os.environ.get('MCIS_EVIDENCE_DIR','/tmp/ecfc-auto-layout-out'));OUT.mkdir(parents=True,exist_ok=True)
CHROME=os.environ.get('MCIS_BROWSER_BIN','/opt/google/chrome/google-chrome');PORT=15874;BASE=f'http://127.0.0.1:{PORT}'
PROFILE='MCIS-ECFC-DRAFT-1';HEADERS={'Cache-Control':'no-store','Content-Type':'application/json'};CID='SYNTHETIC-A'
SRC=[{'evidenceId':'EV-001','title':'合成证据（非真实案卷）','sha256':'0'*64}]
def ev(i,lane=0,t=None,evid=()):return {'id':i,'kind':'Event','text':f'合成事件 {i}','timeSeconds':t,'lane':lane,'isPrimaryIncident':i=='A','evidenceIds':list(evid)}
DRAFT={'scope':'合成未定时 Z→A 布局验收','nodes':[ev('A',0,None,['EV-001']),ev('M'),ev('Z'),ev('S',1),{'id':'C1','kind':'Condition','text':'合成条件 C1','timeSeconds':None,'lane':-1,'isPrimaryIncident':False,'evidenceIds':[]}],'edges':[{'id':'e1','from':'Z','to':'M'},{'id':'e2','from':'M','to':'A'},{'id':'e3','from':'S','to':'A'},{'id':'e4','from':'C1','to':'M'}]}
def validation(d):
 by={n['id']:n for n in d['nodes']}
 return {'coreVersion':'mcis-ecfc-draft/1','nodes':[{**n,'isPresumptive':True} for n in d['nodes']],'edges':[{**e,'kind':'Sequence' if by[e['from']]['kind']=='Event' else 'Influence','bold':by[e['from']]['kind']=='Event' and by[e['from']]['lane']==0 and by[e['to']]['lane']==0} for e in d['edges']],'issues':[]}
DOC={'caseId':CID,'revision':1,'digest':'1'*64,'draft':DRAFT,'sources':SRC,'validation':validation(DRAFT),'status':'Draft','strength':'ToBeVerified','origin':'Investigator','savedBy':'Synthetic UI','savedRole':'LeadInvestigator','savedUtc':'2026-11-28T09:00:00Z'}
receipt={'chrome':CHROME,'sandbox':'default (no --no-sandbox)','base':BASE,'requests':[],'blocked':[],'console':[],'pageerrors':[],'posts':{'preview':0,'save':0},'checks':{}}
log=open(OUT/'browser.log','w')
server=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',str(PORT),'--strictPort'],cwd=ROOT/'web',stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
code=1
try:
 for _ in range(150):
  try:urllib.request.urlopen(BASE,timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=CHROME,headless=True,chromium_sandbox=True)
  receipt['browserVersion']=browser.version
  page=browser.new_page(viewport={'width':1280,'height':900});page.set_default_timeout(10000)
  page.add_init_script("localStorage.setItem('mcis.role','LeadInvestigator');localStorage.setItem('mcis.operator','Synthetic UI')")
  page.on('console',lambda m:receipt['console'].append(f'{m.type}: {m.text}'));page.on('pageerror',lambda e:receipt['pageerrors'].append(str(e)))
  def guard(r):
   u=r.request.url
   if u.startswith(BASE+'/'):r.continue_();return
   receipt['blocked'].append(u);r.abort()
  page.route('**/*',guard)
  def fulfill(r,v,s=200):r.fulfill(status=s,body=json.dumps(v,ensure_ascii=False),headers=HEADERS)
  def api(r):
   action=r.request.url.rsplit('/',1)[1];receipt['requests'].append(f'{r.request.method} {action}')
   if action=='context':fulfill(r,{'profile':PROFILE,'caseId':CID,'sources':SRC,'writeAllowed':True,'identityMode':'local-role-header','sourceBinding':'registered-metadata-only','archiveSupported':False})
   elif action=='draft' and r.request.method=='GET':fulfill(r,{'profile':PROFILE,'caseId':CID,'document':DOC,'sourceStatus':'unchanged','persisted':True,'identityMode':'local-role-header'})
   elif action=='preview':
    receipt['posts']['preview']+=1;b=r.request.post_data_json;receipt['previewDraftEqualsSaved']=b['draft']==DRAFT
    fulfill(r,{'profile':PROFILE,'caseId':CID,'draft':b['draft'],'validation':validation(b['draft']),'persisted':False})
   else:receipt['posts']['save']+=1;fulfill(r,{'code':'SYNTHETIC_NO_WRITE'},403)
  page.route(f'{BASE}/api/v1/cases/**/ecfc/*',api)
  page.goto(BASE+'/tests/ecfc-harness.html')
  page.get_by_role('button',name='预览结构与方法提示（不保存）',exact=True).click()
  svg=page.get_by_role('img',name='人工 ECFC 假设示意图');svg.wait_for()
  pos=lambda:page.eval_on_selector_all('svg[aria-label="人工 ECFC 假设示意图"] g[data-node-id]','gs=>Object.fromEntries(gs.map(g=>[g.dataset.nodeId,[+g.dataset.x,+g.dataset.y]]))')
  dom=lambda:page.eval_on_selector_all('svg[aria-label="人工 ECFC 假设示意图"] g title','ts=>ts.map(t=>t.textContent)')
  before,titles_before=pos(),dom()
  page.screenshot(path=str(OUT/'01-before-schematic.png'),full_page=True);svg.screenshot(path=str(OUT/'01b-before-graph.png'))
  btn=page.get_by_role('button',name='自动布局（仅调整显示坐标）',exact=True);btn.click()
  page.get_by_role('button',name='恢复输入顺序示意布局',exact=True).wait_for()
  after,titles_after=pos(),dom()
  page.screenshot(path=str(OUT/'02-after-auto-layout.png'),full_page=True);svg.screenshot(path=str(OUT/'02b-after-graph.png'))
  status=page.get_by_role('status').filter(has_text='本地自动布局').inner_text()
  pending=page.locator('ul[aria-label="布局待核"]').count()
  c=receipt['checks']
  c['beforeInputOrder_A_M_Z']=before['A'][0]<before['M'][0]<before['Z'][0]
  c['afterTopological_Z_M_A']=after['Z'][0]<after['M'][0]<after['A'][0] and after['Z'][1]==after['M'][1]==after['A'][1]
  c['secondaryS_alignedWithA']=after['S'][0]==after['A'][0] and after['S'][1]!=after['A'][1]
  c['conditionC1_atM_above']=after['C1'][0]==after['M'][0] and after['C1'][1]<after['M'][1]
  c['nodeTitlesUnchanged']=titles_before==titles_after
  c['noPendingShown']=pending==0
  c['zeroSave']=receipt['posts']['save']==0
  c['noPageErrors']=not receipt['pageerrors']
  receipt.update(before=before,after=after,statusText=status)
  browser.close()
 code=0 if all(receipt['checks'].values()) and receipt.get('previewDraftEqualsSaved') else 1
except Exception as e:
 receipt['exception']=repr(e);code=1
finally:
 os.killpg(server.pid,15);server.wait(10);log.close()
 receipt['exitCode']=code
 for f in sorted(OUT.glob('*.png')):receipt.setdefault('files',{})[f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
 (OUT/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=1))
 print(json.dumps(receipt['checks'],ensure_ascii=False));print('EXIT',code)
sys.exit(code)
