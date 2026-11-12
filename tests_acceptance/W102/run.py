import base64,hashlib,json,os,subprocess,tempfile,time,urllib.request,urllib.error,concurrent.futures,sqlite3,traceback,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'logs'; DATA=Path(tempfile.mkdtemp(prefix='w102-independent-')); RESULTS=[]
BASE='http://127.0.0.1:18822/api/v1'; WEB='http://127.0.0.1:15822'; processes=[]
def req(path,body=None,headers=None,base=BASE,raw=False,method=None):
 h={'X-MCIS-Operator':'Independent','X-MCIS-Role':'Investigator'};h.update(headers or {})
 if body is not None and not isinstance(body,bytes):body=json.dumps(body).encode();h['Content-Type']='application/json'
 try:
  with urllib.request.urlopen(urllib.request.Request(base+path,data=body,headers=h,method=method),timeout=30) as r: data=r.read();status=r.status
 except urllib.error.HTTPError as e:status=e.code;data=e.read()
 if not raw:
  try:data=json.loads(data)
  except: data=data.decode(errors='replace')
 return status,data
def ck(name,fn):
 try:fn();RESULTS.append([name,'PASS']);print('PASS',name,flush=True)
 except Exception as e:RESULTS.append([name,'FAIL',str(e)]);print('FAIL',name,str(e),flush=True);traceback.print_exc()
def eq(a,b):assert a==b,(a,b)
def path(i,suffix):return f'/cases/ACCEPT-W102-{i}'+suffix
H='utc,latDeg,lonDeg,sogKn,sogStatus,cogDeg,cogStatus,hdgDeg,hdgStatus\r\n'
ROW='2025-12-31T23:59:59.125Z,31,121,102.2,reported,45,reported,511,unavailable\r\n'
RAW=b'\xef\xbb\xbf'+(H+ROW+'2026-01-01T00:00:00.001Z,31.1,121.1,0,reported,0,reported,1,reported\r\n').encode()
def body(raw=RAW,v='V1'):return dict(profile='mcis-utc-v1',vesselId=v,fileName='synthetic.csv',source='合成资料 <script>window.bad=1</script>',timeBasis='Synthetic full UTC declaration',contentBase64=base64.b64encode(raw).decode())
def preview(i,b=None,headers=None):
 status,p=req(path(i,'/track-imports:preview'),b or body(),headers);eq(status,200);return p
def commit(i,b=None,p=None,headers=None):
 b=b or body();p=p or preview(i,b);return req(path(i,'/track-imports:commit'),{**b,'confirmed':True,'previewDigest':p['previewDigest']},headers)
def counts(i):
 with sqlite3.connect(DATA/'primary/mcis.db') as db:return [db.execute(f'SELECT COUNT(*) FROM {t} WHERE case_id=?',(f'ACCEPT-W102-{i}',)).fetchone()[0] for t in ['track_points','evidence_items','custody_events','audit_events']]
def start(port,folder,seed='1'):
 env={**os.environ,'PYTHONPATH':str(ROOT/'service'),'MCIS_DATA_DIR':str(DATA/folder),'MCIS_SEED_DEMO':'0','MCIS_PORT':str(port),'ACCEPT_SEED':seed}
 f=open(OUT/f'w102-independent-service-{port}.log','w');p=subprocess.Popen([str(ROOT/'service/.venv/bin/python'),str(Path(__file__).with_name('server.py'))],env=env,stdout=f,stderr=f);processes.append(p)
 for _ in range(100):
  try:
   if req('/health',base=f'http://127.0.0.1:{port}/api/v1')[0]==200:return
  except:pass
  time.sleep(.1)
 raise Exception('service start failed')
