"""Real API/core/browser acceptance; only explicit binding/race probes modify response delivery."""
import os,signal,subprocess,tempfile,time,urllib.request,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent
with tempfile.TemporaryDirectory(prefix='w183-accept-') as tmp:
 env={**os.environ,'MCIS_DATA_DIR':tmp+'/data','MCIS_API':'http://127.0.0.1:15985','PYTHONPATH':str(ROOT/'service'),'MCIS_DOTNET':os.environ.get('MCIS_DOTNET',str(Path.home()/'.dotnet/dotnet')),'DOTNET_CLI_HOME':tmp+'/dotnet'}
 back=subprocess.Popen([str(ROOT/'service/.venv/bin/python'),str(HERE/'server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 front=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15986','--strictPort'],cwd=ROOT/'web',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
 try:
  for port,path in [(15985,'/api/v1/health'),(15986,'/')]:
   for _ in range(100):
    try:urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',timeout=1);break
    except Exception:time.sleep(.1)
   else:raise RuntimeError('local startup failed')
  with sync_playwright() as p:
   browser=p.chromium.launch(executable_path=os.environ.get('MCIS_BROWSER_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox'],env={**os.environ,'HOME':tmp,'XDG_CONFIG_HOME':tmp+'/config'})
   page=browser.new_page(); errors=[]
   page.on('pageerror',lambda e:errors.append(str(e)))
   CASES=json.loads('{"three": {"recordStartUtc": "2026-01-01T00:00:00Z", "recordEndUtc": "2026-01-02T00:00:00Z", "intervals": [{"startUtc": "2026-01-01T00:00:00Z", "endUtc": "2026-01-01T06:00:00Z", "kind": "Rest"}, {"startUtc": "2026-01-01T06:00:00Z", "endUtc": "2026-01-01T10:00:00Z", "kind": "Watch"}, {"startUtc": "2026-01-01T10:00:00Z", "endUtc": "2026-01-01T14:00:00Z", "kind": "Rest"}, {"startUtc": "2026-01-01T14:00:00Z", "endUtc": "2026-01-01T18:00:00Z", "kind": "Watch"}, {"startUtc": "2026-01-01T18:00:00Z", "endUtc": "2026-01-01T19:00:00Z", "kind": "Rest"}, {"startUtc": "2026-01-01T19:00:00Z", "endUtc": "2026-01-02T00:00:00Z", "kind": "Watch"}]}, "short": {"recordStartUtc": "2026-01-01T00:00:00Z", "recordEndUtc": "2026-01-01T05:00:00Z", "intervals": [{"startUtc": "2026-01-01T00:00:00Z", "endUtc": "2026-01-01T05:00:00Z", "kind": "Rest"}]}, "gap": {"recordStartUtc": "2026-01-01T00:00:00Z", "recordEndUtc": "2026-01-02T03:00:00Z", "intervals": [{"startUtc": "2026-01-01T00:00:00Z", "endUtc": "2026-01-01T06:00:00Z", "kind": "Rest"}, {"startUtc": "2026-01-01T06:00:00Z", "endUtc": "2026-01-01T21:00:00Z", "kind": "Watch"}, {"startUtc": "2026-01-01T21:00:00Z", "endUtc": "2026-01-02T03:00:00Z", "kind": "Rest"}]}, "minute": {"recordStartUtc": "2026-01-01T00:00:00Z", "recordEndUtc": "2026-01-02T03:00:00Z", "intervals": [{"startUtc": "2026-01-01T00:00:00Z", "endUtc": "2026-01-01T06:00:00Z", "kind": "Rest"}, {"startUtc": "2026-01-01T06:00:00Z", "endUtc": "2026-01-01T13:00:00Z", "kind": "Watch"}, {"startUtc": "2026-01-01T13:00:00Z", "endUtc": "2026-01-01T13:01:00Z", "kind": "Rest"}, {"startUtc": "2026-01-01T13:01:00Z", "endUtc": "2026-01-01T21:00:00Z", "kind": "Watch"}, {"startUtc": "2026-01-01T21:00:00Z", "endUtc": "2026-01-02T03:00:00Z", "kind": "Rest"}]}}')
   for name,data in CASES.items():
    page.goto('http://127.0.0.1:15986/#/hf?case=CASE-A');page.reload()
    page.get_by_label('记录起点 UTC',exact=True).fill(data['recordStartUtc'])
    page.get_by_label('记录终点 UTC',exact=True).fill(data['recordEndUtc'])
    for i,row in enumerate(data['intervals'],1):
     if i>1:page.get_by_role('button',name='添加时段',exact=True).click()
     page.get_by_label(f'开始 UTC {i}',exact=True).fill(row['startUtc'])
     page.get_by_label(f'结束 UTC {i}',exact=True).fill(row['endUtc'])
     page.get_by_label(f'类型 {i}',exact=True).select_option(row['kind'])
    page.get_by_role('checkbox',name='EV-001').check()
    page.get_by_role('checkbox',name='我理解这是人工录入').check()
    page.get_by_role('button',name='运行技术预览（不保存）',exact=True).click()
    page.get_by_role('heading',name='工休技术预览 · 未保存',exact=True).wait_for()
    result=page.locator('.w183-result'); visible=result.inner_text()
    assert '未评估总休息段数' in visible
    assert '短 Rest 未经专业认定' in visible
    assert '核心历史说明中的“合规”等字样不构成结论' in visible
    assert '无偏离条目不代表合规' in visible
    if name=='short':
     assert '记录长度不足' in visible
     assert '不表示数据充分' in visible
    result.locator('summary').click()
    assert '每天连续 10h 均判合规' in result.inner_text()
    assert '“合规”等旧措辞不能超出上述未评估边界解释' in result.inner_text()
   assert not errors,errors
   browser.close()
  print('PASS 4 synthetic schedules via actual browser/API/CLI; visible limitations and preserved historical assumptions qualified.')
 finally:
  for proc in (front,back):os.killpg(proc.pid,signal.SIGTERM);proc.wait()
