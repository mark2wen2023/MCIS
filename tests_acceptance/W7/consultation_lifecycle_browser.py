"""Local-only W7.2 browser acceptance; requires frozen implementation and official headless shell.
Runs isolated disposable service data, Vite build/preview and browser on 127.0.0.1.
Screenshots remain local and are never uploaded. Not mobile/production/Unity acceptance.
"""
from pathlib import Path
from urllib.parse import urlparse
import hashlib
import os, socket, subprocess, time, urllib.request, urllib.error, tempfile, signal, json, traceback
from playwright.sync_api import sync_playwright, expect
ROOT=Path(os.environ.get('MCIS_REPO',str(Path(__file__).resolve().parents[2]))).resolve()
OUT=Path(os.environ['MCIS_BROWSER_OUT']).resolve(); OUT.mkdir(parents=True,exist_ok=False)
BINARY=os.environ['MCIS_BROWSER_EXECUTABLE']; DOTNET=os.environ['MCIS_DOTNET']
PYTHON=str(ROOT/'service/.venv/bin/python')
OTHER='CASE-2026-DEMO-LILY-MARY'; CASE='CJK-2024-1230-YangZe22-VegaDream'
def port():
 with socket.socket() as s: s.bind(('127.0.0.1',0)); return s.getsockname()[1]
def wait(url):
 for _ in range(200):
  try:
   with urllib.request.urlopen(url,timeout=2):return
  except Exception:time.sleep(.15)
 raise RuntimeError('not ready '+url)
