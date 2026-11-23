"""Opt-in real Chromium test. Only intercepted local assets; no server or backend."""
import argparse, hashlib, json
from pathlib import Path
from urllib.parse import urlparse, unquote

p=argparse.ArgumentParser()
p.add_argument('--chromium',required=True, type=Path)
p.add_argument('--dist',required=True,type=Path)
p.add_argument('--output',required=True,type=Path)
a=p.parse_args()
if not a.chromium.is_file() or not (a.dist/'index.html').is_file():p.error('existing Chromium and built fixture required')
if a.output.exists():p.error('output must be a new directory')
from playwright.sync_api import sync_playwright

a.output.mkdir(parents=True)
receipt={'schema':'mcis-evidence-page-browser-1','passed':False,'fixtureSha256':{},'checks':[],'externalRequests':0}
for f in sorted(a.dist.rglob('*')):
 if f.is_file():receipt['fixtureSha256'][str(f.relative_to(a.dist))]=hashlib.sha256(f.read_bytes()).hexdigest()
try:
 with sync_playwright() as pw:
  # Playwright default disables sandbox: explicitly enable it. No custom launch flags.
  browser=pw.chromium.launch(executable_path=str(a.chromium.resolve()),headless=True,chromium_sandbox=True)
  receipt['browserVersion']=browser.version
  for width in (1440,390):
   context=browser.new_context(viewport={'width':width,'height':900},service_workers='block')
   external=[]; errors=[]
   def route(r):
    u=urlparse(r.request.url)
    path=(a.dist/unquote(u.path).lstrip('/')).resolve()
    if u.scheme!='https' or u.netloc!='mcis-synthetic.invalid' or not path.is_relative_to(a.dist.resolve()) or not path.is_file():
     external.append('blocked');receipt['externalRequests']+=1;r.abort();return
    r.fulfill(path=str(path))
   context.route('**/*',route)
   page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
   def req():
    page.wait_for_function('window.gate && gate.requests().length > 0')
    return page.evaluate('gate.requests().at(-1).id')
   def settle(i,kind,title=''):
    page.evaluate('(v)=>gate.settle(...v)',[i,kind,title])
   def metrics(value):
    page.wait_for_function('(v)=>Array.from(document.querySelectorAll(".w4-metrics .val")).slice(0,4).every(x=>x.textContent===v)',arg=value)
   for late in ('data','deny'):
    page.goto('https://mcis-synthetic.invalid/index.html')
    old=req();metrics('待载入');settle(old,'data','OLD-A')
    page.get_by_role('button',name='OLD-A',exact=True).wait_for()
    page.get_by_role('button',name='Case B',exact=True).click();b=req()
    assert 'OLD-A' not in page.locator('.w4-page').inner_text()
    page.get_by_role('button',name='Case A',exact=True).click();stale=req()
    page.get_by_role('button',name='Case B',exact=True).click();current=req()
    settle(current,'data','CURRENT-B');page.get_by_role('button',name='CURRENT-B',exact=True).wait_for()
    settle(stale,late,'LATE-A');settle(b,late,'LATE-B')
    # Allow promise, effects and rendering opportunities before checking absence.
    page.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
    text=page.locator('.w4-page').inner_text()
    assert 'CURRENT-B' in text and 'LATE-' not in text and 'OLD-A' not in text and 'Synthetic denied' not in text
    # A pending request issued under old identity must not overwrite current denial.
    page.get_by_role('button',name='Case A',exact=True).click();identity_old=req()
    page.get_by_role('button',name='Synthetic identity change',exact=True).click();identity_new=req()
    assert identity_old!=identity_new
    settle(identity_new,'deny');metrics('不可用')
    settle(identity_old,late,'LATE-IDENTITY')
    page.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
    metrics('不可用')
    assert 'LATE-IDENTITY' not in page.locator('.w4-page').inner_text()
    assert '暂无证据' not in page.locator('.w4-page').inner_text()
    page.get_by_role('button',name='Case B',exact=True).click();settle(req(),'empty')
    page.get_by_text('暂无证据，请添加调查证据。',exact=True).wait_for()
    assert page.locator('.w4-metrics .val').all_text_contents()[:4]==['0条','0/ 0','0条','0条']
    assert not page.evaluate('gate.unexpected()')
    receipt['checks'].append({'width':width,'touch':False,'late':late,'passed':True})
   assert not external and not errors, 'unexpected network or page error'
   page.screenshot(path=str(a.output/f'empty-{width}.png'),full_page=True)
   context.close()
  browser.close()
 receipt['passed']=True
finally:
 (a.output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('PASS EvidencePage synthetic Chromium lifecycle; no real authorization/backend')
