"""Synthetic API-double UI isolation tests, not real-backend acceptance."""
import subprocess,time,urllib.request,os,signal,hashlib,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
s=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15859','--strictPort'],cwd=ROOT/'web',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
try:
 for _ in range(100):
  try:urllib.request.urlopen('http://127.0.0.1:15859',timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=os.environ['MCIS_BROWSER_BIN'],headless=True,args=['--no-sandbox']);p=b.new_page();p.set_default_timeout(8000);held=[];mode={'hold':False,'bad':False,'code':'ARCHIVE_HISTORY_ONLY'};posts=[];downloads=[];p.on('download',lambda d:downloads.append(d))
  raw=b'utc,latDeg,lonDeg,sogKn,sogStatus,cogDeg,cogStatus,hdgDeg,hdgStatus\n2026-01-01T00:00:00Z,0,0,1,reported,0,reported,,unavailable\n';sha=hashlib.sha256(raw).hexdigest();digest='a'*64
  h={'caseId':'A','vesselId':'V','digest':digest,'mode':'archive-only','sourceEvidenceId':'E1','reportEvidenceId':'E2','sourceSha256':sha,'reportSha256':'b'*64,'pointCount':1,'identityMode':'unverified-self-reported'}
  def route(r):
   u=r.request.url
   if '/archive-history/track-imports?' in u:
    if mode['hold']:held.append(r)
    else:r.fulfill(json={'caseId':'A','vesselId':'V','mode':'archive-only','items':[h]})
   elif '/archive-history/track-imports/' in u:r.fulfill(body=b'wrong' if mode['bad'] else raw,headers={'Cache-Control':'no-store','Content-Disposition':'attachment; filename=source.csv','X-Sha256':sha})
   elif u.endswith(':preview'):
    d=r.request.post_data_json;r.fulfill(json={**{k:d[k] for k in ['profile','vesselId','fileName','source','timeBasis']},'caseId':'A','caseEpochUtc':'2026-01-01T00:00:00Z','previewDigest':digest,'sourceSha256':sha,'rowCount':1,'canCommit':True,'issues':[],'issuesTotal':0,'issuesTruncated':False,'samplePoints':[],'warnings':[],'existingTrackCount':0,'timeRange':{'firstUtc':'2026-01-01T00:00:00Z','lastUtc':'2026-01-01T00:00:00Z','fromSec':0,'toSec':0}})
   else:
    if r.request.method=='POST':posts.append(r.request.post_data)
    r.fulfill(status=409,json={'code':mode['code']})
  p.route('**/api/v1/**',route)
  def open():
   p.goto('http://127.0.0.1:15859/tests/track-history-harness.html');p.get_by_role('button',name='＋ 导入明确语义 UTC CSV / 查看导入原件',exact=True).click();p.get_by_label('目标船舶').select_option('V')
  open();p.get_by_role('button',name='读取本船导入回执（只读）').click();p.get_by_text('这是只读归档历史',exact=False).wait_for();assert p.get_by_role('heading',name='已核对保存回执').count()==0
  p.get_by_role('button',name='独立读取本船归档历史（不核验当前保存）').click();p.get_by_role('heading',name='只读航迹归档历史').wait_for()
  mode['bad']=True;p.get_by_role('button',name='记录访问并下载历史CSV').click();p.get_by_text('请求失败或响应无法核对',exact=False).wait_for();assert not downloads
  mode['bad']=False
  with p.expect_download() as dl:p.get_by_role('button',name='记录访问并下载历史CSV').click()
  assert Path(dl.value.path()).read_bytes()==raw
  open();p.get_by_label('资料来源说明（必填）').fill('Synthetic');p.get_by_label('UTC 时间依据说明（必填）').fill('Synthetic UTC');p.get_by_label('CSV 原件',exact=False).set_input_files({'name':'raw.csv','mimeType':'text/csv','buffer':raw});p.get_by_text('SHA-256：',exact=False).first.wait_for();p.get_by_role('button',name='服务端预览（不保存）',exact=True).click();p.get_by_role('heading',name='2 · 核对预览与来源声明').wait_for();p.get_by_label('我已核对目标案件',exact=False).check();p.get_by_role('button',name='确认保存本次航迹',exact=True).click();p.get_by_text('3 · 结果待核查',exact=False).wait_for();assert p.get_by_label('目标船舶').is_disabled()
  mode['code']='TRACK_ORIGIN_UNVERIFIED';p.get_by_role('button',name='同一内容幂等重试保存').click();p.get_by_text('导入来源无法验证',exact=False).wait_for();assert len(posts)==2 and posts[0]==posts[1];assert p.get_by_label('目标船舶').is_disabled()
  p.get_by_role('button',name='只读核查本次保存').click();p.get_by_text('导入来源无法验证',exact=False).wait_for();assert p.get_by_role('heading',name='已核对保存回执').count()==0
  for button in ['Switch case','Switch identity']:
   open();mode['hold']=True;p.get_by_role('button',name='独立读取本船归档历史（不核验当前保存）').click()
   for _ in range(30):
    if held:break
    p.wait_for_timeout(20)
   assert held;p.get_by_role('button',name=button,exact=True).click();held.pop().fulfill(json={'caseId':'A','vesselId':'V','mode':'archive-only','items':[h]});p.wait_for_timeout(100);assert p.get_by_role('heading',name='只读航迹归档历史').count()==0;mode['hold']=False
  b.close()
 print('Track history API-double browser passed: historical not active, strict hash download, both409 preserve identical unknown body, late case/identity response suppressed')
finally:os.killpg(s.pid,signal.SIGTERM);s.wait()
