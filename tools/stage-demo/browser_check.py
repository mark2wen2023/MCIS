#!/usr/bin/env python3
"""Browse/download UI checks against held stage-demo real HTTP services. No API doubles.
Requires runner --hold, installed Playwright and MCIS_BROWSER_BIN. Does not mutate cases.
"""
import argparse, hashlib, json, os, signal, socket, subprocess, time, urllib.request
from pathlib import Path
from urllib.parse import urlparse, urlencode
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]

def port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def clean_env():
 return {k:os.environ[k] for k in ['PATH','HOME','TMPDIR','LANG','LC_ALL'] if k in os.environ}

def owned_listener(pid,port):
 """Linux-only fail closed: exact process must hold the loopback LISTEN inode."""
 try:
  sockets=set()
  for fd in Path(f'/proc/{pid}/fd').iterdir():
   try:target=os.readlink(fd)
   except FileNotFoundError:continue # unrelated transient descriptors can close during enumeration
   if target.startswith('socket:['):sockets.add(target[8:-1])
  for line in Path('/proc/net/tcp').read_text().splitlines()[1:]:
   cols=line.split()
   if cols[1]==f'0100007F:{port:04X}' and cols[3]=='0A' and cols[9] in sockets:return True
 except (OSError,ValueError):return False
 return False

def service_guard(entry,run_dir):
 u=urlparse(entry['url']);assert u.scheme=='http' and u.hostname=='127.0.0.1' and u.port and not u.username and not u.password and not u.path and not u.query and not u.fragment,'Exact loopback origin required'
 pid=entry['pid'];assert type(pid) is int and pid>0
 data=(run_dir/entry['dataDir']).resolve();assert data.parent==run_dir.resolve(),'Data directory must belong to this run'
 expected=str((ROOT/'tools/stage-demo/server.py').resolve())
 cmd=Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0');args=[x.decode() for x in cmd if x]
 assert len(args)==4 and str(Path(args[1]).resolve())==expected and str(Path(args[2]).resolve())==str(data),'Manifest process is not the expected owned service'
 # starttime pins against PID reuse even when a stale manifest names a later process.
 start=entry.get('processStartTicks');assert isinstance(start,str) and start.isdecimal(),'Missing process start identity'
 def check():
  assert Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[19]==start,'Service process changed'
  assert Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')==cmd,'Service executable changed'
  assert owned_listener(pid,u.port),'Owned service no longer holds declared port'
 check();return check

