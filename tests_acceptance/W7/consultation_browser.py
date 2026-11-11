"""Local-only W7.1 browser acceptance; requires frozen implementation and official headless shell.
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
CASE='CASE-2026-DEMO-LILY-MARY'; YANGZE='CJK-2024-1230-YangZe22-VegaDream'
def port():
 with socket.socket() as s: s.bind(('127.0.0.1',0)); return s.getsockname()[1]
def wait(url):
 for _ in range(200):
  try:
   with urllib.request.urlopen(url,timeout=2):return
  except Exception:time.sleep(.15)
 raise RuntimeError('not ready '+url)
bp,fp=port(),port(); base=f'http://127.0.0.1:{fp}'; back=f'http://127.0.0.1:{bp}/api/v1'
data=Path(tempfile.mkdtemp(prefix='w71-data-'))
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
freeze=(ROOT/'logs/w7.1-impl-hashes-frozen.txt').read_text();(OUT/'implementation-hashes.txt').write_text(freeze)
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
  phase='normal'
  page.goto(base+'/#/recs?case='+CASE);ready()
  check('default latest open round',panel.get_by_label('选择轮次').input_value()=='2')
  panel.get_by_label('回复正文',exact=True).fill('unsent private test draft')
  page.evaluate('(h)=>location.hash=h','#/recs?case='+YANGZE)
  expect(panel.get_by_text('暂无征求意见轮次',exact=False)).to_be_visible()
  check('case switch clears old draft and rounds','unsent private' not in panel.inner_text() and panel.get_by_label('选择轮次').count()==0)
  page.evaluate('(h)=>location.hash=h','#/recs?case='+CASE);ready();expect(panel.get_by_label('回复正文',exact=True)).to_have_value('')
  panel.get_by_label('回复正文',exact=True).fill('role draft must clear')
  role('InterestedState');expect(panel.get_by_text('当前角色只读',exact=False)).to_be_visible()
  check('RO has no mutation forms',panel.get_by_role('button',name='登记回复',exact=True).count()==0 and panel.get_by_role('button',name='保存决定').count()==0)
  role('Investigator');ready();expect(panel.get_by_label('回复正文',exact=True)).to_have_value('')
  panel.get_by_label('回复方',exact=True).select_option('FLAG-B');panel.get_by_label('回复正文',exact=True).fill('W71 browser received reply (fictional)')
  panel.get_by_label('意见条目',exact=False).fill('W71 browser comment one\nW71 browser comment two')
  old_posts=len([w for w in writes if '/replies' in w['url']])
  with page.expect_response(lambda r:r.request.method=='POST' and '/rounds/2/replies' in r.url) as reply:
   panel.get_by_role('button',name='登记回复',exact=True).evaluate('(b)=>{b.click();b.click()}')
  check('reply HTTP201',reply.value.status==201);reply_doc=reply.value.json();ready()
  ids=next(r['commentIds'] for r in reply_doc['replies'] if r['partyId']=='FLAG-B')
  check('two Pending comments persisted',len(ids)==2 and all(next(c for c in reply_doc['comments'] if c['commentId']==cid)['decision']=='Pending' for cid in ids))
  check('double click emitted one POST',len([w for w in writes if '/replies' in w['url']])-old_posts==1)
  save(ids[0],'Adopted')
  row=item(ids[1]);row.get_by_label('采纳决定').select_option('PartiallyAdopted');row.get_by_label('反馈理由',exact=False).fill('   ')
  check('trimmed blank feedback blocks submission',row.get_by_role('button',name='保存决定').is_disabled())
  save(ids[1],'PartiallyAdopted','Browser acceptance partial reason')
  page.reload();ready();check('reload preserves reply and decisions','W71 browser received reply' in panel.inner_text() and 'Browser acceptance partial reason' in panel.inner_text())
  expect(page.locator('.p6-table').filter(has_text='consultation.decide').first).to_contain_text('Browser acceptance partial reason')
  check('audit refreshed after UI mutations',True)
  panel.get_by_label('选择轮次').select_option('1');check('closed round prevents reply',panel.get_by_role('button',name='登记回复',exact=True).count()==0 and '本轮已关闭' in panel.inner_text())
  panel.get_by_label('选择轮次').select_option('2')
  panel.get_by_label('回复方',exact=True).select_option('CO-MARY');panel.get_by_label('回复正文',exact=True).fill('stale reply')
  api(cp('/consultation/rounds/2/replies'),'POST',{'partyId':'CO-MARY','text':'Other session reply (fictional)','comments':[]})
  phase='expected-conflict';n=len(writes)
  with page.expect_response(lambda r:r.request.method=='POST' and '/rounds/2/replies' in r.url) as conflict:panel.get_by_role('button',name='登记回复',exact=True).click()
  check('real stale reply HTTP409',conflict.value.status==409);expect(panel.get_by_role('alert')).to_contain_text('consultation_duplicate_reply');ready();page.wait_for_timeout(300)
  check('conflict no retry and stale form invalidated',len(writes)==n+1 and panel.get_by_role('button',name='登记回复',exact=True).count()==0)
  phase='expected-permission';policy=api(cp('/access-policy'));policy['matrix']['Investigator']['report_draft']='ReadOnly';api(cp('/access-policy'),'PUT',policy)
  n=len(writes);row=item('R2-C04')
  with page.expect_response(lambda r:r.request.method=='PATCH' and '/comments/R2-C04' in r.url) as denied:row.get_by_role('button',name='保存决定').click()
  check('actual permission change HTTP403',denied.value.status==403);expect(panel.get_by_text('当前角色只读',exact=False)).to_be_visible();page.wait_for_timeout(300)
  check('403 no mutation retry',len(writes)==n+1)
  policy['matrix']['Investigator']['report_draft']='ReadWrite';api(cp('/access-policy'),'PUT',policy);refresh()
  phase='normal';api(cp('/consultation/rounds/2:close'),'POST');refresh()
  expect(item('R2-C04').get_by_role('button',name='保存决定')).to_be_visible();check('closed round Pending remains actionable',True)
  save('R2-C04','NotAdopted','Closed round pending decision reason')
  for width in (1440,768):
   page.set_viewport_size({'width':width,'height':1000});panel.scroll_into_view_if_needed();page.screenshot(path=str(OUT/f'consultation-{width}.png'),full_page=True);shots.append(f'consultation-{width}.png')
   dims=page.evaluate('({viewport:innerWidth,document:document.documentElement.scrollWidth,panel:document.querySelector(".w7-consultation").getBoundingClientRect().width,main:document.querySelector(".main").clientWidth,mainScroll:document.querySelector(".main").scrollWidth})')
   checks.append({'name':'viewport no document overflow '+str(width),'passed':dims['document']==width and dims['mainScroll']<=dims['main'],'detail':dims})
  page.set_viewport_size({'width':1440,'height':1000})
  phase='role-denied'
  held_audit=[]
  page.route('**/audit?*',lambda route:held_audit.append(route))
  role('Public')
  page.wait_for_timeout(100)
  check('whole page immediately removes prior audit and feedback before denied response',all(t not in page.locator('body').inner_text() for t in ['Browser acceptance partial reason','Closed round pending decision reason','W71 browser received reply']))
  check('new role audit response held',bool(held_audit))
  for route in held_audit:route.continue_()
  page.unroute('**/audit?*')
  expect(panel.get_by_role('alert')).to_contain_text('无权查看')
  check('Deny clears consultation content','W71 browser received reply' not in panel.inner_text() and panel.get_by_label('选择轮次').count()==0)
  role('Investigator');ready()
  # Hold allowed old-identity audit payloads, change role, then release them.
  old_audit=[]
  def hold_old_audit(route):
   if route.request.headers.get('x-mcis-role')=='Investigator':
    response=route.fetch();old_audit.append((route,response.body(),response.status))
   else:route.continue_()
  page.route('**/audit?*',hold_old_audit)
  page.reload();ready()
  for _ in range(50):
   if len(old_audit)==2:break
   page.wait_for_timeout(20)
  check('two allowed old-role audit responses held',len(old_audit)==2)
  role('ExternalExpert');expect(panel.get_by_role('alert')).to_contain_text('无权查看')
  for route,body,status in old_audit:route.fulfill(status=status,content_type='application/json',body=body)
  page.wait_for_timeout(100)
  check('late allowed audit response cannot refill denied role',all(t not in page.locator('body').inner_text() for t in ['Browser acceptance partial reason','Closed round pending decision reason','W71 browser received reply']))
  page.unroute('**/audit?*');role('Investigator');ready()
  phase='expected-policy-error';page.route('**/access-policy',lambda route:route.fulfill(status=503,content_type='application/json',body=json.dumps({'code':'TEST_POLICY_UNAVAILABLE','message':'Injected local policy failure'})))
  refresh_button=panel.get_by_role('button',name='重新读取',exact=True);refresh_button.click();expect(panel.get_by_role('alert')).to_contain_text('Injected local policy failure')
  check('policy failure is fail closed',panel.get_by_label('选择轮次').count()==0 and panel.get_by_role('button',name='保存决定').count()==0)
  page.unroute('**/access-policy');phase='normal';refresh()
  # Hold an old-case read response, switch case, then deliver the stale result.
  held=[]
  def hold(route):
   response=route.fetch();held.append((route,response.body(),response.status))
  page.route('**/cases/'+CASE+'/consultation/rounds',hold);panel.get_by_role('button',name='重新读取',exact=True).click()
  for _ in range(50):
   if held:break
   page.wait_for_timeout(20)
  check('old-case response held',bool(held));page.evaluate('(h)=>location.hash=h','#/recs?case='+YANGZE)
  expect(panel.get_by_text('暂无征求意见轮次',exact=False)).to_be_visible()
  for route,body,status in held:route.fulfill(status=status,content_type='application/json',body=body)
  page.wait_for_timeout(150);check('late old-case response ignored','W71 browser received reply' not in panel.inner_text() and panel.get_by_label('选择轮次').count()==0)
  page.unroute('**/cases/'+CASE+'/consultation/rounds')
  check('no external network requests',not external,external)
  check('no JS errors',not errors,list(errors))
  unexpected=[r for r in http if not ((r['status']==403 and '/audit?' in r['url'] and r['role'] in ['InterestedState','Public','ExternalExpert']) or r['phase'] in ['expected-conflict','expected-permission','role-denied','expected-policy-error'] and r['status'] in [403,409,503])]
  check('no unexpected HTTP errors',not unexpected,unexpected)
  check('no non-resource console errors',not [c for c in consoles if c['type']=='error' and not c['text'].startswith('Failed to load resource:')],consoles)
  chain=api(cp('/audit:verify'));check('audit hash chain valid',chain.get('valid',chain.get('ok',False)),chain)
  events=api(cp('/audit?category=Consultation'));new=[e for e in events if e['seq']>before_seq]
  check('exact audit mutation counts',len([e for e in new if e['action']=='consultation.reply'])==2 and len([e for e in new if e['action']=='consultation.decide'])==3 and len([e for e in new if e['action']=='consultation.close'])==1,[(e['action'],e['entityId']) for e in new])
  check('browser mutations bound to demo case',all('/cases/'+CASE+'/' in w['url'] for w in writes),writes)
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