bp,fp=port(),port(); base=f'http://127.0.0.1:{fp}'; back=f'http://127.0.0.1:{bp}/api/v1'
data=Path(tempfile.mkdtemp(prefix='w72-data-'))
env=dict(os.environ,MCIS_DATA_DIR=str(data),MCIS_PORT=str(bp),MCIS_API=f'http://127.0.0.1:{bp}',MCIS_CORE=str(ROOT/'tests_acceptance/W6/mcis-core-norebuild.sh'),MCIS_CORE_DLL=str(ROOT/'tools/mcis-core/out/mcis-core.dll'))
env.pop('MCIS_DB_URL',None)
procs=[]; handles=[]; checks=[]; errors=[]; consoles=[]; http=[]; writes=[]; shots=[]; phase='setup'
def api(path,method='GET',body=None,role='LeadInvestigator'):
 b=None if body is None else json.dumps(body).encode()
 req=urllib.request.Request(back+path,data=b,method=method,headers={'X-MCIS-Role':role,'X-MCIS-Operator':'BrowserAcceptance','Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=15) as r:return json.load(r)
def cp(path):return '/cases/'+CASE+path
def start(cmd,cwd,name):
 f=open(OUT/name,'w');handles.append(f);procs.append(subprocess.Popen(cmd,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True))
def check(name,ok,detail=None):
 checks.append({'name':name,'passed':bool(ok),'detail':detail})
 if not ok:raise AssertionError(name)
freeze=(ROOT/'logs/w7.2-impl-hashes-frozen.txt').read_text();(OUT/'implementation-hashes.txt').write_text(freeze)
def frozen_ok():
 return all(hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha for sha,path in (line.split(maxsplit=1) for line in freeze.strip().splitlines()))
try:
 check('frozen implementation hashes before',frozen_ok())
 start([PYTHON,'-m','mcis_service'],ROOT/'service','backend.log');wait(back+'/health')
 subprocess.run(['npx','vite','build','--outDir',str(OUT/'dist'),'--emptyOutDir','--logLevel','error'],cwd=ROOT/'web',env=env,check=True,capture_output=True)
 start(['npx','vite','preview','--outDir',str(OUT/'dist'),'--host','127.0.0.1','--port',str(fp),'--strictPort'],ROOT/'web','frontend.log');wait(base)
 before=api(cp('/audit?category=Consultation')); before_seq=max([e['seq'] for e in before],default=0)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=BINARY,headless=True,args=['--no-sandbox','--disable-gpu'])
  page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
  external=[]
  def local_only(route):
   if urlparse(route.request.url).hostname not in ['127.0.0.1',None]:external.append(route.request.url);route.abort()
   else:route.continue_()
  page.route('**/*',local_only)
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda m:consoles.append({'phase':phase,'type':m.type,'text':m.text}) if m.type in ['error','warning'] else None)
  page.on('response',lambda r:http.append({'phase':phase,'status':r.status,'url':r.url,'role':r.request.headers.get('x-mcis-role')}) if r.status>=400 else None)
  page.on('request',lambda r:writes.append({'phase':phase,'method':r.method,'url':r.url,'body':r.post_data}) if r.method in ['POST','PATCH','PUT','DELETE'] else None)
  panel=page.locator('.w7-consultation')
  def ready():expect(panel.get_by_label('选择轮次')).to_be_visible();expect(panel.get_by_role('button',name='重新读取',exact=True)).to_be_enabled()
  def refresh():
   with page.expect_response(lambda r:'/consultation/rounds' in r.url and r.request.method=='GET'):
    panel.get_by_role('button',name='重新读取',exact=True).click()
   ready()
  def role(name):page.locator('.topbar select').select_option(name)
  def item(cid):return panel.locator('.w7-comment').filter(has=page.locator('strong',has_text=cid)).last
  def save(cid,decision,feedback=''):
   row=item(cid);row.get_by_label('采纳决定').select_option(decision)
   row.get_by_label('反馈理由',exact=False).fill(feedback)
   with page.expect_response(lambda r:r.request.method=='PATCH' and f'/comments/{cid}' in r.url) as result:row.get_by_role('button',name='保存决定').click()
   check('decision HTTP '+cid,result.value.status==200);ready();expect(item(cid).get_by_role('button',name='保存决定')).to_have_count(0)
  from datetime import datetime, timezone, timedelta
  import sqlite3
  lifecycle=panel.locator('.w7-lifecycle'); confirmation=panel.get_by_role('region',name='轮次操作确认')
  def readready():expect(panel.get_by_role('button',name='重新读取',exact=True)).to_be_enabled()
  def fillnew(version=' W72-v1 ',two=True,digest=''):
   panel.get_by_label('草案版本',exact=True).fill(version)
   panel.get_by_label('相关方编号',exact=True).nth(0).fill(' A ');panel.get_by_label('相关方名称',exact=True).nth(0).fill(' Fictional A ')
   if two:
    panel.get_by_role('button',name='添加相关方').click();panel.get_by_label('相关方编号',exact=True).nth(1).fill(' B ');panel.get_by_label('相关方名称',exact=True).nth(1).fill(' Fictional B ')
   panel.get_by_label('草案 SHA-256',exact=False).fill(digest)
  def preview(name):panel.get_by_role('button',name=name,exact=True).click();expect(confirmation).to_be_visible()
  def confirm(status,suffix,double=True):
   n=len(writes)
   with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith(suffix)) as response:
    confirmation.get_by_role('button',name='确认登记',exact=True).evaluate('(b)=>{b.click();b.click()}' if double else '(b)=>b.click()')
   check('HTTP '+str(status)+' '+suffix,response.value.status==status);readready();page.wait_for_timeout(100)
   check('single mutation '+suffix,len(writes)==n+1)
   return response.value.json()
  def rounds():return api(cp('/consultation/rounds'))
  def refresh_all():
   with page.expect_response(lambda r:r.request.method=='GET' and r.url.endswith('/consultation/rounds')):panel.get_by_role('button',name='重新读取',exact=True).click()
   readready()
  phase='normal';page.goto(base+'/#/recs?case='+CASE)
  expect(panel.get_by_text('暂无征求意见轮次',exact=False)).to_be_visible();expect(panel.get_by_label('草案版本')).to_be_visible()
  check('temporary case initially empty',rounds()==[])
  fillnew(two=True,digest='x'*64)
  panel.get_by_role('button',name='核对新建轮次').click();expect(lifecycle.get_by_role('alert')).to_be_visible();check('invalid hash prevents confirmation and write',confirmation.count()==0 and len(writes)==0)
  panel.get_by_label('草案 SHA-256',exact=False).fill('A'*64)
  panel.get_by_label('相关方编号',exact=True).nth(1).fill(' A ')
  panel.get_by_role('button',name='核对新建轮次').click();expect(lifecycle.get_by_role('alert')).to_be_visible();check('trimmed duplicate party blocks',confirmation.count()==0 and len(writes)==0)
  panel.get_by_label('相关方编号',exact=True).nth(1).fill(' B ');preview('核对新建轮次')
  check('preview warns local only irreversible',all(t in confirmation.inner_text() for t in ['不会向相关方发送消息','无删除/撤销接口','30天']))
  confirmation.get_by_role('button',name='返回修改').click();check('cancel creates no writes',not writes)
  preview('核对新建轮次');role('InterestedState');page.wait_for_timeout(100)
  check('RO clears new confirmation and forms',confirmation.count()==0 and panel.get_by_label('草案版本').count()==0)
  role('Investigator');expect(panel.get_by_label('草案版本')).to_have_value('')
  fillnew(two=True,digest='A'*64);preview('核对新建轮次')
  page.evaluate('(h)=>location.hash=h','#/recs?case='+OTHER);ready();check('case switch clears confirmation',confirmation.count()==0)
  page.evaluate('(h)=>location.hash=h','#/recs?case='+CASE);expect(panel.get_by_label('草案版本')).to_have_value('')
  fillnew(two=True,digest='A'*64);preview('核对新建轮次');created=confirm(201,'/consultation/rounds');ready()
  check('open trims and normalizes payload',created['draftVersion']=='W72-v1' and created['draftSha256']=='a'*64 and created['parties']==[{'partyId':'A','name':'Fictional A'},{'partyId':'B','name':'Fictional B'}],created)
  check('fixed default thirty days',datetime.fromisoformat(created['deadlineUtc'].replace('Z','+00:00'))-datetime.fromisoformat(created['openedUtc'].replace('Z','+00:00'))==timedelta(days=30) and not created['isAgreedDeadline'])
  phase='expected-conflict';preview('核对关闭本轮');confirm(409,'/rounds/1:close');expect(panel.get_by_role('alert')).to_contain_text('consultation_cannot_close');check('early close not persisted',not rounds()[0]['isClosed'])
  phase='normal';panel.get_by_label('回复方',exact=True).select_option('A');panel.get_by_label('回复正文',exact=True).fill('Fictional received response');panel.get_by_label('意见条目',exact=False).fill('Pending survives close')
  with page.expect_response(lambda r:r.request.method=='POST' and '/replies' in r.url):panel.get_by_role('button',name='登记回复',exact=True).click()
  expect(panel.get_by_label('放弃回复方')).to_have_value('B')
  panel.get_by_label('已确认放弃的依据/理由').fill('   ');check('blank waiver reason blocks',panel.get_by_role('button',name='核对放弃回复登记').is_disabled())
  panel.get_by_label('已确认放弃的依据/理由').fill('  Fictional written waiver received  ');preview('核对放弃回复登记')
  check('waiver preview consequence explicit','不能再登记该方回复' in confirmation.inner_text())
  n=len(writes);confirmation.get_by_role('button',name='返回修改').click();check('waiver cancel no mutation',len(writes)==n)
  preview('核对放弃回复登记');waived=confirm(201,'/rounds/1/waivers');ready()
  check('waiver persisted and all replied',waived['allReplied'] and waived['waivers'][0]['reason']=='Fictional written waiver received' and waived['comments'][0]['decision']=='Pending')
  preview('核对关闭本轮');closed=confirm(200,'/rounds/1:close');ready();check('close permits Pending opinions',closed['isClosed'] and closed['comments'][0]['decision']=='Pending')
  save('R1-C01','Adopted');page.reload();ready();check('first cycle persists',rounds()[0]['comments'][0]['decision']=='Adopted' and rounds()[0]['isClosed'])
  # Second creation commits successfully at service; intentionally lose only its response.
  fillnew('W72-v2',two=False);preview('核对新建轮次');committed=[];phase='expected-lost-response';n=len(writes)
  def lose_open(route):
   if route.request.method=='POST':
    response=route.fetch();check('actual create committed before response lost',response.status==201);committed.append(response.json());route.abort('failed')
   else:route.continue_()
  page.route('**/cases/'+CASE+'/consultation/rounds',lose_open)
  confirmation.get_by_role('button',name='确认登记').click();expect(panel.get_by_role('alert')).to_contain_text('结果未确认');expect(panel.get_by_label('选择轮次')).to_have_value('2')
  expect(page.locator('.p6-table').filter(has_text='consultation.open').first).to_contain_text('W72-v2')
  page.wait_for_timeout(150);check('lost committed response reconciles via reads not retry',len(committed)==1 and len(writes)==n+1 and len(rounds())==2)
  page.unroute('**/cases/'+CASE+'/consultation/rounds');phase='normal'
  # Age only disposable test round2, never alter an audit record.
  with sqlite3.connect(data/'mcis.db') as db:
   doc=json.loads(db.execute('select doc from consultation_rounds where case_id=? and key=?',(CASE,'2')).fetchone()[0]);doc['deadlineUtc']=(datetime.now(timezone.utc)-timedelta(seconds=5)).isoformat().replace('+00:00','Z');db.execute('update consultation_rounds set doc=? where case_id=? and key=?',(json.dumps(doc),CASE,'2'))
  refresh_all();check('expired fixture still unanswered',not rounds()[1]['allReplied']);preview('核对关闭本轮');closed2=confirm(200,'/rounds/2:close');check('expired allows close with unanswered party',closed2['isClosed'] and not closed2['allReplied'])
  # Stale create preview versus another actual client open -> real409, no retry.
  expect(panel.get_by_label('草案版本')).to_be_visible();fillnew('Stale v3',two=False);preview('核对新建轮次')
  api(cp('/consultation/rounds'),'POST',{'draftVersion':'Other client v3','parties':[{'partyId':'C','name':'Fictional C'}]})
  phase='expected-conflict';confirm(409,'/consultation/rounds');expect(panel.get_by_role('alert')).to_contain_text('consultation_round_open');ready();check('stale open does not duplicate round',len(rounds())==3)
  panel.get_by_label('选择轮次').select_option('3');panel.get_by_label('已确认放弃的依据/理由').fill('stale waiver');preview('核对放弃回复登记')
  api(cp('/consultation/rounds/3/waivers'),'POST',{'partyId':'C','reason':'Other client waiver'})
  confirm(409,'/rounds/3/waivers');expect(panel.get_by_role('alert')).to_contain_text('consultation_duplicate_reply');ready()
  # Real permission downgrade while close confirmation is stale.
  preview('核对关闭本轮');policy=api(cp('/access-policy'));policy['matrix']['Investigator']['report_draft']='ReadOnly';api(cp('/access-policy'),'PUT',policy)
  phase='expected-permission';confirm(403,'/rounds/3:close');expect(panel.get_by_text('当前角色只读',exact=False)).to_be_visible();check('403 leaves round open and clears lifecycle',not rounds()[2]['isClosed'] and lifecycle.count()==0)
  policy['matrix']['Investigator']['report_draft']='ReadWrite';api(cp('/access-policy'),'PUT',policy);refresh_all();phase='normal';panel.get_by_label('选择轮次').select_option('3')
  preview('核对关闭本轮');api(cp('/consultation/rounds/3:close'),'POST');phase='expected-conflict';confirm(409,'/rounds/3:close');ready();check('stale close conflict preserves closed state',rounds()[2]['isClosed'])
  # Unknown outcome plus failed reconciliation must not leave mutation controls enabled.
  fillnew('W72-v4 recovery',two=False);preview('核对新建轮次');phase='expected-reconcile-failure';lost=[];n=len(writes)
  def fail_reconcile(route):
   if route.request.method=='POST':
    response=route.fetch();check('fourth create actually committed',response.status==201);lost.append(response.json());route.abort('failed')
   else:route.fulfill(status=503,content_type='application/json',body=json.dumps({'code':'TEST_READ_FAILURE','message':'Injected reconciliation read failure'}))
  page.route('**/cases/'+CASE+'/consultation/rounds',fail_reconcile);confirmation.get_by_role('button',name='确认登记').click()
  expect(panel.get_by_role('alert')).to_contain_text('Injected reconciliation read failure');page.wait_for_timeout(150)
  check('failed reconcile fail closed no mutation retry',len(lost)==1 and len(writes)==n+1 and panel.get_by_label('草案版本').count()==0 and panel.get_by_role('button',name='确认登记').count()==0)
  page.unroute('**/cases/'+CASE+'/consultation/rounds');phase='normal';refresh_all();check('manual read recovers fourth committed round',len(rounds())==4)
  panel.get_by_label('选择轮次').select_option('4');panel.get_by_label('已确认放弃的依据/理由').fill('private draft confirmation');preview('核对放弃回复登记');phase='role-denied';role('Public');expect(panel.get_by_role('alert')).to_contain_text('无权查看');check('Deny clears lifecycle confirmation',confirmation.count()==0 and 'private draft confirmation' not in page.locator('body').inner_text())
  role('Investigator');ready();panel.get_by_label('选择轮次').select_option('4')
  for width in (1440,768):
   page.set_viewport_size({'width':width,'height':1000});panel.scroll_into_view_if_needed();page.screenshot(path=str(OUT/f'lifecycle-{width}.png'),full_page=True);shots.append(f'lifecycle-{width}.png')
   dims=page.evaluate('({document:document.documentElement.scrollWidth,main:document.querySelector(".main").clientWidth,scroll:document.querySelector(".main").scrollWidth})');check('no layout overflow '+str(width),dims['document']==width and dims['scroll']<=dims['main'],dims)
  check('no external requests',not external,external);check('no JS errors',not errors,list(errors))
  unexpected=[r for r in http if not (r['status']==403 and '/audit?' in r['url'] and r['role'] in ['InterestedState','Public','ExternalExpert']) and not (r['phase'] in ['expected-conflict','expected-permission','expected-reconcile-failure'] and r['status'] in [403,409,503])]
  check('HTTP errors explained',not unexpected,unexpected)
  check('console errors only controlled network failures',not [c for c in consoles if c['type']=='error' and not c['text'].startswith('Failed to load resource:')],consoles)
  chain=api(cp('/audit:verify'));check('audit hash valid',chain['valid'],chain)
  events=api(cp('/audit?category=Consultation'));new=[e for e in events if e['seq']>before_seq]
  from collections import Counter
  counts=dict(Counter(e['action'] for e in new));check('exact successful audit counts',counts=={'consultation.open':4,'consultation.reply':1,'consultation.waive':2,'consultation.close':3,'consultation.decide':1},counts)
  check('all browser writes scoped to temporary case',all('/cases/'+CASE+'/' in w['url'] for w in writes))
  check('frozen implementation hashes after',frozen_ok())
  browser.close()
except Exception as e:
 errors.append('HARNESS: '+repr(e));(OUT/'exception.txt').write_text(traceback.format_exc())
 try: (OUT/'failure-body.txt').write_text(page.locator('body').inner_text());page.screenshot(path=str(OUT/'failure.png'),full_page=True)
 except Exception:pass
 raise
finally:
 (OUT/'result.json').write_text(json.dumps({'checks':checks,'errors':errors,'console':consoles,'httpErrors':http,'mutations':writes,'screenshotsLocalOnly':shots},ensure_ascii=False,indent=2))
 for p in reversed(procs):
  try:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=10)
  except Exception:pass
 for f in handles:f.close()
if any(not c['passed'] for c in checks):
 raise SystemExit(1)