def main():
 if not __debug__:raise RuntimeError('Optimized Python disables verification; refusing before any operation')
 ap=argparse.ArgumentParser();ap.add_argument('manifest',type=Path);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
 args.manifest=args.manifest.resolve();manifest=json.loads(args.manifest.read_text());assert manifest['status']=='passed' and manifest['running'], 'Runner must be successful and --hold services still running'
 guards={name:service_guard(manifest['services'][name],args.manifest.parent) for name in ['source','case-restored','knowledge-history']}
 args.output.mkdir(parents=True,exist_ok=False);checks=[];result={'status':'running','scope':'real-backend-browse-and-download-ui','checks':checks,'notTested':['UI form submission end-to-end','LLM','production authentication','Unity','W11']};servers=[]
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.environ['MCIS_BROWSER_BIN'],headless=True,args=['--no-sandbox','--no-proxy-server','--disable-background-networking','--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1'],env=clean_env())
   for name in ['source','case-restored','knowledge-history']:
    guard=guards[name];guard();service=manifest['services'][name]['url']
    frontend=port();env={**clean_env(),'MCIS_API':service};proc=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port',str(frontend),'--strictPort'],cwd=ROOT/'web',env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True);servers.append(proc)
    base=f'http://127.0.0.1:{frontend}'
    for _ in range(150):
     try:
      assert proc.poll() is None and owned_listener(proc.pid,frontend),'Vite not ready or no longer owns port'
      guard();urllib.request.build_opener(urllib.request.ProxyHandler({})).open(base,timeout=.5);break
     except Exception:time.sleep(.1)
    else:raise RuntimeError('Frontend startup failed')
    context=browser.new_context();context.add_init_script("localStorage.setItem('mcis.role','LeadInvestigator');localStorage.setItem('mcis.operator','Stage Browser Readonly')")
    page=context.new_page();page.set_default_timeout(15000)
    def visit(route,query,endpoint):
     guard();assert proc.poll() is None and owned_listener(proc.pid,frontend)
     with page.expect_response(lambda r:endpoint in r.url and r.request.method=='GET') as response:page.goto(base+'/#/'+route+'?'+urlencode(query))
     assert response.value.status==200,(name,route,response.value.status)
    if name!='knowledge-history':
     case=manifest['caseId'];ids=manifest['ids']
     visit('lobby',{},'/api/v1/cases');page.get_by_text(case,exact=False).first.wait_for();checks.append(name+': lobby actual case visible')
     for route,endpoint in [('ships','/vessels'),('track','/tracks'),('evidence','/evidence')]:
      visit(route,{'case':case},f'/cases/{case}'+endpoint)
      if route=='ships':page.get_by_text('船舶编号：'+manifest['vesselId'],exact=True).wait_for()
      elif route=='track':page.get_by_role('heading',name='点位分布',exact=False).wait_for()
      else:page.locator('.w42-evidence-select').first.wait_for()
      if route=='track':
       page.get_by_role('button',name='＋ 导入明确语义 UTC CSV / 查看导入原件',exact=True).click();page.get_by_label('目标船舶').select_option(manifest['vesselId']);page.get_by_role('button',name='读取本船导入回执（只读）',exact=True).click()
       if name=='source':page.get_by_role('heading',name='已核对保存回执',exact=True).wait_for();checks.append('source: current local track receipt visible')
       else:
        page.get_by_text('这是只读归档历史',exact=False).wait_for();assert page.get_by_role('heading',name='已核对保存回执',exact=True).count()==0
        page.get_by_role('button',name='独立读取本船归档历史（不核验当前保存）',exact=True).click();page.get_by_role('heading',name='只读航迹归档历史',exact=True).wait_for();guard()
        with page.expect_download() as dl:page.get_by_role('button',name='记录访问并下载历史CSV',exact=True).click()
        assert Path(dl.value.path()).read_bytes()==(args.manifest.parent/'synthetic-track.csv').read_bytes();dl.value.save_as(args.output/'historical-track.csv');checks.append('case-restored: track history not active; original CSV exact download')
      page.screenshot(path=str(args.output/f'{name}-{route}.png'),full_page=True);checks.append(name+': '+route+' real GET200 and route rendered')
     visit('interview',{'case':case,'record':ids['interviewId']},f'/interview-compare/{ids["interviewId"]}')
     if name=='case-restored':page.get_by_role('heading',name='此对象包含恢复历史',exact=True).wait_for()
     page.screenshot(path=str(args.output/f'{name}-interview.png'),full_page=True);checks.append(name+': interview reopened'+(' with restored-history warning' if name=='case-restored' else ''))
     visit('report',{'case':case,'report':ids['reportId']},f'/reports/{ids["reportId"]}')
     page.locator('select[aria-label="报告版本"]').wait_for();assert page.locator('select[aria-label="报告版本"]').input_value()==ids['reportId']
     if name=='case-restored':page.get_by_role('heading',name='此对象包含恢复历史',exact=True).wait_for()
     page.screenshot(path=str(args.output/f'{name}-report.png'),full_page=True);checks.append(name+': report saved version reopened')
    guard();page.goto(base+'/#/knowledge');page.get_by_role('heading',name='案例、疑难与方法知识卡').wait_for();page.get_by_text('全局知识库独立归档（首席限定）',exact=True).click()
    if name=='knowledge-history':
     page.get_by_role('button',name='读取只读历史列表',exact=True).click();page.get_by_role('button',name='浏览历史原文',exact=True).first.wait_for();page.get_by_role('button',name='浏览历史原文',exact=True).first.click();page.get_by_role('heading',name='历史原文（不是当前在线状态）').wait_for()
     guard()
     with page.expect_download() as dl:page.get_by_role('button',name='校验并下载历史原包',exact=True).first.click()
     path=Path(dl.value.path());digest=hashlib.sha256(path.read_bytes()).hexdigest();assert digest in dl.value.suggested_filename;dl.value.save_as(args.output/'history-original.json');checks.append('knowledge-history: real UI history detail and SHA-verified original download')
    page.screenshot(path=str(args.output/f'{name}-knowledge.png'),full_page=True);context.close()
   browser.close();result['status']='passed'
 except Exception as e:result['status']='failed';result['error']=str(e);raise
 finally:
  (args.output/'browser-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
  for proc in servers:
   if proc.poll() is None:os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=10)
if __name__=='__main__':main()