def main():
 start(18822,'primary');start(18823,'roundtrip','0')
 processes.append(subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15822'],cwd=ROOT/'web',env={**os.environ,'MCIS_API':'http://127.0.0.1:18822'},stdout=open(OUT/'w102-independent-vite.log','w'),stderr=subprocess.STDOUT))
 def semantic():
  before=counts(0);p=preview(0);eq(p['canCommit'],True);eq(p['sourceSha256'],hashlib.sha256(RAW).hexdigest());eq(p['samplePoints'][0]['hdgDeg'],None);eq(p['samplePoints'][0]['sogKn'],102.2);eq(p['samplePoints'][0]['timeSec'],-.875);eq(p['samplePoints'][1]['timeSec'],.001);eq(before,counts(0))
 ck('BOM CRLF reported102.2 HDG511 null UTC milliseconds negative sim preview zero writes',semantic)
 for status in ['lowerBound','unknown','unavailable']:
  def blocked(status=status):
   b=body(RAW.replace(b'102.2,reported',('102.2,'+status).encode()));p=preview(1,b);eq(p['canCommit'],False);eq(commit(1,b,p)[0],422);eq(counts(1),[0,0,0,0])
  ck('Required SOG '+status+' blocks',blocked)
 for old,new in [(b'45,reported',b'45,unknown'),(b'45,reported',b'3600,unavailable'),(b'511,unavailable',b'511,unknown'),(b'2025-12-31T23:59:59.125Z',b'23:59:59Z'),(b'2025-12-31T23:59:59.125Z',b'2025-02-30T23:59:59Z'),(b'2025-12-31T23:59:59.125Z',b'2026-01-01T00:00:00.001Z'),(b'2025-12-31T23:59:59.125Z',b'2026-01-02T00:00:00Z'),(b'2025-12-31T23:59:59.125Z',b'2025-12-31T23:59:59+00:00'),(b'2025-12-31T23:59:59.125Z',b'2025-12-31T23:59:59.1234Z'),(b',31,121,',b',91,121,')]:
  ck('Reject '+new.decode(),lambda old=old,new=new:eq(preview(1,body(RAW.replace(old,new)))['canCommit'],False))
 def bindings():
  p=preview(2)
  for field,value in [('source','changed'),('timeBasis','changed'),('vesselId','V2'),('fileName','other.csv'),('contentBase64',base64.b64encode(RAW+b'\r\n').decode())]:eq(commit(2,{**body(),field:value},p)[0],409)
  eq(commit(2,p=p,headers={'X-MCIS-Operator':'Other'})[0],409)
  eq(commit(3,p=p)[0],409)
  eq(req(path(2,'/track-imports:commit'),{**body(),'confirmed':False,'previewDigest':p['previewDigest']})[0],422)
  eq(req(path(2,'/track-imports:preview'),{**body(),'profile':'ais'})[0],422)
 ck('Metadata operator vessel case profile confirmation binding',bindings)
 def saved():
  st,r=commit(0);eq(st,200);eq(counts(0),[2,2,2,3]);d=r['previewDigest'];eq(req(path(0,'/track-imports/'+d+'/source'),raw=True)[1],RAW)
  rb=req(path(0,'/track-imports/'+d+'/report'),raw=True)[1];eq(hashlib.sha256(rb).hexdigest(),r['reportSha256']);report=json.loads(rb);eq(report['operator'],'Independent');eq(report['preview']['caseEpochUtc'],'2026-01-01T00:00:00Z');eq(report['metadata']['profile'],'mcis-utc-v1')
  before=counts(0);eq(commit(0)[1]['replayed'],True);eq(counts(0),before);eq(commit(0,body(RAW.replace(b',31,',b',32,')))[0],409)
 ck('Save originals report digest evidence custody audit idempotency no overwrite',saved)
 def race(i,same):
  b=body();p=preview(i,b);b2=b if same else body(RAW.replace(b',31,',b',32,'));p2=preview(i,b2)
  with concurrent.futures.ThreadPoolExecutor(2) as pool:r=list(pool.map(lambda args:commit(i,*args),[(b,p),(b2,p2)]))
  eq(sorted(x[0] for x in r),[200,200] if same else [200,409]);eq(counts(i)[0],2);eq(counts(i)[1],2)
 ck('Concurrent same request single result',lambda:race(4,True));ck('Concurrent different source one wins',lambda:race(5,False))
 for i,kind in [(6,'file2'),(7,'dbcommit'),(8,'cleanup')]:
  def failure(i=i,kind=kind):
   p=preview(i);st,r=commit(i,p=p,headers={'X-Accept-Fault':kind});eq(st,500);eq(counts(i),[0,0,0,0]);files=list((DATA/'primary/blobs'/f'ACCEPT-W102-{i}').rglob('*.*'));eq(len(files),1 if kind=='cleanup' else 0)
   if kind=='cleanup':eq(r['code'],'IMPORT_CLEANUP_FAILED')
  ck('Injected '+kind+' rollback',failure)
 for role in ['Public','InterestedState','ExternalExpert']:
  ck('Role '+role+' denied',lambda role=role:eq(req(path(0,'/track-imports?vesselId=V1'),headers={'X-MCIS-Role':role})[0],403))
 def budget():
  from datetime import datetime,timedelta
  rows=''.join((datetime(2026,1,1)+timedelta(seconds=i)).isoformat()+'Z,31,121,1,reported,45,reported,511,unavailable\n' for i in range(10000));p=preview(9,body((H+rows).encode()));eq(p['rowCount'],10000);eq(len(p['samplePoints']),100);eq(p['canCommit'],True)
  eq(req(path(9,'/track-imports:preview'),body((H+rows+rows.splitlines()[0]+'\n').encode()))[0],413)
  p=preview(9,body((H+rows.replace(',1,reported',',1,unknown')).encode()));eq(len(p['issues']),200);eq(p['issuesTotal'],10000);eq(p['issuesTruncated'],True)
 ck('10000 row 100 preview 200 diagnostics bounded',budget)
 def package():
  st,data=req(path(0,'/export'),raw=True);eq(st,200);eq(req('/cases:import',data,{'Content-Type':'application/zip'},base='http://127.0.0.1:18823/api/v1')[0],201)
  r=req(path(0,'/track-imports?vesselId=V1'),base='http://127.0.0.1:18823/api/v1')[1][0];eq(req(path(0,'/track-imports/'+r['previewDigest']+'/source'),base='http://127.0.0.1:18823/api/v1',raw=True)[1],RAW)
  with sqlite3.connect(DATA/'roundtrip/mcis.db') as db,sqlite3.connect(DATA/'primary/mcis.db') as src:
   eq(db.execute('select doc from track_points order by time_sec').fetchall(),src.execute('select doc from track_points where case_id=? order by time_sec',('ACCEPT-W102-0',)).fetchall())
   old=src.execute('select line from audit_events where case_id=? order by seq',('ACCEPT-W102-0',)).fetchall();new=db.execute('select line from audit_events where case_id=? order by seq',('ACCEPT-W102-0',)).fetchall();eq(new[:len(old)],old)
 ck('mcase export fresh DB import original receipt tracks',package)
 def boundaries():
  for raw in [b'\xff'+RAW,RAW+b'\0',RAW.replace(b'sogStatus',b'missing'),RAW.replace(b'cogStatus',b'sogStatus'),RAW.replace(b',102.2,',b',NaN,'),RAW.replace(b',102.2,',b',-1,')]:
   st,p=req(path(19,'/track-imports:preview'),body(raw));assert st==422 or (st==200 and not p['canCommit']),(st,p)
  eq(req(path(19,'/track-imports:preview'),body(b'x'*(1024*1024+1)))[0],413)
  eq(req(path(19,'/track-imports:preview'),b' '* (1536*1024+1),{'Content-Type':'application/json'})[0],413)
  for key in ['source','timeBasis']:eq(req(path(19,'/track-imports:preview'),{**body(),key:''})[0],422)
  eq(counts(19),[0,0,0,0])
 ck('Encoding NUL missing duplicate headers NaN negative empty metadata bytes body limits',boundaries)
 def persisted_points():
  r=req(path(0,'/track-imports?vesselId=V1'))[1][0];points=req(path(0,'/tracks?vesselId=V1'))[1]['tracks'][0]['points'];eq(len(points),r['pointCount']);eq([p['timeSec'] for p in points],[-.875,.001]);eq([p['hdgDeg'] for p in points],[None,1]);eq(points[0]['source'],'CSV:'+r['sourceEvidenceId']+':row:1')
 ck('Persisted GET tracks receipt source row values consistency',persisted_points)
 def epoch():
  p=preview(13)
  with sqlite3.connect(DATA/'primary/mcis.db') as db:
   row=db.execute('select doc from cases where case_id=?',('ACCEPT-W102-13',)).fetchone();d=json.loads(row[0]);d['caseEpochUtc']='2026-01-02T00:00:00Z';db.execute('update cases set doc=? where case_id=?',(json.dumps(d),'ACCEPT-W102-13'))
  eq(commit(13,p=p)[0],409);eq(counts(13),[0,0,0,0])
 ck('Epoch changed after preview revalidated',epoch)
 def policy():
  p=preview(14)
  pol={'matrix':{'Investigator':{'ais_sim':'ReadWrite','evidence_meta':'ReadWrite','testimony':'Deny'}},'fieldRules':[]}
  with sqlite3.connect(DATA/'primary/mcis.db') as db:db.execute("insert into access_policies(case_id,key,doc,created_utc,updated_utc) values(?,?,?,?,?)",('ACCEPT-W102-14','policy',json.dumps(pol),'2026-01-01T00:00:00Z','2026-01-01T00:00:00Z'))
  eq(commit(14,p=p)[0],403);eq(req(path(14,'/track-imports:preview'),body())[0],403);eq(counts(14),[0,0,0,0])
 ck('Restricted source policy changed after preview denied',policy)
 def damaged_points():
  p=preview(15);eq(commit(15,p=p)[0],200)
  with sqlite3.connect(DATA/'primary/mcis.db') as db:db.execute('delete from track_points where case_id=?',('ACCEPT-W102-15',))
  eq(req(path(15,'/track-imports/'+p['previewDigest']))[0],409)
  eq(req(path(15,'/track-imports?vesselId=V1'))[0],409);eq(commit(15,p=p)[0],409)
  eq(req(path(15,'/track-imports/'+p['previewDigest']+'/source'))[0],409);eq(counts(15)[0],0)
 ck('KnownDefect receipt recovery rejects missing persisted points',damaged_points)
 def corrupt_variant(i,kind):
  p=preview(i);eq(commit(i,p=p)[0],200)
  with sqlite3.connect(DATA/'primary/mcis.db') as db:
   if kind=='edited-point':
    row=db.execute('select id,doc from track_points where case_id=? order by id', (f'ACCEPT-W102-{i}',)).fetchone();d=json.loads(row[1]);d['sogKn']=7;db.execute('update track_points set doc=? where id=?',(json.dumps(d),row[0]))
   elif kind=='point-source':
    row=db.execute('select id,doc from track_points where case_id=? order by id',(f'ACCEPT-W102-{i}',)).fetchone();d=json.loads(row[1]);d['source']='CSV:EV-999:row:1';db.execute('update track_points set doc=? where id=?',(json.dumps(d),row[0]))
   elif kind=='epoch':
    row=db.execute('select doc from cases where case_id=?',(f'ACCEPT-W102-{i}',)).fetchone();d=json.loads(row[0]);d['caseEpochUtc']='2026-01-02T00:00:00Z';db.execute('update cases set doc=? where case_id=?',(json.dumps(d),f'ACCEPT-W102-{i}'))
  if kind=='source-bytes':
   f=DATA/'primary/blobs'/f'ACCEPT-W102-{i}'/'raw/track-imports'/p['previewDigest']/'source.csv';f.write_bytes(RAW+b'\n')
  eq(req(path(i,'/track-imports/'+p['previewDigest']))[0],409);eq(req(path(i,'/track-imports?vesselId=V1'))[0],409);eq(commit(i,p=p)[0],409)
 for i,kind in enumerate(['edited-point','point-source','epoch','source-bytes'],21):ck('Receipt recovery rejects '+kind,lambda i=i,kind=kind:corrupt_variant(i,kind))
 def edit_description(i,label):
  st,snapshot=req(path(i,'/metadata'));eq(st,200)
  before=snapshot['case']
  change=dict(operationId='independent-w102-'+str(i),expectedRevision=snapshot['revision'],changes={'title':label,'summaryNotes':'Synthetic cross-package description only'},sourceLabel='Independent synthetic fixture',changeReason='Verify W8.4 W10.2 compatibility')
  st,after=req(path(i,'/metadata'),change,method='PATCH');eq(st,200);eq(after['case']['title'],label);eq(after['case']['caseEpochUtc'],before['caseEpochUtc']);eq(after['case']['caseId'],before['caseId']);return after
 def preview_then_edit():
  p=preview(28);edit_description(28,'Synthetic renamed after preview');eq(preview(28)['previewDigest'],p['previewDigest']);st,r=commit(28,p=p);eq(st,200);eq(r['pointCount'],2);eq(counts(28)[0],2)
 ck('W8.4 description edit after W10 preview permits original confirmed commit',preview_then_edit)
 def saved_then_edit():
  p=preview(29);st,r=commit(29,p=p);eq(st,200);d=p['previewDigest'];source=req(path(29,'/track-imports/'+d+'/source'),raw=True)[1];report=req(path(29,'/track-imports/'+d+'/report'),raw=True)[1];points=req(path(29,'/tracks?vesselId=V1'))[1]
  edit_description(29,'Synthetic renamed after saving');st,recovered=req(path(29,'/track-imports/'+d));eq(st,200);eq(recovered['previewDigest'],d);eq(recovered['pointCount'],2);eq(req(path(29,'/track-imports/'+d+'/source'),raw=True)[1],source);eq(req(path(29,'/track-imports/'+d+'/report'),raw=True)[1],report);eq(req(path(29,'/tracks?vesselId=V1'))[1],points);eq(req(path(29,'/metadata'))[1]['case']['caseEpochUtc'],'2026-01-01T00:00:00Z');eq(commit(29,p=p)[1]['replayed'],True)
 ck('W8.4 description edit after saved W10 preserves receipt bytes points epoch',saved_then_edit)
 browser()

def browser():
 from playwright.sync_api import sync_playwright
 with sync_playwright() as pw:
  br=pw.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN'),headless=True,args=['--no-sandbox']);page=br.new_page(viewport={'width':1440,'height':1000});page.add_init_script("localStorage.setItem('mcis.operator','Independent')")
  def open_panel(i):
   page.goto(WEB+f'/#/track?case=ACCEPT-W102-{i}');page.get_by_role('button',name='＋ 导入明确语义 UTC CSV / 查看导入原件').click()
  def fill():
   page.get_by_label('目标船舶').select_option('V1');page.locator('input[type=file]').set_input_files({'name':'browser.csv','mimeType':'text/csv','buffer':RAW});page.get_by_label('资料来源说明（必填）').fill('<img src=x onerror=window.bad=1> Synthetic');page.get_by_label('UTC 时间依据说明（必填）').fill('Synthetic UTC')
  def ui():
   open_panel(10);fill();eq(counts(10),[0,0,0,0]);page.get_by_role('button',name='服务端预览（不保存）',exact=True).click();page.get_by_text('2 · 核对预览与来源声明').wait_for();eq(counts(10),[0,0,0,0]);eq(page.evaluate('window.bad||null'),None)
   eq(page.get_by_role('button',name='确认保存本次航迹').is_disabled(),True);page.get_by_role('checkbox').check();page.get_by_label('资料来源说明（必填）').fill('changed');eq(page.get_by_text('2 · 核对预览与来源声明').count(),0)
   page.get_by_role('button',name='服务端预览（不保存）',exact=True).click();page.get_by_role('checkbox').check();page.screenshot(path=str(OUT/'w102-independent-1440.png'),full_page=True);page.get_by_role('button',name='确认保存本次航迹').dblclick();page.get_by_text('已核对保存回执',exact=True).wait_for();eq(counts(10)[0],2)
   page.reload();page.get_by_role('button',name='＋ 导入明确语义 UTC CSV / 查看导入原件').wait_for();eq(page.locator('.w102-panel').count(),0)
  ck('Chromium local-only selection preview invalidate escaping confirm doubleclick reload',ui)
  def loss():
   open_panel(11);fill();page.get_by_role('button',name='服务端预览（不保存）',exact=True).click();page.get_by_role('checkbox').check()
   def drop(route):route.fetch();route.abort('failed')
   page.route('**/track-imports:commit',drop);page.get_by_role('button',name='确认保存本次航迹').click();page.get_by_text('保存结果未确认，服务可能已经保存。先只读核查；不要另选文件重复提交。',exact=True).wait_for();eq(counts(11)[0],2);page.get_by_role('button',name='只读核查本次保存').click();page.get_by_text('已核对保存回执',exact=True).wait_for();page.unroute('**/track-imports:commit');eq(counts(11)[0],2)
  ck('Chromium committed response loss readonly recovery',loss)
  def desktop():
   page.set_viewport_size({'width':1920,'height':1080});open_panel(12);fill();page.screenshot(path=str(OUT/'w102-independent-1920.png'),full_page=True);eq(page.evaluate('document.documentElement.scrollWidth <= innerWidth'),True);page.get_by_role('button',name='取消 / 关闭输入').focus();page.keyboard.press('Enter');eq(page.locator('.w102-panel').count(),0)
  ck('Chromium 1920 no horizontal overflow keyboard close',desktop)
  def replacement():
   open_panel(16);fill();page.get_by_role('button',name='服务端预览（不保存）',exact=True).click();page.get_by_role('checkbox').check();page.locator('input[type=file]').set_input_files({'name':'second.csv','mimeType':'text/csv','buffer':RAW.replace(b',31,',b',32,')});page.get_by_text('本地文件：second.csv',exact=False).wait_for();eq(page.get_by_text('2 · 核对预览与来源声明').count(),0);eq(page.get_by_role('checkbox').count(),0)
  ck('Chromium file replacement invalidates preview confirmation',replacement)
  def late():
   open_panel(17);fill()
   def delay(route):
    response=route.fetch();page.evaluate("location.hash='#/track?case=ACCEPT-W102-18'");route.fulfill(response=response)
   page.route('**/track-imports:preview',delay);page.get_by_role('button',name='服务端预览（不保存）',exact=True).click();page.wait_for_timeout(700);eq(page.locator('.w102-preview').count(),0);eq(page.locator('.w102-panel').count(),0);page.unroute('**/track-imports:preview');page.go_back();page.wait_for_timeout(500);eq(page.locator('.w102-preview').count(),0);eq(counts(17),[0,0,0,0])
  ck('Chromium late preview case navigation fast Back isolation',late)
  def large_preview():
   from datetime import datetime,timedelta
   open_panel(25);fill();rows=''.join((datetime(2026,1,1)+timedelta(seconds=i)).isoformat()+'Z,31,121,1,reported,45,reported,511,unavailable\n' for i in range(10000));page.locator('input[type=file]').set_input_files({'name':'large.csv','mimeType':'text/csv','buffer':(H+rows).encode()});start=time.monotonic();page.get_by_role('button',name='服务端预览（不保存）',exact=True).click();page.get_by_text('2 · 核对预览与来源声明').wait_for();elapsed=time.monotonic()-start;eq(page.locator('.w102-table tbody tr').count(),20)
   for _ in range(4):page.get_by_role('button',name='预览下一页',exact=True).click()
   eq(page.get_by_role('button',name='预览下一页',exact=True).is_disabled(),True);eq(page.locator('.w102-table tbody tr').count(),20);eq(counts(25),[0,0,0,0]);print('MEASURE Chromium 10000 rows preview seconds',round(elapsed,3),flush=True)
  ck('Chromium 10000 rows preview 100 samples paginated 20 DOM budget',large_preview)
  def navigate_commit():
   open_panel(26);fill();page.get_by_role('button',name='服务端预览（不保存）',exact=True).click();page.get_by_role('checkbox').check()
   def delay(route):
    response=route.fetch();page.evaluate("location.hash='#/track?case=ACCEPT-W102-27'");route.fulfill(response=response)
   page.route('**/track-imports:commit',delay);page.get_by_role('button',name='确认保存本次航迹').click();page.wait_for_timeout(700);eq(page.locator('.w102-receipt').count(),0);eq(counts(26)[0],2);page.unroute('**/track-imports:commit');open_panel(26);page.get_by_label('目标船舶').select_option('V1');page.get_by_role('button',name='读取本船导入回执（只读）').click();page.get_by_text('已核对保存回执',exact=True).wait_for();eq(counts(26)[0],2)
  ck('Chromium navigate during committed response then reopen readonly recovery',navigate_commit)
  def role_late():
   open_panel(20);fill()
   def delay(route):
    response=route.fetch();page.locator('select').first.select_option('Public');route.fulfill(response=response)
   page.route('**/track-imports:preview',delay);page.get_by_role('button',name='服务端预览（不保存）',exact=True).click();page.wait_for_timeout(600);eq(page.locator('.w102-preview').count(),0);eq(page.locator('.w102-panel').count(),0);page.unroute('**/track-imports:preview');eq(counts(20),[0,0,0,0])
  ck('Chromium role switch rejects late preview',role_late)
  br.close()
try:main()
finally:
 for p in processes:p.terminate()
 for p in processes:
  try:p.wait(timeout=10)
  except:p.kill()
 (OUT/'w102-independent-results.json').write_text(json.dumps({'results':RESULTS,'data':str(DATA),'passed':sum(r[1]=='PASS' for r in RESULTS),'failed':sum(r[1]=='FAIL' for r in RESULTS)},ensure_ascii=False,indent=2))
 print('TOTAL',len(RESULTS),'PASS',sum(r[1]=='PASS' for r in RESULTS),'FAIL',sum(r[1]=='FAIL' for r in RESULTS),flush=True)
sys.exit(1 if any(r[1]=='FAIL' for r in RESULTS) else 0)
