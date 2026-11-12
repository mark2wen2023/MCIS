"""Real old-runtime restore, new service and browser compatibility/403 checks."""
import os,signal,subprocess,tempfile,time,urllib.request,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).parent;CID='SYN-TRACK-HISTORY'
with tempfile.TemporaryDirectory(prefix='track-old-provenance-') as tmp:
 root=Path(tmp);old=Path(os.environ['MCIS_OLD_ROOT'])
 subprocess.run([str(ROOT/'service/.venv/bin/python'),str(HERE/'legacy_fixture.py'),tmp],env={**os.environ,'PYTHONPATH':str(old/'service')},check=True,capture_output=True,text=True,timeout=40)
 report=json.loads((root/'report.json').read_text());data=root/'restricted-restored';source=data/'blobs'/CID/'_package_intake/source.mcase';original=source.read_bytes()
 env={**os.environ,'MCIS_DATA_DIR':str(data),'MCIS_API':'http://127.0.0.1:15996','PYTHONPATH':str(ROOT/'service')};procs=[]
 try:
  procs.append(subprocess.Popen([str(ROOT/'service/.venv/bin/python'),str(HERE/'provenance_server.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True))
  procs.append(subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','15997','--strictPort'],cwd=ROOT/'web',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True))
  for port in (15996,15997):
   for _ in range(200):
    try:urllib.request.urlopen(f'http://127.0.0.1:{port}'+('/api/v1/health' if port==15996 else '/'),timeout=1);break
    except Exception:time.sleep(.1)
   else:raise RuntimeError('loopback service startup failed')
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.environ['MCIS_BROWSER_BIN'],headless=True,args=['--no-sandbox']);p=browser.new_page();p.set_default_timeout(12000);errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
   p.add_init_script("localStorage.setItem('mcis.role','LeadInvestigator');localStorage.setItem('mcis.operator','Synthetic Track Reviewer')")
   p.goto(f"http://127.0.0.1:15997/#/report?case={CID}&report={report['reportId']}")
   p.get_by_text('旧来源包版本暂不支持恢复来源核验',exact=False).wait_for();assert p.locator('.rpt-sentence').count()>0
   assert source.read_bytes()==original
   source.write_bytes(original+b'SYNTHETIC-TAMPER');p.reload();p.get_by_text('此对象恢复来源未能核验',exact=False).wait_for()
   assert p.get_by_text('旧来源包版本暂不支持恢复来源核验',exact=False).count()==0
   source.write_bytes(original)
   held=[]
   def pause(route):held.append(route)
   pattern='**/archive-history/provenance/report/*';p.route(pattern,pause);p.reload()
   p.wait_for_function("document.querySelectorAll('.rpt-sentence').length>0")
   for _ in range(200):
    if held:break
    p.wait_for_timeout(10)
   assert held
   base=f'http://127.0.0.1:15996/api/v1/cases/{CID}/access-policy';h={'X-MCIS-Role':'LeadInvestigator'}
   policy=p.request.get(base,headers=h).json();policy['matrix']['LeadInvestigator']['audit']='Deny';assert p.request.put(base,headers=h,data=policy).status==200
   with p.expect_response(lambda r:'/archive-history/provenance/report/' in r.url) as response:held.pop(0).continue_()
   assert response.value.status==403;p.wait_for_function("document.querySelectorAll('.rpt-sentence').length===0")
   p.unroute(pattern,pause)
   assert not errors,errors;assert source.read_bytes()==original;browser.close()
  print('PASS real old1.2 runtime restored DB upgraded: UNSUPPORTED notice keeps actual report body; real source tamper stays integrity/general error; real403 after body load clears parent; original bytes preserved.')
 finally:
  for p in procs:
   if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
  for p in procs:p.wait()
