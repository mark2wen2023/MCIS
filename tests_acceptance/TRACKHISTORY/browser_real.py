"""Real restored-history browser; separate explicit simulated refusal UI checks."""
import os,signal,subprocess,tempfile,time,urllib.request,json
from pathlib import Path
from playwright.sync_api import sync_playwright
CID='SYN-TRACK-HISTORY'
CSV=b'utc,latDeg,lonDeg,sogKn,sogStatus,cogDeg,cogStatus,hdgDeg,hdgStatus\r\n2026-01-01T00:00:01Z,31,121,8,reported,20,reported,20,reported\r\n2026-01-01T00:00:02Z,31.001,121.001,8,reported,21,reported,21,reported\r\n'
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent
with tempfile.TemporaryDirectory(prefix='track-history-browser-') as tmp:
 env={**os.environ,'MCIS_DATA_DIR':tmp,'MCIS_API':'http://127.0.0.1:15994','PYTHONPATH':str(ROOT/'service'),'ARCHIVE_PORT':'15994'};procs=[]
 try:
  procs.append(subprocess.Popen([str(ROOT/'service/.venv/bin/python'),str(HERE/'server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True))
  procs.append(subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15995','--strictPort'],cwd=ROOT/'web',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True))
  for port in (15994,15995):
   for _ in range(200):
    try:urllib.request.urlopen(f'http://127.0.0.1:{port}'+('/api/v1/health' if port==15994 else '/'),timeout=1);break
    except Exception:time.sleep(.1)
   else:raise RuntimeError('synthetic services startup failed')
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.environ['MCIS_BROWSER_BIN'],headless=True,args=['--no-sandbox']);p=browser.new_page();p.set_default_timeout(12000);errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
   p.add_init_script("localStorage.setItem('mcis.role','LeadInvestigator');localStorage.setItem('mcis.operator','Synthetic Track Reviewer')")
   def open(v='ship'):
    p.goto('http://127.0.0.1:15995/#/track?case='+CID);p.reload()
    p.get_by_role('button',name='＋ 导入明确语义 UTC CSV / 查看导入原件',exact=True).click();p.get_by_label('目标船舶').select_option(v)
   open();p.get_by_role('button',name='读取本船导入回执（只读）',exact=True).click();p.get_by_text('这是只读归档历史',exact=False).wait_for()
   assert p.get_by_role('heading',name='已核对保存回执').count()==0
   p.get_by_role('button',name='独立读取本船归档历史（不核验当前保存）',exact=True).click();p.get_by_role('heading',name='只读航迹归档历史',exact=True).wait_for()
   with p.expect_download() as dl:p.get_by_role('button',name='记录访问并下载历史CSV',exact=True).click()
   assert Path(dl.value.path()).read_bytes()==CSV
   with p.expect_download() as dl:p.get_by_role('button',name='记录访问并下载历史说明',exact=True).click()
   record=json.loads(Path(dl.value.path()).read_bytes());assert record['role']=='LeadInvestigator' and record['receipt']['pointCount']==2
   assert p.get_by_role('heading',name='已核对保存回执').count()==0
   p.locator('select[title="X-MCIS-Role"]').select_option('Investigator');assert p.get_by_role('heading',name='只读航迹归档历史').count()==0
   p.locator('select[title="X-MCIS-Role"]').select_option('LeadInvestigator')
   # Real preview for an unused vessel, but explicitly simulated save refusal responses.
   for code in ('ARCHIVE_HISTORY_ONLY','TRACK_ORIGIN_UNVERIFIED'):
    open('newship');p.get_by_label('资料来源说明（必填）').fill('Synthetic browser');p.get_by_label('UTC 时间依据说明（必填）').fill('Synthetic UTC')
    p.get_by_label('CSV 原件',exact=False).set_input_files({'name':'synthetic.csv','mimeType':'text/csv','buffer':CSV});p.get_by_text('SHA-256：',exact=False).first.wait_for()
    p.get_by_role('button',name='服务端预览（不保存）',exact=True).click();p.get_by_role('heading',name='2 · 核对预览与来源声明').wait_for()
    p.get_by_label('我已核对目标案件',exact=False).check()
    def refuse(route):route.fulfill(status=409,json={'code':code,'message':'Synthetic controlled refusal'})
    p.route('**/track-imports:commit',refuse);p.get_by_role('button',name='确认保存本次航迹',exact=True).click();p.get_by_text('3 · 结果待核查',exact=False).wait_for()
    assert p.get_by_label('目标船舶').is_disabled() and p.get_by_role('heading',name='已核对保存回执').count()==0
    p.unroute('**/track-imports:commit',refuse)
   assert not errors,errors;browser.close()
  print('PASS real restored list refusal/history CSV+report downloads and role clearing. Separately PASS 2 explicitly simulated409 save responses retain unknown lock after real preview; no claim those saves were real.')
 finally:
  for process in procs:
   if process.poll() is None:os.killpg(process.pid,signal.SIGTERM)
  for process in procs:process.wait()
